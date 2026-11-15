"""Compact console view of runs_mp/results.json, Task 1.   python memory_protocol/show.py [tag ...]"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(os.path.dirname(HERE), "runs_mp", "results.json"), encoding="utf-8"))
for tag in (sys.argv[1:] or list(R)):
    t = R[tag]["t1"]
    if not t: print(tag, "no t1"); continue
    print(f"\n== {tag}: sessions {t['sessions']}, not complete {t['not_complete']}, judged {t['judged']}")
    head = "retr mark said flag | judged ment  act check contra"
    row = lambda b: f"{b['retrieved']:4d} {b['marker']:4d} {b['user_said']:4d} {b['flags']:4d} | {b['judged']:6d} {b['mentions']:4d} {b['action']:4d} {b['check']:5d} {b['contradicts']:6d}"   # noqa: E731
    print(f"{'cond':6s} ph   n  {head}")
    for b in t["table"]: print(f"{b['condition']:6s} {b['phase']}  {b['n']:3d}  {row(b)}")
    print(f"{'cond':6s} kind     n  {head}")
    for b in t["by_kind"]: print(f"{b['condition']:6s} {b['kind']:6s} {b['n']:3d}  {row(b)}")
    print("by whether a teaching contradicts the false inference:")
    for b in t["by_contradiction"]: print(f"{b['condition']:6s} {str(b['contradicted_by_teaching']):5s} {b['n']:3d}  {row(b)}")
    for p in t["pairs"]:
        print(f"  {p['test']}: {p['a']}/{p['n']} vs {p['b']}/{p['n']}, diff {100 * p['diff']:.0f} [{100 * p['ci95'][0]:.0f}, {100 * p['ci95'][1]:.0f}], discordant {p['discordant']}, p={p['p_exact']:.3g}")
    print("  judge agreement:", t["agreement"]); print("  pattern vs judge (mentions):", t["pattern_vs_judge"])
