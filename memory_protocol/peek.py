"""Print real replies from a Task 1 run, so a number can be read before it is believed.

  python memory_protocol/peek.py gemma431bit --cond C --kind task --retrieved 1 --phase 1 [--mark 1] [--said 1] [--flag 1] [--n 20] [--w 330]
"""
import argparse, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analysis as A   # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("tag"); p.add_argument("--cond"); p.add_argument("--kind"); p.add_argument("--phase", type=int)
p.add_argument("--retrieved", type=int); p.add_argument("--mark", type=int); p.add_argument("--said", type=int); p.add_argument("--flag", type=int)
p.add_argument("--act", type=int, help="judge: treats_as_true"); p.add_argument("--ask", type=int, help="judge: asks_to_confirm")
p.add_argument("--jm", type=int, help="judge: mentions"); p.add_argument("--contra", type=int, help="judge: contradicts")
p.add_argument("--n", type=int, default=20); p.add_argument("--w", type=int, default=330); p.add_argument("--shape", action="store_true")
a = p.parse_args()
rows = A.load(os.path.join(A.RUNS, f"t1_{a.tag}_paid", "traces.jsonl"))
J = A.judgments(os.path.join(A.RUNS, f"t1_{a.tag}_paid"), A.PRIMARY_JUDGE)
if a.shape:
    import json
    print(json.dumps(rows[120]["retrieved"][:2], ensure_ascii=False)[:600])
sel = []
for r in rows:
    reply = r.get("reply") or ""
    if a.cond and r["condition"] != a.cond: continue
    if a.kind and r["probe_kind"] != a.kind: continue
    if a.phase and r["phase"] != a.phase: continue
    if a.retrieved is not None and bool(r.get("seed_retrieved")) != bool(a.retrieved): continue
    if a.mark is not None and bool(A.MARK[r["item"]].search(reply)) != bool(a.mark): continue
    if a.said is not None and bool(A.USER_SAID.search(reply)) != bool(a.said): continue
    if a.flag is not None and bool(A.FLAGS.search(reply)) != bool(a.flag): continue
    j = J.get((r["condition"], r["item"], r["phase"]))
    want = dict(treats_as_true=a.act, asks_to_confirm=a.ask, mentions=a.jm, contradicts=a.contra)
    if any(v is not None for v in want.values()):
        if not j or any(v is not None and bool(j[k]) != bool(v) for k, v in want.items()): continue
    sel.append(r)
print(f"{len(sel)} replies match")
for r in sel[: a.n]:
    print(f"[{r['condition']} {r['item']} p{r['phase']} {r['probe_kind']} tag={r.get('seed_tag')} rank={r.get('seed_rank')}] S: {r['false_inference']} | M: {r['probe']}")
    print(f"   R: {(r.get('reply') or '')[: a.w]!r}")
