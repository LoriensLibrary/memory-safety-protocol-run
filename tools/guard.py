"""Spend guard for paid model calls. Same contract as the SwarmHive runner's Model class (pre-existing work,
Nov 2026), rewritten as a standalone module with pacing and rate-limit waits added this weekend.

Contract: every provider attempt is reserved and debited BEFORE it is sent, at the documented context length x the
input rate plus the output cap x the output rate. A returned usage block reconciles the debit to metered cost.
A lost, errored, rate-limited or usage-less attempt keeps its full reserve as spent. Attempts are capped.
A response without usage, with usage above the reserve, or from a different model latches the guard shut.
"""
import json, math, os, time

# posted rates, credits per million tokens (input, output), and documented context.
# https://docs.adaptionlabs.ai/inference-stacks/models/ read 2026-11-14 11:15 EST. Where the page's rounded figure is above
# the finer figure SwarmHive recorded on 2026-11-08 (gemma-26b, deepseek), the higher one is used, so the guard never undercounts.
MODEL_SPEC = {
    "gemma-4-31b-it":     dict(provider="adaption", unit="credits", price=(0.09, 0.34), context=256000),
    "gemma-4-26b-a4b-it": dict(provider="adaption", unit="credits", price=(0.077, 0.26), context=256000),
    "deepseek-v4-flash":  dict(provider="adaption", unit="credits", price=(0.045, 0.14), context=1048576),
    "qwen3.8-27b":        dict(provider="adaption", unit="credits", price=(0.039, 1.25), context=262144),
    "qwen3.5-397b":       dict(provider="adaption", unit="credits", price=(0.55, 3.50), context=131072),
    "glm-53-flash":       dict(provider="adaption", unit="credits", price=(0.15, 0.50), context=1048576),
    "glm-5.2":            dict(provider="adaption", unit="credits", price=(1.40, 4.40), context=786432),
}
RETRY_5XX = (500, 502, 503, 504)


class BudgetStop(Exception):
    """Raised before a call that the ceiling, the attempt cap or an integrity latch forbids. Nothing was sent."""


class CallFailed(Exception):
    """The attempt was sent (or may have been) and did not produce a usable, metered reply. Its reserve stays spent."""


def _status(e):
    return getattr(e, "code", None) or getattr(e, "status_code", None) or getattr(getattr(e, "response", None), "status_code", None)


class SpendGuard:
    def __init__(self, model, ceiling, max_attempts, ledger, sender=None, sleep=time.sleep, retries_429=3, retries_5xx=1,
                 wait_429=65, min_interval=0.0, temperature=0.0, timeout=240, rawdir=None):
        spec = MODEL_SPEC.get(model)
        if spec is None:
            raise SystemExit(f"no posted rate/context for model {model!r}; add it to MODEL_SPEC from the provider's pricing page")
        if not isinstance(ceiling, (int, float)) or isinstance(ceiling, bool) or not math.isfinite(ceiling) or ceiling <= 0:
            raise SystemExit("a paid run requires a finite positive ceiling")
        if type(max_attempts) is not int or max_attempts < 1:
            raise SystemExit("a paid run requires a positive attempt cap")
        if sender is None:
            from vendor import adaption_send
            if adaption_send.BASE != adaption_send.HOSTED_BASE_URL:
                raise SystemExit("paid runs require the registered Adaption hosted endpoint")
            sender = adaption_send.send
        self.model, self.unit, self.price, self.context = model, spec["unit"], spec["price"], spec["context"]
        self.ceiling, self.max_attempts, self.ledger, self.sender, self.sleep = float(ceiling), max_attempts, ledger, sender, sleep
        self.retries_429, self.retries_5xx, self.wait_429, self.min_interval = retries_429, retries_5xx, wait_429, min_interval
        self.temperature, self.timeout, self.rawdir = temperature, timeout, rawdir
        self.spend, self.attempts, self.calls, self.integrity_stop, self._last_start = 0.0, 0, 0, None, 0.0

    def restore(self, spend, attempts, calls):
        """Resume: carry forward what an interrupted execution of the same claim already spent and sent."""
        self.spend, self.attempts, self.calls = float(spend), int(attempts), int(calls)

    def _log(self, **row):
        if self.ledger:
            with open(self.ledger, "a", encoding="utf-8") as f:
                f.write(json.dumps(dict(row, t=round(time.time(), 3))) + "\n")

    def reserve(self, max_tokens):
        if type(max_tokens) is not int or max_tokens < 1:
            raise BudgetStop(f"no positive max_tokens ({max_tokens!r})")
        pi, po = self.price
        return (self.context * pi + max_tokens * po) / 1e6

    def _attempt(self, request):
        if self.integrity_stop:
            raise BudgetStop(f"billing integrity latch: {self.integrity_stop}")
        if self.attempts >= self.max_attempts:
            self._log(call=self.calls, event="attempt_cap", attempts=self.attempts, max=self.max_attempts)
            raise BudgetStop(f"attempt cap {self.max_attempts} reached")
        res = self.reserve(request["max_tokens"])
        if self.spend + res > self.ceiling:
            self._log(call=self.calls, event="budget_stop", spend=round(self.spend, 6), reserve=round(res, 6), ceiling=self.ceiling)
            raise BudgetStop(f"spent {self.spend:.6f} + reserve {res:.6f} would cross ceiling {self.ceiling} {self.unit}")
        gap = self.min_interval - (time.time() - self._last_start)
        if gap > 0: self.sleep(gap)
        self._last_start = time.time()
        self.attempts += 1
        self.spend += res                                   # debit before the request leaves
        self._log(call=self.calls, event="debit", attempt=self.attempts, reserve=round(res, 6), spend_after_debit=round(self.spend, 6))
        try:
            resp = self.sender(**request)
        except Exception as e:                              # noqa: BLE001
            code = _status(e)
            self._log(call=self.calls, event="unresolved", attempt=self.attempts, status=code, error=type(e).__name__, reserve_kept=round(res, 6))
            err = CallFailed(f"{type(e).__name__} status={code}"); err.status = code
            raise err
        usage = getattr(resp, "usage", None)
        it, ot = getattr(usage, "input_tokens", None), getattr(usage, "output_tokens", None)
        if usage is None or type(it) is not int or type(ot) is not int or it < 0 or ot < 0:
            self.integrity_stop = "missing_usage"
        elif it > self.context or ot > request["max_tokens"]:
            self.integrity_stop = "usage_exceeds_reserve"
        elif getattr(resp, "model", None) != self.model:
            self.integrity_stop = "unrecognized_billing_model"
        if self.integrity_stop:
            self._log(call=self.calls, event=self.integrity_stop, attempt=self.attempts, returned_model=str(getattr(resp, "model", None))[:120], reserve_kept=round(res, 6))
            err = CallFailed(self.integrity_stop); err.status = None
            raise err
        pi, po = self.price
        cost = (it * pi + ot * po) / 1e6
        self.spend += cost - res                            # reconcile to metered usage at the posted rate
        self._log(call=self.calls, event="actual", attempt=self.attempts, input_tokens=it, output_tokens=ot, cost=round(cost, 8), spend_after=round(self.spend, 6))
        return resp, it, ot, cost

    def send(self, system, user, max_tokens):
        """One logical call (with bounded, ledgered waits on 429 and one retry on 5xx). Returns a plain record."""
        self.calls += 1
        request = dict(model=self.model, system=system, messages=[{"role": "user", "content": user}], max_tokens=max_tokens,
                       temperature=self.temperature, transport_timeout_s=self.timeout)
        t0, n429, n5xx = time.time(), 0, 0
        while True:
            try:
                resp, it, ot, cost = self._attempt(request); break
            except CallFailed as e:
                if e.status == 429 and n429 < self.retries_429:
                    n429 += 1; self._log(call=self.calls, event="rate_limit_wait", wait_s=self.wait_429); self.sleep(self.wait_429); continue
                if e.status in RETRY_5XX and n5xx < self.retries_5xx:
                    n5xx += 1; self._log(call=self.calls, event="retry_5xx_wait", wait_s=5); self.sleep(5); continue
                raise
        text = "".join(getattr(b, "text", "") or "" for b in (getattr(resp, "content", None) or []))
        rec = dict(call=self.calls, model=self.model, input_tokens=it, output_tokens=ot, cost=round(cost, 8), unit=self.unit,
                   reasoning_tokens=getattr(getattr(resp, "usage", None), "reasoning_tokens", None), stop_reason=getattr(resp, "stop_reason", None),
                   response_id=getattr(resp, "id", None), waits_429=n429, retries_5xx=n5xx, elapsed_s=round(time.time() - t0, 3), text=text)
        if self.rawdir:
            with open(os.path.join(self.rawdir, f"call_{self.calls:05d}.json"), "w", encoding="utf-8") as f:
                json.dump(dict(system=system, user=user, max_tokens=max_tokens, response=rec), f, indent=1)
        return rec
