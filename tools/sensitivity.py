"""POST HOC, NOT PREREGISTERED. A second reading of replies the strict scorer marked invalid.

  python tools/sensitivity.py --run runs/heldout_gemma31_paid --freeze holdout/heldout_gemma31

The strict scorer rejects a reply whose JSON breaks the contract. In the held-out runs most such replies had a readable
decision and integer answer and a malformed sources list (ids written without quotes). This script reads the decision
and the answer from those replies with a fixed pattern, ignores the sources list, and recomputes the tables and the
seven comparisons. The preregistered analysis is unchanged; this only shows whether the invalid replies could move it.
"""
import argparse, glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import items, score, analyze   # noqa: E402

DEC = re.compile(r'"decision"\s*:\s*"(answer|abstain)"')
ANS = re.compile(r'"answer"\s*:\s*(-?\d+|null)\s*[,}]')


def lenient(text):
    d, a = DEC.findall(text or ""), ANS.findall(text or "")
    if len(d) != 1 or len(a) != 1: return None
    if d[0] == "answer" and a[0] != "null": return dict(decision="answer", answer=int(a[0]), sources=[])
    if d[0] == "abstain" and a[0] == "null": return dict(decision="abstain", answer=None, sources=[])
    return None


def main():
    p = argparse.ArgumentParser(); p.add_argument("--run", required=True); p.add_argument("--freeze", required=True)
    a = p.parse_args()
    run_dir = a.run if os.path.isabs(a.run) else os.path.join(ROOT, a.run)
    fdir = a.freeze if os.path.isabs(a.freeze) else os.path.join(ROOT, a.freeze)
    frz, inst, rows = analyze.load(run_dir, fdir)
    key = {}
    for it in inst:
        for arm in items.MODEL_ARMS:
            for stage in ((1, 2) if arm == "lookup" else (1,)):
                r = items.build_request(it, arm, stage)
                key[(r["system"], r["user"])] = (it["tid"], arm, stage)
    last = {}                                             # final call text per slot (a retried call keeps the later file)
    for f in sorted(glob.glob(os.path.join(run_dir, "raw", "call_*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        k = key.get((d["system"], d["user"]))
        if k: last[(k[0], k[1])] = d["response"]["text"]
    by_tid = {it["tid"]: it for it in inst}
    recovered, still = [], 0
    for (tid, arm), r in list(rows.items()):
        if r["status"] != "invalid": continue
        rep = lenient(last.get((tid, arm)))
        if rep is None: still += 1; continue
        new = dict(r, status="complete", decision=rep["decision"], answer=rep["answer"], sources=[], lenient=True, **score.score(by_tid[tid], rep))
        new["cited_bad"] = None
        rows[(tid, arm)] = new; recovered.append((tid, arm, r["invalid_reason"], new["outcome"]))
    table, claims = analyze.analyze(frz, inst, rows)
    out = dict(note="post hoc, not preregistered", recovered=len(recovered), still_invalid=still,
               recovered_outcomes={o: sum(1 for x in recovered if x[3] == o) for o in analyze.OUTCOMES}, claims=claims,
               table={f"{v}|{arm}": dict(c) for (v, arm), c in table.items()})
    json.dump(out, open(os.path.join(run_dir, "sensitivity.json"), "w", encoding="utf-8"), indent=1)
    print(f"recovered {len(recovered)} of {len(recovered) + still} invalid replies:", out["recovered_outcomes"])
    for c in claims:
        print(f"  {c['claim'][:2]}  {c['arm_a']} {c['rate_a']:.3f} vs {c['arm_b']} {c['rate_b']:.3f}  diff {c['diff']:+.3f}  CI [{c['ci95'][0]:+.3f}, {c['ci95'][1]:+.3f}]  Holm p {c['p_holm']:.3g}")


if __name__ == "__main__":
    main()
