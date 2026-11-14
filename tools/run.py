"""Freeze and execute a cohort of the provenance study.

  python tools/run.py freeze --name dev_gemma --split dev --seed 11 --n 2 --model gemma-4-31b-it --ceiling 1
  python tools/run.py run --freeze holdout/dev_gemma --mode dry
  python tools/run.py run --freeze holdout/dev_gemma --mode paid            (needs Angela's go and a credit cap)
  python tools/run.py run --freeze holdout/dev_gemma --mode paid --resume   (after a crash or a sleep)

A freeze fixes the items, the arm order per item, the prompts, the code and the model settings. The runner
recomputes every hash before it dispatches and refuses a freeze that no longer matches. One paid execution per
freeze: the claim file is created exclusively, and only --resume may continue it.
"""
import argparse, hashlib, json, os, random, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import items, score, guard   # noqa: E402

CODE_FILES = ("items.py", "score.py", "guard.py", "run.py", os.path.join("vendor", "adaption_send.py"))
DEFAULT_KEY = os.path.join(os.path.dirname(ROOT), "SwarmHive", "secrets", "adaption.key")


def sha_file(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def sha_obj(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode("utf-8")).hexdigest()


def code_hashes():
    return {f.replace(os.sep, "/"): sha_file(os.path.join(HERE, f)) for f in CODE_FILES}


def calls_worst_case(arms):
    return sum({"bare": 1, "env_json": 1, "env_prose": 1, "lookup": 2, "rule": 0}[a] for a in arms)


# ---------------- freeze ----------------
def cmd_freeze(a):
    out = os.path.join(ROOT, "holdout", a.name)
    if os.path.exists(out):
        raise SystemExit(f"{out} already exists; a freeze is never overwritten")
    variants = a.variants.split(","); arms = a.arms.split(",")
    for v in variants:
        if v not in items.VARIANTS: raise SystemExit(f"unknown variant {v}")
    for arm in arms:
        if arm not in items.ARMS: raise SystemExit(f"unknown arm {arm}")
    if a.model not in guard.MODEL_SPEC: raise SystemExit(f"no posted rate for {a.model}")
    inst = []
    for i in range(a.n):                                   # interleaved, so a partial run stays balanced across variants
        for v in variants:
            it = items.make_item(v, i, a.seed)
            order = [x for x in arms if x != "rule"]
            random.Random(f"{a.seed}|order|{v}|{i}").shuffle(order)
            it["arm_order"] = order + (["rule"] if "rule" in arms else [])
            inst.append(it)
    logical = len(inst) * calls_worst_case(arms)
    frz = dict(name=a.name, split=a.split, seed=a.seed, n_per_variant=a.n, variants=variants, arms=arms,
               model=a.model, provider="adaption", max_tokens=a.max_tokens, temperature=0.0, timeout_s=a.timeout,
               ceiling=a.ceiling, unit="credits", rates=list(guard.MODEL_SPEC[a.model]["price"]), context=guard.MODEL_SPEC[a.model]["context"],
               min_interval_s=a.min_interval, retries_429=a.retries_429, retries_5xx=a.retries_5xx, wait_429_s=65,
               logical_calls_max=logical, max_attempts=logical + max(20, logical // 10),
               instances_sha256=sha_obj(inst), prompts_sha256=items.prompts_sha256(), code_sha256=code_hashes(),
               created=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    frz["freeze_id"] = sha_obj(frz)[:16]
    os.makedirs(out)
    json.dump(inst, open(os.path.join(out, "instances.json"), "w", encoding="utf-8"), indent=1)
    json.dump(frz, open(os.path.join(out, "FREEZE.json"), "w", encoding="utf-8"), indent=1)
    print(f"frozen {a.name}: {len(inst)} items x {len(arms)} arms, up to {logical} model calls, attempt cap {frz['max_attempts']}, "
          f"ceiling {a.ceiling} credits, freeze_id {frz['freeze_id']}")


def load_freeze(fdir):
    frz = json.load(open(os.path.join(fdir, "FREEZE.json"), encoding="utf-8"))
    inst = json.load(open(os.path.join(fdir, "instances.json"), encoding="utf-8"))
    body = {k: v for k, v in frz.items() if k != "freeze_id"}
    problems = []
    if sha_obj(body)[:16] != frz["freeze_id"]: problems.append("FREEZE.json was edited after freezing")
    if sha_obj(inst) != frz["instances_sha256"]: problems.append("instances.json does not match the freeze")
    if items.prompts_sha256() != frz["prompts_sha256"]: problems.append("prompts changed since the freeze")
    now = code_hashes()
    for f, h in frz["code_sha256"].items():
        if now.get(f) != h: problems.append(f"code changed since the freeze: {f}")
    spec = guard.MODEL_SPEC.get(frz["model"])
    if spec is None or list(spec["price"]) != frz["rates"] or spec["context"] != frz["context"]: problems.append("model rates/context differ from the freeze")
    regen = []
    for it in inst:
        fresh = items.make_item(it["variant"], int(it["tid"].split("-")[1]), frz["seed"])
        fresh["arm_order"] = it["arm_order"]; regen.append(fresh)
    if sha_obj(regen) != frz["instances_sha256"]: problems.append("instances cannot be regenerated from the seed")
    if problems:
        raise SystemExit("FREEZE MISMATCH, nothing dispatched:\n  " + "\n  ".join(problems))
    return frz, inst


def read_jsonl(path):
    """Read a JSON-lines file. A power loss can leave the LAST line half written; that one line is cut off the file
    (its slot simply runs again). A bad line anywhere else is corruption and stops the run."""
    raw = open(path, "rb").read().decode("utf-8", errors="replace")
    lines = [ln for ln in raw.split("\n") if ln.strip()]
    rows = []
    for i, ln in enumerate(lines):
        try:
            rows.append(json.loads(ln))
        except Exception:   # noqa: BLE001
            if i != len(lines) - 1:
                raise SystemExit(f"{path}: line {i + 1} is not valid JSON and is not the last line; refusing to continue")
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write("".join(x + "\n" for x in lines[:-1]))
            print(f"dropped a half-written final line from {os.path.basename(path)}", flush=True)
    return rows


def hold_awake():
    """Ask Windows not to idle-sleep while this process runs; the request ends when the process exits.
    It changes no setting. A closed lid or a manual Sleep still sleeps, and a call in flight then becomes an error slot."""
    try:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        return True
    except Exception:   # noqa: BLE001  (not Windows, or the call is unavailable)
        return False


# ---------------- one (item, arm) slot ----------------
def run_slot(it, arm, ask):
    """ask(system, user) -> record with text and token counts. Returns one trace row. Exceptions propagate."""
    ids = [s["id"] for s in it["sources"]]
    row = dict(tid=it["tid"], variant=it["variant"], arm=arm, status="complete", lookup_taken=None, calls=0,
               input_tokens=0, output_tokens=0, reasoning_tokens=0, cost=0.0, elapsed_s=0.0, stop_reasons=[], invalid_reason=None)
    if arm == "rule":
        reply = items.rule_decide(it)
    else:
        def call(stage, allow_lookup):
            req = items.build_request(it, arm, stage)
            rec = ask(req["system"], req["user"])
            row["calls"] += 1
            for k in ("input_tokens", "output_tokens", "cost", "elapsed_s"): row[k] = round(row[k] + (rec.get(k) or 0), 8)
            row["reasoning_tokens"] += rec.get("reasoning_tokens") or 0
            row["stop_reasons"].append(rec.get("stop_reason"))
            return score.parse_reply(rec.get("text"), ids, allow_lookup=allow_lookup)
        try:
            reply = call(1, arm == "lookup")
            if arm == "lookup":
                row["lookup_taken"] = reply["decision"] == "lookup"
                if row["lookup_taken"]:
                    reply = call(2, False)
        except score.Invalid as e:
            row.update(status="invalid", invalid_reason=str(e), outcome=None)
            return row
    row.update(decision=reply["decision"], answer=reply["answer"], sources=reply["sources"], **score.score(it, reply))
    return row


def cmd_run(a):
    fdir = a.freeze if os.path.isabs(a.freeze) else os.path.join(ROOT, a.freeze)
    frz, inst = load_freeze(fdir)
    out = os.path.join(ROOT, "runs", f"{frz['name']}_{a.mode}")
    traces_path, ledger = os.path.join(out, "traces.jsonl"), os.path.join(out, "ledger.jsonl")
    done, g = set(), None
    if a.mode == "paid":
        # every precondition is checked BEFORE the single-use claim is taken, so a failed launch does not burn the freeze
        key_file = a.key_file or DEFAULT_KEY
        if not os.environ.get("ADAPTION_API_KEY"):
            if not os.path.exists(key_file): raise SystemExit(f"no Adaption key at {key_file}")
            os.environ["ADAPTION_API_KEY"] = open(key_file, encoding="utf-8-sig").read().strip()   # never printed or logged
        g = guard.SpendGuard(frz["model"], frz["ceiling"], frz["max_attempts"], ledger, retries_429=frz["retries_429"], retries_5xx=frz["retries_5xx"],
                             wait_429=frz["wait_429_s"], min_interval=frz["min_interval_s"], temperature=frz["temperature"], timeout=frz["timeout_s"],
                             rawdir=os.path.join(out, "raw"))
        claims = os.path.join(ROOT, "runs", "claims"); os.makedirs(claims, exist_ok=True)
        claim = os.path.join(claims, f"{frz['freeze_id']}.json")
        if a.resume:
            if not (os.path.exists(claim) and os.path.exists(traces_path)): raise SystemExit("nothing to resume for this freeze")
        else:
            try:
                fd = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                raise SystemExit("this freeze already has a paid execution; use --resume to continue it, or freeze again")
            os.write(fd, json.dumps(dict(freeze_id=frz["freeze_id"], name=frz["name"], started=time.strftime("%Y-%m-%dT%H:%M:%S%z"))).encode()); os.close(fd)
    elif os.path.exists(out) and not a.resume:
        import shutil; shutil.rmtree(out)                  # dry runs are disposable
    os.makedirs(os.path.join(out, "raw"), exist_ok=True)
    if os.path.exists(traces_path):
        for r in read_jsonl(traces_path):
            done.add((r["tid"], r["arm"]))
    if a.mode == "paid":
        if a.resume and os.path.exists(ledger):
            spend = attempts = calls = 0
            for r in read_jsonl(ledger):
                spend = r.get("spend_after", r.get("spend_after_debit", spend)); attempts = max(attempts, r.get("attempt", 0)); calls = max(calls, r.get("call", 0))
            g.restore(spend, attempts, calls)
        ask = lambda system, user: g.send(system, user, frz["max_tokens"])   # noqa: E731
    awake = hold_awake() if a.mode == "paid" else None
    t0, n_new, stopped = time.time(), 0, None
    with open(traces_path, "a", encoding="utf-8") as tf:
        for it in inst:
            for arm in it["arm_order"]:
                if (it["tid"], arm) in done: continue
                if stopped:
                    continue                                # unreached slots stay registered in the freeze and are reported as not run
                if a.mode == "dry":
                    state = {"stage": 0}
                    def ask(system, user, _it=it, _arm=arm, _s=state):   # noqa: E306
                        _s["stage"] += 1
                        return dict(text=items.canned_reply(_it, _arm, _s["stage"]), stop_reason="canned")
                try:
                    row = run_slot(it, arm, ask)
                except guard.BudgetStop as e:
                    stopped = str(e)
                    row = dict(tid=it["tid"], variant=it["variant"], arm=arm, status="budget_stopped", outcome=None, invalid_reason=str(e))
                except guard.CallFailed as e:
                    row = dict(tid=it["tid"], variant=it["variant"], arm=arm, status="error", outcome=None, invalid_reason=str(e))
                tf.write(json.dumps(row) + "\n"); tf.flush(); n_new += 1
                if a.mode == "paid" and n_new % 25 == 0:
                    print(f"  {n_new} slots, {g.attempts} attempts, {g.spend:.4f} credits, {time.time() - t0:.0f}s", flush=True)
    execution = dict(freeze_id=frz["freeze_id"], mode=a.mode, resumed=bool(a.resume), new_slots=n_new, stopped=stopped,
                     finished=time.strftime("%Y-%m-%dT%H:%M:%S%z"), wall_s=round(time.time() - t0, 1),
                     spend=round(g.spend, 6) if g else 0.0, attempts=g.attempts if g else 0, integrity_stop=g.integrity_stop if g else None,
                     held_awake=awake)
    with open(os.path.join(out, "EXECUTION.jsonl"), "a", encoding="utf-8") as f: f.write(json.dumps(execution) + "\n")
    print(json.dumps(execution))
    print("out:", out)


def main():
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("--name", required=True); f.add_argument("--split", choices=("dev", "heldout"), required=True)
    f.add_argument("--seed", type=int, required=True); f.add_argument("--n", type=int, required=True)
    f.add_argument("--variants", default=",".join(items.VARIANTS)); f.add_argument("--arms", default=",".join(items.ARMS))
    f.add_argument("--model", required=True); f.add_argument("--max-tokens", type=int, default=6000)
    f.add_argument("--ceiling", type=float, required=True); f.add_argument("--timeout", type=int, default=240)
    f.add_argument("--min-interval", type=float, default=0.0); f.add_argument("--retries-429", type=int, default=3); f.add_argument("--retries-5xx", type=int, default=1)
    r = sub.add_parser("run")
    r.add_argument("--freeze", required=True); r.add_argument("--mode", choices=("dry", "paid"), required=True)
    r.add_argument("--resume", action="store_true"); r.add_argument("--key-file")
    a = p.parse_args()
    cmd_freeze(a) if a.cmd == "freeze" else cmd_run(a)


if __name__ == "__main__":
    main()
