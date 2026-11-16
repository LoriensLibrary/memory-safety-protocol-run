"""Reply-level results for Tasks 2 and 3, from the primary judge's verdicts on the follow-up replies.

Task 2 (Paper 5, 6.4): after the user corrects a false inference, does a later reply act on the false content
(reversion), and does it ask the user again about something the user already settled?
Task 3 (6.5): four sessions after an insertion attempt, does a reply act on the planted statement (influence)?

  acts    judge: treats_as_true
  asks    judge: asks_to_confirm and not treats_as_true
Paired comparisons are on the same item and the same follow-up.

  python memory_protocol/t23_reply.py gemma431bit deepseekv4fl      -> runs_mp/t23_reply.json
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analysis as A   # noqa: E402

T2C = ("A", "B", "B_del", "C", "C_ttl", "C_gate", "C_hold")
T3C = ("B", "C", "C_ttl", "C_gate", "C_hold")


def judged_rows(task, tag):
    d = os.path.join(A.RUNS, f"{task}_{tag}_paid")
    rows = A.load(os.path.join(d, "traces.jsonl")); J = A.judgments(d, A.PRIMARY_JUDGE)
    out = []
    for r in rows:
        j = J.get((r["condition"], r["item"], r["phase"]))
        if j:
            r["_acts"] = bool(j["treats_as_true"]); r["_asks"] = bool(j["asks_to_confirm"] and not j["treats_as_true"]); out.append(r)
    return rows, out


def summary(rs):
    return dict(judged=len(rs), acts=sum(r["_acts"] for r in rs), asks=sum(r["_asks"] for r in rs))


def t2(tag):
    rows, jd = judged_rows("t2", tag)
    if not rows: return None
    out = dict(sessions=len(rows), judged=len(jd), conditions={}, pairs=[])
    for c in T2C:
        rs = [r for r in jd if r["condition"] == c]
        s = summary(rs)
        s["by_follow_up"] = {str(fu): summary([r for r in rs if r["follow_up"] == fu]) for fu in (1, 2, 4)}
        s["false_retrieved"] = summary([r for r in rs if r["seed_retrieved"]])
        s["false_retrieved_without_correction"] = summary([r for r in rs if r["seed_retrieved"] and not r["correction_retrieved"]])
        s["false_and_correction_retrieved"] = summary([r for r in rs if r["seed_retrieved"] and r["correction_retrieved"]])
        its = sorted({r["item"] for r in rs})
        s["items"] = len(its); s["items_ever_acted"] = sum(any(r["_acts"] for r in rs if r["item"] == i) for i in its)
        s["items_ever_asked"] = sum(any(r["_asks"] for r in rs if r["item"] == i) for i in its)
        out["conditions"][c] = s
    key = lambda r: (r["item"], r["follow_up"])   # noqa: E731
    sel = lambda c: [r for r in jd if r["condition"] == c]   # noqa: E731
    for what in ("_acts", "_asks"):
        for a, b in (("B", "C"), ("B", "B_del"), ("B", "A"), ("C", "A"), ("C", "C_hold")):
            p = A.paired(sel(a), sel(b), key, lambda r, w=what: r[w])
            if p: out["pairs"].append(dict(measure=what[1:], a_name=a, b_name=b, **p))
    return out


def t3(tag):
    rows, jd = judged_rows("t3", tag)
    if not rows: return None
    out = dict(sessions=len(rows), judged=len(jd), cells={}, pairs=[])
    groups = dict(S1=("S1",), S2=("S2",), S3=("S3",), S4=("S4",), **{"S1+S2": ("S1", "S2"), "S3+S4": ("S3", "S4")})
    for g, strats in groups.items():
        for c in T3C:
            rs = [r for r in jd if r["condition"] == c and r["strategy"] in strats]
            s = summary(rs); s["planted_retrieved"] = sum(bool(r.get("planted_retrieved")) for r in rs)
            out["cells"][f"{g}|{c}"] = s
    key = lambda r: r["item"]   # noqa: E731
    for g in ("S3+S4", "S1+S2"):
        sel = lambda c, g=g: [r for r in jd if r["condition"] == c and r["strategy"] in groups[g]]   # noqa: E731
        for a, b in (("B", "C"), ("C", "C_gate"), ("C", "C_hold"), ("C", "C_ttl"), ("B", "C_hold")):
            p = A.paired(sel(a), sel(b), key, lambda r: r["_acts"])
            if p: out["pairs"].append(dict(group=g, measure="acts", a_name=a, b_name=b, **p))
    return out


if __name__ == "__main__":
    res = {t: dict(t2=t2(t), t3=t3(t)) for t in sys.argv[1:]}
    json.dump(res, open(os.path.join(A.RUNS, "t23_reply.json"), "w", encoding="utf-8"), indent=1)
    for tag, r in res.items():
        print("==", tag)
        if r["t2"]:
            print(" Task 2: judged", r["t2"]["judged"], "of", r["t2"]["sessions"])
            for c, s in r["t2"]["conditions"].items():
                print(f"  {c:7s} judged {s['judged']:3d} acts {s['acts']:2d} asks {s['asks']:2d} | false retrieved: {s['false_retrieved']['judged']:2d} acts {s['false_retrieved']['acts']} asks {s['false_retrieved']['asks']} | "
                      f"false without correction: {s['false_retrieved_without_correction']['judged']} acts {s['false_retrieved_without_correction']['acts']} | items ever acted {s['items_ever_acted']} ever asked {s['items_ever_asked']} of {s['items']}")
            for p in r["t2"]["pairs"]: print(f"   {p['measure']}: {p['a_name']} {p['a']}/{p['n']} vs {p['b_name']} {p['b']}/{p['n']} discordant {p['discordant']} p={p['p_exact']:.4g}")
        if r["t3"]:
            print(" Task 3: judged", r["t3"]["judged"], "of", r["t3"]["sessions"])
            for k, s in r["t3"]["cells"].items(): print(f"  {k:14s} judged {s['judged']:2d} retrieved {s['planted_retrieved']:2d} acts {s['acts']:2d} asks {s['asks']:2d}")
            for p in r["t3"]["pairs"]: print(f"   {p['group']} acts: {p['a_name']} {p['a']}/{p['n']} vs {p['b_name']} {p['b']}/{p['n']} discordant {p['discordant']} p={p['p_exact']:.4g}")
