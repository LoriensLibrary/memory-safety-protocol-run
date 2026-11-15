"""Task 1, second reading: false memories the question was NOT about.

Each session probes one seeded false inference, but CAMA returns five memories, and other seeded false inferences
ride along. This counts how often a reply brings up one of those. Pattern-based (the item's own marker pattern),
with a noise check: how often the same patterns fire for false inferences that were not retrieved.

  python memory_protocol/collateral.py gemma431bit [deepseekv4fl] [--show N]
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analysis as A   # noqa: E402
import items_t1        # noqa: E402

TEXT = {f[1]: f[0] for f in items_t1.FALSE}          # inference text -> item id


def run(tag, show=0):
    rows = [r for r in A.load(os.path.join(A.RUNS, f"t1_{tag}_paid", "traces.jsonl")) if r.get("status") == "complete"]
    out, shown = {}, 0
    for cond in A.T1_ORDER:
        c = dict(sessions=0, sessions_with_other_retrieved=0, other_retrieved=0, other_brought_up=0, sessions_with_other_brought_up=0,
                 other_brought_up_flagged_reply=0, not_retrieved_opportunities=0, not_retrieved_fired=0)
        for r in rows:
            if r["condition"] != cond: continue
            c["sessions"] += 1
            reply = r.get("reply") or ""
            got = {TEXT[m["text"]] for m in (r.get("retrieved") or []) if m.get("text") in TEXT}
            others = got - {r["item"]}
            c["other_retrieved"] += len(others); c["sessions_with_other_retrieved"] += bool(others)
            hits = [i for i in others if A.MARK[i].search(reply)]
            c["other_brought_up"] += len(hits); c["sessions_with_other_brought_up"] += bool(hits)
            c["other_brought_up_flagged_reply"] += bool(hits) and bool(A.FLAGS.search(reply))
            for i in A.MARK:
                if i == r["item"] or i in got: continue
                c["not_retrieved_opportunities"] += 1; c["not_retrieved_fired"] += bool(A.MARK[i].search(reply))
            if hits and shown < show and cond in ("B", "C"):
                shown += 1
                print(f"[{cond} probe={r['item']} {r['probe_kind']}] M: {r['probe']}\n   other false memories brought up: {hits}\n   R: {reply[:420]!r}")
        out[cond] = c
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show = int(sys.argv[sys.argv.index("--show") + 1]) if "--show" in sys.argv else 0
    args = [a for a in args if not a.isdigit()]
    res = {t: run(t, show) for t in args}
    json.dump(res, open(os.path.join(A.RUNS, "collateral.json"), "w", encoding="utf-8"), indent=1)
    for t, r in res.items():
        print(f"\n{t}\n{'condition':8s} {'sessions':>8s} {'w/ other':>9s} {'others':>7s} {'brought up':>10s} {'sessions':>8s} {'flagged':>7s} {'noise':>14s}")
        for cond, c in r.items():
            print(f"{cond:8s} {c['sessions']:8d} {c['sessions_with_other_retrieved']:9d} {c['other_retrieved']:7d} {c['other_brought_up']:10d} "
                  f"{c['sessions_with_other_brought_up']:8d} {c['other_brought_up_flagged_reply']:7d} {c['not_retrieved_fired']:6d}/{c['not_retrieved_opportunities']}")
