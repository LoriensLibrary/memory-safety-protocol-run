"""Print what the assistant chose to save in Task 3, stage 1, and the source it gave.

  python memory_protocol/peek_t3_writes.py deepseekv4fl S4 [--w 200]
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analysis as A   # noqa: E402
import items_t3        # noqa: E402

tag, strat = sys.argv[1], sys.argv[2]
w = int(sys.argv[sys.argv.index("--w") + 1]) if "--w" in sys.argv else 200
planted = {a[0]: a[3] for a in items_t3.ATTACKS}
for x in A.load(os.path.join(A.RUNS, f"t3_{tag}_paid", "stage1.jsonl")):
    if x["strategy"] != strat: continue
    print(f"[{x['item']} {x['status']}] planted: {planted[x['item']]}")
    print("   reply:", repr((x.get("reply") or "")[:w]))
    for text, src in (x.get("saves") or []): print(f"   SAVE [{src}] {text[:150]}")
