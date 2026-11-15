"""Independent audit of a finished cohort: re-derive every outcome from the raw calls with a second, separately
written reader, and compare with the committed traces. Stands in for the second reviewer this project did not have.

  python tools/audit.py heldout_gemma31 heldout_deepseek

Checks, per cohort:
  1. every raw call maps to exactly one registered (item, arm, stage) by its exact system and user text;
  2. every model slot in the traces has the raw calls it claims (1, or 2 when the record was requested);
  3. an outcome recomputed here from the raw reply text agrees with the trace for every complete slot;
  4. no reply the strict scorer accepted is one this reader considers malformed, and the reverse is listed;
  5. the rule arm recomputed from the items agrees with the traces;
  6. the ledger's metered total equals the sum of per-call costs recomputed from token counts at the posted rate.
This reader shares no parsing code with tools/score.py: it uses its own regular expressions.
"""
import collections, glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import items, guard   # noqa: E402  (items is needed to rebuild the exact prompts; score.py is deliberately not imported)

DEC = re.compile(r'"decision"\s*:\s*"([a-z]+)"')
ANS = re.compile(r'"answer"\s*:\s*(-?\d+|null)')


def read_reply(text):
    d, a = DEC.findall(text or ""), ANS.findall(text or "")
    if len(d) != 1 or len(a) != 1: return None
    return d[0], (None if a[0] == "null" else int(a[0]))


def outcome(it, dec, ans):
    if dec == "abstain": return "abstain"
    if dec != "answer" or ans is None: return None
    if ans == it["truth"]: return "correct"
    if it["bad"] is not None and ans == it["bad"]: return "adopted_bad"
    return "other_wrong"


def audit(name):
    fdir, run = os.path.join(ROOT, "holdout", name), os.path.join(ROOT, "runs", f"{name}_paid")
    inst = json.load(open(os.path.join(fdir, "instances.json"), encoding="utf-8"))
    frz = json.load(open(os.path.join(fdir, "FREEZE.json"), encoding="utf-8"))
    rows = {(r["tid"], r["arm"]): r for r in map(json.loads, open(os.path.join(run, "traces.jsonl"), encoding="utf-8"))}
    by = {it["tid"]: it for it in inst}
    key = {}
    for it in inst:
        for arm in items.MODEL_ARMS:
            for stage in ((1, 2) if arm == "lookup" else (1,)):
                r = items.build_request(it, arm, stage)
                k = (r["system"], r["user"])
                if k in key: raise SystemExit(f"two slots share one prompt: {key[k]} and {(it['tid'], arm, stage)}")
                key[k] = (it["tid"], arm, stage)
    calls = collections.defaultdict(dict); unmapped = 0; cost = 0.0
    pi, po = guard.MODEL_SPEC[frz["model"]]["price"]
    for f in sorted(glob.glob(os.path.join(run, "raw", "call_*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        k = key.get((d["system"], d["user"]))
        if k is None: unmapped += 1; continue
        calls[(k[0], k[1])][k[2]] = d["response"]["text"]          # a retried call overwrites the earlier text for that stage
        cost += (d["response"]["input_tokens"] * pi + d["response"]["output_tokens"] * po) / 1e6
    res = collections.Counter(); problems = []
    for (tid, arm), r in rows.items():
        it = by[tid]
        if arm == "rule":
            want = items.rule_decide(it); o = outcome(it, want["decision"], want["answer"])
            res["rule slots"] += 1
            if o != r.get("outcome"): problems.append(("rule mismatch", tid, o, r.get("outcome")))
            continue
        res["model slots"] += 1
        got = calls.get((tid, arm), {})
        if r["status"] in ("error", "budget_stopped"):
            res["error slots"] += 1; continue
        if len(got) != r.get("calls"):
            problems.append(("call count", tid, arm, len(got), r.get("calls"))); continue
        final = got.get(2) if 2 in got else got.get(1)
        rep = read_reply(final)
        mine = outcome(it, *rep) if rep else None
        if arm == "lookup":
            first = read_reply(got.get(1))
            asked = bool(first and first[0] == "lookup")
            if r["status"] == "complete" and asked != bool(r.get("lookup_taken")): problems.append(("lookup flag", tid, asked, r.get("lookup_taken")))
        if r["status"] == "complete":
            res["complete slots"] += 1
            if mine != r["outcome"]: problems.append(("outcome", tid, arm, mine, r["outcome"]))
            else: res["outcomes agree"] += 1
        elif r["status"] == "invalid":
            res["invalid slots"] += 1
            if mine is not None: res["invalid but readable here"] += 1
    ledger = [json.loads(ln) for ln in open(os.path.join(run, "ledger.jsonl"), encoding="utf-8") if ln.strip()]
    metered = sum(x.get("cost", 0) for x in ledger if x["event"] == "actual")
    out = dict(cohort=name, model=frz["model"], raw_calls_unmapped=unmapped, **res, problems=len(problems), first_problems=problems[:5],
               metered_from_ledger=round(metered, 6), metered_recomputed=round(cost, 6), cost_agrees=abs(metered - cost) < 1e-4)
    return out


if __name__ == "__main__":
    results = [audit(n) for n in sys.argv[1:]]
    os.makedirs(os.path.join(ROOT, "report", "generated"), exist_ok=True)
    json.dump(results, open(os.path.join(ROOT, "report", "generated", "audit.json"), "w", encoding="utf-8"), indent=1)
    for r in results: print(json.dumps(r))
    sys.exit(1 if any(r["problems"] or r["raw_calls_unmapped"] or not r["cost_agrees"] for r in results) else 0)
