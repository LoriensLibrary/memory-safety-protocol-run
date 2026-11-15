"""Second judge pass for Task 1: the false memories a session was NOT asking about.

Paper 5 (6.3.3) defines citation and action per session over ANY seeded false memory, not only the one the probe
targets. judge.py scores the target. This scores, with the same blind prompt and parser:
  other     every other seeded false inference CAMA returned in that session
  control   one seeded false inference that was not returned (chosen by hash), in a fixed sample of sessions,
            to measure how often the judge says yes when the memory was never in front of the model

  python memory_protocol/judge_others.py --run runs_mp/t1_gemma431bit_paid --judge gemma-4-31b-it --ceiling 1 [--controls 200] [--interval 3]
"""
import argparse, hashlib, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "tools"))
import guard, run as mainrun   # noqa: E402
import judge as J              # noqa: E402
import items_t1                # noqa: E402

TEXT = {f[1]: f[0] for f in items_t1.FALSE}
INFER = {f[0]: f[1] for f in items_t1.FALSE}


def h(*p):
    return hashlib.sha256("|".join(str(x) for x in p).encode()).hexdigest()


def pairs(rows, n_controls):
    out = []
    for r in rows:
        got = {TEXT[m["text"]] for m in (r.get("retrieved") or []) if m.get("text") in TEXT}
        for other in sorted(got - {r["item"]}):
            out.append((r, other, "other"))
    pool = sorted(rows, key=lambda r: h("control", r["condition"], r["item"], r["phase"]))[:n_controls]
    for r in pool:
        got = {TEXT[m["text"]] for m in (r.get("retrieved") or []) if m.get("text") in TEXT}
        cands = sorted((i for i in INFER if i != r["item"] and i not in got), key=lambda i: h("pick", r["condition"], r["item"], r["phase"], i))
        out.append((r, cands[0], "control"))
    return out


def main():
    p = argparse.ArgumentParser(); p.add_argument("--run", required=True); p.add_argument("--judge", required=True)
    p.add_argument("--ceiling", type=float, required=True); p.add_argument("--controls", type=int, default=200); p.add_argument("--interval", type=float, default=3.0)
    a = p.parse_args()
    run_dir = a.run if os.path.isabs(a.run) else os.path.join(ROOT, a.run)
    rows = [r for r in mainrun.read_jsonl(os.path.join(run_dir, "traces.jsonl")) if r["status"] == "complete" and r.get("reply")]
    todo = pairs(rows, a.controls)
    tag = a.judge.replace("-", "").replace(".", "")[:12]
    out_path = os.path.join(run_dir, f"judgments_others_{tag}.jsonl")
    done = {(r["condition"], r["item"], r["phase"], r["other"], r["kind"]) for r in mainrun.read_jsonl(out_path)} if os.path.exists(out_path) else set()
    if not os.environ.get("ADAPTION_API_KEY"):
        os.environ["ADAPTION_API_KEY"] = open(mainrun.DEFAULT_KEY, encoding="utf-8-sig").read().strip()
    rawdir = os.path.join(run_dir, f"raw_judge_others_{tag}"); os.makedirs(rawdir, exist_ok=True)
    ledger = os.path.join(run_dir, f"ledger_judge_others_{tag}.jsonl")
    g = guard.SpendGuard(a.judge, a.ceiling, len(todo) + max(20, len(todo) // 10), ledger, min_interval=a.interval, rawdir=rawdir)
    if os.path.exists(ledger) and done:
        spend = attempts = ncalls = 0
        for r in mainrun.read_jsonl(ledger):
            spend = r.get("spend_after", r.get("spend_after_debit", spend)); attempts = max(attempts, r.get("attempt", 0)); ncalls = max(ncalls, r.get("call", 0))
        g.restore(spend, attempts, ncalls)
    mainrun.hold_awake()
    print(f"{len(todo)} pairs ({sum(k == 'other' for _, _, k in todo)} other, {sum(k == 'control' for _, _, k in todo)} control), {len(done)} already done", flush=True)
    n = 0; t0 = time.time()
    with open(out_path, "a", encoding="utf-8") as f:
        for r, other, kind in todo:
            if (r["condition"], r["item"], r["phase"], other, kind) in done: continue
            j = dict(condition=r["condition"], item=r["item"], phase=r["phase"], other=other, kind=kind, judge=a.judge,
                     prompt_sha=hashlib.sha256(J.SYSTEM.encode()).hexdigest()[:12])
            try:
                system, user = J.request(dict(false_inference=INFER[other], probe=r["probe"], reply=r["reply"]))
                rec = g.send(system, user, 6000); v = J.parse(rec["text"]); j.update(raw=rec["text"][:300])
                j.update(status="complete", **v) if v else j.update(status="invalid")
            except guard.BudgetStop as e:
                print("budget stop:", e); break
            except guard.CallFailed as e:
                j.update(status="error", error=str(e))
            f.write(json.dumps(j) + "\n"); f.flush(); n += 1
            if n % 50 == 0: print(f"  {n} judged, {g.spend:.4f} credits, {time.time() - t0:.0f}s", flush=True)
    print(json.dumps(dict(judged=n, out=out_path, spend=round(g.spend, 6))))


if __name__ == "__main__":
    main()
