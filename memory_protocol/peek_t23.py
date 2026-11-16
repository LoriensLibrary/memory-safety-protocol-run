"""Print real replies from a Task 2 or Task 3 run with the judge's verdict beside them.

  python memory_protocol/peek_t23.py t2 gemma431bit --cond B [--act 1] [--n 8] [--w 260]
  python memory_protocol/peek_t23.py t3 gemma431bit --cond C --strategy S4
"""
import argparse, collections, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analysis as A   # noqa: E402

p = argparse.ArgumentParser(); p.add_argument("task"); p.add_argument("tag"); p.add_argument("--cond"); p.add_argument("--strategy")
p.add_argument("--act", type=int); p.add_argument("--n", type=int, default=8); p.add_argument("--w", type=int, default=260)
a = p.parse_args()
d = os.path.join(A.RUNS, f"{a.task}_{a.tag}_paid")
rows = A.load(os.path.join(d, "traces.jsonl")); J = A.judgments(d, A.PRIMARY_JUDGE)
c = collections.Counter()
for r in rows:
    j = J.get((r["condition"], r["item"], r["phase"]))
    if j: c[(r["condition"], r.get("follow_up", r.get("strategy")), "acts" if j["treats_as_true"] else ("asks" if j["asks_to_confirm"] else "no"))] += 1
for k in sorted(c, key=str): print(k, c[k])
shown = 0
for r in rows:
    j = J.get((r["condition"], r["item"], r["phase"]))
    if a.cond and r["condition"] != a.cond: continue
    if a.strategy and r.get("strategy") != a.strategy: continue
    if a.act is not None and (not j or bool(j["treats_as_true"]) != bool(a.act)): continue
    if shown >= a.n: break
    shown += 1
    extra = f"fu{r['follow_up']} false_retr={r['seed_retrieved']} corr_retr={r['correction_retrieved']}" if a.task == "t2" else f"{r['strategy']} planted_retr={r.get('planted_retrieved')} status={r.get('planted_status')}"
    stmt = r.get("false_inference") or r.get("statement") or ""
    print(f"[{r['condition']} {r['item']} {extra} judge={'none' if not j else ('acts' if j['treats_as_true'] else 'asks' if j['asks_to_confirm'] else 'no')}] S: {stmt} | M: {r['probe'][:90]}")
    print("   R:", repr((r.get("reply") or "")[: a.w]))
