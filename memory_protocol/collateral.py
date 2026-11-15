"""Task 1, session reading: any seeded false memory in the session, as Paper 5 (6.3.3) words its rates.

Each session probes one seeded false inference (the target), but CAMA returns five memories, and other seeded false
inferences ride along. This reads every session for all of them.

  pattern columns   the item's own marker pattern on the reply; needs no judge
  judge columns     judge.py's verdict on the target plus judge_others.py's verdicts on the others, same blind prompt
  controls          judge verdicts on false inferences that were never retrieved (how often the judge says yes anyway)
  repeat            C against D: same store, same retrieved lists, so any difference is run-to-run variation

  python memory_protocol/collateral.py gemma431bit [deepseekv4fl] [--show N] [--judge gemma431bit]
Writes runs_mp/collateral.json.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analysis as A   # noqa: E402
import items_t1        # noqa: E402

TEXT = {f[1]: f[0] for f in items_t1.FALSE}          # inference text -> item id
JK = ("mentions", "treats_as_true", "asks_to_confirm")


def run(tag, judge, show=0):
    run_dir = os.path.join(A.RUNS, f"t1_{tag}_paid")
    rows = [r for r in A.load(os.path.join(run_dir, "traces.jsonl")) if r.get("status") == "complete"]
    if not rows: return None
    jt = A.judgments(run_dir, judge)
    jo, ctrl = {}, []
    for j in A.load(os.path.join(run_dir, f"judgments_others_{judge}.jsonl")):
        if j.get("status") != "complete": continue
        if j["kind"] == "other": jo[(j["condition"], j["item"], j["phase"], j["other"])] = j
        else: ctrl.append(j)
    shown = 0
    for r in rows:
        reply = r.get("reply") or ""
        got = {TEXT[m["text"]] for m in (r.get("retrieved") or []) if m.get("text") in TEXT}
        others = sorted(got - {r["item"]})
        r["_others"] = others; r["_any_retrieved"] = bool(got)
        r["_other_hits"] = [i for i in others if A.MARK[i].search(reply)]
        r["_noise_opps"] = sum(1 for i in A.MARK if i != r["item"] and i not in got)
        r["_noise_fired"] = sum(1 for i in A.MARK if i != r["item"] and i not in got and A.MARK[i].search(reply))
        tj = jt.get((r["condition"], r["item"], r["phase"])) if r["item"] in got else None
        oj = [jo.get((r["condition"], r["item"], r["phase"], i)) for i in others]
        r["_judged_all"] = (r["item"] not in got or tj is not None) and all(j is not None for j in oj)
        verdicts = ([tj] if tj else []) + [j for j in oj if j]
        for k in JK:
            r["_any_" + k] = any(v[k] for v in verdicts)
            r["_other_" + k] = any(j[k] for j in oj if j)
        r["_any_check_only"] = any(v["asks_to_confirm"] and not v["treats_as_true"] for v in verdicts) and not r["_any_treats_as_true"]
        if r["_other_hits"] and shown < show and r["condition"] in ("B", "C"):
            shown += 1
            print(f"[{r['condition']} probe={r['item']} {r['probe_kind']}] M: {r['probe']}\n   other false memories brought up: {r['_other_hits']}\n   R: {reply[:420]!r}")
    out = dict(judge=judge, target_judged=len(jt), others_judged=len(jo), conditions={}, pairs=[], repeat_C_vs_D=None, controls=None)
    for cond in A.T1_ORDER:
        rs = [r for r in rows if r["condition"] == cond]
        jd = [r for r in rs if r["_judged_all"]]
        out["conditions"][cond] = dict(
            sessions=len(rs), any_retrieved=sum(r["_any_retrieved"] for r in rs), sessions_with_other_retrieved=sum(bool(r["_others"]) for r in rs),
            other_retrieved=sum(len(r["_others"]) for r in rs), other_brought_up=sum(len(r["_other_hits"]) for r in rs),
            sessions_with_other_brought_up=sum(bool(r["_other_hits"]) for r in rs),
            noise_fired=sum(r["_noise_fired"] for r in rs), noise_opportunities=sum(r["_noise_opps"] for r in rs),
            judged_sessions=len(jd), any_cited=sum(r["_any_mentions"] for r in jd), any_action=sum(r["_any_treats_as_true"] for r in jd),
            any_check_only=sum(r["_any_check_only"] for r in jd), other_action=sum(r["_other_treats_as_true"] for r in jd),
            other_cited=sum(r["_other_mentions"] for r in jd))
    key = lambda r: (r["item"], r["phase"])   # noqa: E731
    sel = lambda c, judged: [r for r in rows if r["condition"] == c and (r["_judged_all"] or not judged)]   # noqa: E731
    tests = [("pattern: session brings up a false memory the question was not about", "_pat", False),
             ("judge: session acts on any seeded false memory", "_any_treats_as_true", True),
             ("judge: session acts on a false memory the question was not about", "_other_treats_as_true", True)]
    for label, field, judged in tests:
        pred = (lambda r: bool(r["_other_hits"])) if field == "_pat" else (lambda r, f=field: bool(r[f]))
        for a, b in (("B", "C"), ("C", "C_gate"), ("C", "C_hold"), ("B", "A"), ("C", "D")):
            p = A.paired(sel(a, judged), sel(b, judged), key, pred)
            if p and (not judged or p["n"] >= 20): out["pairs"].append(dict(test=label, a_name=a, b_name=b, **p))
    C = {key(r): r for r in rows if r["condition"] == "C"}; D = {key(r): r for r in rows if r["condition"] == "D"}
    ks = sorted(set(C) & set(D))
    if ks:
        out["repeat_C_vs_D"] = dict(pairs=len(ks), same_retrieved=sum([m["text"] for m in C[k]["retrieved"]] == [m["text"] for m in D[k]["retrieved"]] for k in ks),
                                    identical_reply_text=sum(C[k]["reply"] == D[k]["reply"] for k in ks),
                                    target_marker_differs=sum(bool(A.MARK[k[0]].search(C[k]["reply"] or "")) != bool(A.MARK[k[0]].search(D[k]["reply"] or "")) for k in ks))
    if ctrl:
        out["controls"] = dict(n=len(ctrl), **{k: sum(j[k] for j in ctrl) for k in JK})
    return out


if __name__ == "__main__":
    argv = sys.argv[1:]
    show = int(argv[argv.index("--show") + 1]) if "--show" in argv else 0
    judge = argv[argv.index("--judge") + 1] if "--judge" in argv else A.PRIMARY_JUDGE
    skip = set()
    for flag in ("--show", "--judge"):
        if flag in argv: skip |= {argv.index(flag), argv.index(flag) + 1}
    tags = [a for i, a in enumerate(argv) if i not in skip]
    res = {t: run(t, judge, show) for t in tags}
    json.dump(res, open(os.path.join(A.RUNS, "collateral.json"), "w", encoding="utf-8"), indent=1)
    for t, r in res.items():
        if not r: print(t, "no run"); continue
        print(f"\n{t}  (judge {judge}: {r['target_judged']} target verdicts, {r['others_judged']} other verdicts)")
        print(f"{'cond':7s} {'sess':>4s} {'anyRet':>6s} {'others':>6s} {'broughtUp':>9s} {'sess':>4s} {'noise':>9s} | {'judged':>6s} {'cited':>5s} {'action':>6s} {'checkOnly':>9s} {'otherAct':>8s}")
        for cond, c in r["conditions"].items():
            print(f"{cond:7s} {c['sessions']:4d} {c['any_retrieved']:6d} {c['other_retrieved']:6d} {c['other_brought_up']:9d} {c['sessions_with_other_brought_up']:4d} "
                  f"{c['noise_fired']:4d}/{c['noise_opportunities']:<4d} | {c['judged_sessions']:6d} {c['any_cited']:5d} {c['any_action']:6d} {c['any_check_only']:9d} {c['other_action']:8d}")
        for p in r["pairs"]:
            print(f"  {p['test']}: {p['a_name']} {p['a']}/{p['n']} vs {p['b_name']} {p['b']}/{p['n']}, diff {100 * p['diff']:.0f} pts [{100 * p['ci95'][0]:.0f}, {100 * p['ci95'][1]:.0f}], discordant {p['discordant']}, p={p['p_exact']:.4g}")
        print("  repeat C vs D:", r["repeat_C_vs_D"]); print("  controls:", r["controls"])
