"""Total Adaption spend recorded in every ledger under runs_mp (and the first study's runs), with failure counts.

  python memory_protocol/spend.py [--errors]
"""
import collections, glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
total = 0.0
for path in sorted(glob.glob(os.path.join(ROOT, "runs*", "**", "ledger*.jsonl"), recursive=True)):
    last, ev, errs = 0.0, collections.Counter(), collections.Counter()
    for line in open(path, encoding="utf-8", errors="replace"):
        try: r = json.loads(line)
        except json.JSONDecodeError: continue
        last = r.get("spend_after", r.get("spend_after_debit", last)) or last
        ev[r.get("event") or "row"] += 1
        if r.get("error"): errs[str(r["error"])[:90]] += 1
    total += last
    rel = os.path.relpath(path, ROOT)
    print(f"{last:8.4f}  {rel}  {dict(ev)}")
    if "--errors" in sys.argv:
        for e, n in errs.most_common(4): print(f"            {n} x {e}")
print(f"{total:8.4f}  TOTAL credits recorded")
