"""Assemble report/COMPANION.md from report/COMPANION.src.md and the result files, then render the PDF.

  python memory_protocol/analysis.py gemma431bit deepseekv4fl      (writes runs_mp/results.json)
  python memory_protocol/collateral.py gemma431bit deepseekv4fl    (writes runs_mp/collateral.json)
  python memory_protocol/handlabel.py score                        (writes runs_mp/judge_check.json)
  python tools/build_companion.py [--draft] [--no-pdf]

No number in the paper is typed by hand. The source holds two kinds of marker:
  {{TABLE_...}}            a whole table built here
  {{g|B.task|act}}         one count, "33 of 50": model g or d | condition[.recall|.task|.p1|.p2|.contra|.nocontra] | measure
                           measures: act check ment retr said flag (target reading); s_act s_cited s_retr s_other s_otherpat (session reading)
                           add |k for the count alone
--draft replaces markers that cannot be filled yet with [pending] instead of stopping.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REP = os.path.join(ROOT, "report")
RUNS = os.path.join(ROOT, "runs_mp")
sys.path.insert(0, HERE)
import build_report as BR   # noqa: E402  (CSS and the Edge path only)

TAG = dict(g="gemma431bit", d="deepseekv4fl")
MODEL = dict(g="gemma-4-31b-it", d="deepseek-v4-flash")
ORDER = ("A", "B", "C", "D", "C_ttl", "C_gate", "C_hold")
NAME = dict(A="A, no memory", B="B, naive memory", C="C, provenance labels (CAMA as shipped)", D="D, full safeguards (repeat of C here)",
            C_ttl="C with the paper's time-to-live", C_gate="C + read-time gate (added)", C_hold="C + hold until confirmed (added)", B_del="B + delete on correction")


def load(name):
    p = os.path.join(RUNS, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


R, S, JC = load("results.json"), load("collateral.json"), load("judge_check.json")


class Pending(Exception):
    pass


def block(m, sl):
    t = (R.get(TAG[m]) or {}).get("t1")
    if not t: raise Pending(m)
    cond, _, part = sl.partition(".")
    if part in ("recall", "task"):
        rows = [b for b in t["by_kind"] if b["condition"] == cond and b["kind"] == part]
    elif part in ("p1", "p2"):
        rows = [b for b in t["table"] if b["condition"] == cond and b["phase"] == int(part[1])]
    elif part in ("contra", "nocontra"):
        rows = [b for b in t["by_contradiction"] if b["condition"] == cond and b["contradicted_by_teaching"] == (part == "contra")]
    else:
        rows = [b for b in t["table"] if b["condition"] == cond]
    if not rows: raise Pending(sl)
    return {k: sum(b[k] for b in rows) for k in rows[0] if isinstance(rows[0][k], int) and not isinstance(rows[0][k], bool)}


def count(m, sl, meas):
    if meas.startswith("s_"):
        c = ((S.get(TAG[m]) or {}).get("conditions") or {}).get(sl)
        if not c: raise Pending(sl)
        k, n = dict(s_act=("any_action", "judged_sessions"), s_cited=("any_cited", "judged_sessions"), s_retr=("any_retrieved", "sessions"),
                    s_other=("other_action", "judged_sessions"), s_otherpat=("sessions_with_other_brought_up", "sessions"))[meas]
        if n == "judged_sessions" and c[n] < 0.95 * c["sessions"]: raise Pending(f"{sl} session reading not fully judged")
        return c[k], c[n]
    b = block(m, sl)
    k, n = dict(act=("action", "judged"), check=("check", "judged"), ment=("mentions", "judged"), retr=("retrieved", "n"),
                said=("user_said", "n"), flag=("flags", "n"))[meas]
    return b[k], b[n]


def cell(m, sl, meas):
    try:
        k, n = count(m, sl, meas); return f"{k}/{n}"
    except Pending:
        return "not judged yet"


def p_fmt(p):
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i]); adj = [0.0] * len(ps); run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - rank) * ps[i])); adj[i] = run
    return adj


def table_ttl():
    L = ["| Condition | Target retrieved, before | after | gemma acts, before | after | deepseek acts, before | after |", "|---|---|---|---|---|---|---|"]
    for c in ("B", "C", "C_ttl"):
        L.append(f"| {NAME[c]} | {cell('g', c + '.p1', 'retr')} | {cell('g', c + '.p2', 'retr')} | " + " | ".join(cell(m, c + s, "act") for m in "gd" for s in (".p1", ".p2")) + " |")
    return "\n".join(L)


def holm_max():
    worst = 0.0
    for m in "gd":
        t = (R.get(TAG[m]) or {}).get("t1")
        if not t or not t["pairs"]: raise Pending("pairs")
        worst = max(worst, max(holm([p["p_exact"] for p in t["pairs"]])))
    return f"{worst:.3f}"


def table_action():
    L = ["| Condition | gemma, all | recall | task | deepseek, all | recall | task |", "|---|---|---|---|---|---|---|"]
    for c in ("A", "B", "C", "D", "C_gate", "C_hold"):
        L.append(f"| {NAME[c]} | " + " | ".join(cell(m, c + s, "act") for m in "gd" for s in ("", ".recall", ".task")) + " |")
    return "\n".join(L)


def table_check():
    L = ["| Condition | gemma, recall | task | deepseek, recall | task |", "|---|---|---|---|---|"]
    for c in ("B", "C", "D", "C_gate"):
        L.append(f"| {NAME[c]} | " + " | ".join(cell(m, c + s, "check") for m in "gd" for s in (".recall", ".task")) + " |")
    return "\n".join(L)


def table_retrieval():
    L = ["| Condition | Target false memory retrieved, before the time-to-live | after | Any seeded false memory retrieved (session reading) |", "|---|---|---|---|"]
    for c in ORDER:
        L.append(f"| {NAME[c]} | {cell('g', c + '.p1', 'retr')} | {cell('g', c + '.p2', 'retr')} | {cell('g', c, 's_retr')} |")
    return "\n".join(L)


def table_session():
    L = ["| Condition | gemma: cited any | acted on any | acted on one the question was not about | deepseek: cited any | acted on any | acted on one the question was not about |", "|---|---|---|---|---|---|---|"]
    for c in ("B", "C", "D", "C_ttl", "C_gate", "C_hold"):
        L.append(f"| {NAME[c]} | " + " | ".join(cell(m, c, k) for m in "gd" for k in ("s_cited", "s_act", "s_other")) + " |")
    return "\n".join(L)


def table_pairs():
    L = ["| Comparison (same false memory, same probe) | Model | Pairs | First | Second | Difference, points [95%] | Improved / worsened | Exact p | Holm p |", "|---|---|---|---|---|---|---|---|---|"]
    for m in "gd":
        t = (R.get(TAG[m]) or {}).get("t1")
        if not t or not t["pairs"]: L.append(f"| not judged yet | {MODEL[m]} | | | | | | | |"); continue
        adj = holm([p["p_exact"] for p in t["pairs"]])
        for p, a in zip(t["pairs"], adj):
            L.append(f"| {p['test'].replace('action: ', '').replace('action ', '')} | {MODEL[m]} | {p['n']} | {p['a']} | {p['b']} | {100 * p['diff']:.0f} [{100 * p['ci95'][0]:.0f}, {100 * p['ci95'][1]:.0f}] | "
                     f"{p['discordant'][0]} / {p['discordant'][1]} | {p_fmt(p['p_exact'])} | {p_fmt(a)} |")
    return "\n".join(L)


def table_session_pairs():
    L = ["| Session-reading comparison | Model | Pairs | First | Second | Difference, points [95%] | Exact p |", "|---|---|---|---|---|---|---|"]
    for m in "gd":
        for p in ((S.get(TAG[m]) or {}).get("pairs") or []):
            L.append(f"| {p['test']}: {p['a_name']} against {p['b_name']} | {MODEL[m]} | {p['n']} | {p['a']} | {p['b']} | {100 * p['diff']:.0f} [{100 * p['ci95'][0]:.0f}, {100 * p['ci95'][1]:.0f}] | {p_fmt(p['p_exact'])} |")
    return "\n".join(L) if len(L) > 2 else "not judged yet"


def table_judge():
    if not JC: return "not judged yet"
    names = dict(mentions="mentions it", treats_as_true="acts as if true (action)", asks_to_confirm="flags it or asks (check)", contradicts="says it is not true")
    L = ["| Replies from | Judge | Compared | Question | Agree with reference label | Kappa | Agree, replies not marked borderline |", "|---|---|---|---|---|---|---|"]
    for key, c in sorted(JC["judges"].items()):
        if not c["compared"]: continue
        run, judge = key.split("|")
        for k, v in c["keys"].items():
            L.append(f"| {'gemma' if 'gemma' in run else 'deepseek'} run | {'gemma' if 'gemma' in judge else 'deepseek'} | {c['compared']} | {names[k]} | {v['agree']}/{v['n']} | {v['kappa']} | {v['agree_not_borderline']}/{v['n_not_borderline']} |")
    return "\n".join(L)


def table_two_judges():
    L = ["| Replies from | Scored by both judges | acts as if true | flags or asks | mentions | says not true |", "|---|---|---|---|---|---|"]
    for m in "gd":
        ag = ((R.get(TAG[m]) or {}).get("t1") or {}).get("agreement")
        if not ag: L.append(f"| {MODEL[m]} | not judged yet | | | | |"); continue
        n = ag["treats_as_true"]["n"]
        L.append(f"| {MODEL[m]} | {n} | {ag['treats_as_true']['agree']}/{n} | {ag['asks_to_confirm']['agree']}/{n} | {ag['mentions']['agree']}/{n} | {ag['contradicts']['agree']}/{n} |")
    return "\n".join(L)


def table_full(m):
    L = ["| Condition | Phase | Sessions | Target retrieved | Judged | Mentions | Acts | Flags or asks | Reply credits the user (pattern) |", "|---|---|---|---|---|---|---|---|---|"]
    t = (R.get(TAG[m]) or {}).get("t1")
    if not t: return "not judged yet"
    for b in t["table"]:
        L.append(f"| {NAME[b['condition']]} | {'before' if b['phase'] == 1 else 'after'} | {b['n']} | {b['retrieved']} | {b['judged']} | {b['mentions']} | {b['action']} | {b['check']} | {b['user_said']} |")
    return "\n".join(L)


def table_contra():
    L = ["| Condition | A teaching contradicts the false inference | gemma: acts | deepseek: acts |", "|---|---|---|---|"]
    for c in ("B", "C", "C_gate"):
        for part, label in ((".contra", "yes (14 inferences)"), (".nocontra", "no (36 inferences)")):
            L.append(f"| {NAME[c]} | {label} | {cell('g', c + part, 'act')} | {cell('d', c + part, 'act')} |")
    return "\n".join(L)


def table_repeat():
    L = ["| Model | Sessions paired (C, D) | Same five memories retrieved | Identical reply text | acts: C | acts: D |", "|---|---|---|---|---|---|"]
    for m in "gd":
        rp = (S.get(TAG[m]) or {}).get("repeat_C_vs_D")
        if not rp: L.append(f"| {MODEL[m]} | not judged yet | | | | |"); continue
        L.append(f"| {MODEL[m]} | {rp['pairs']} | {rp['same_retrieved']} | {rp['identical_reply_text']} | {cell(m, 'C', 'act')} | {cell(m, 'D', 'act')} |")
    return "\n".join(L)


def table_controls():
    L = ["| Replies from | Never-retrieved statements judged | judge says mentions | acts | flags or asks |", "|---|---|---|---|---|"]
    for m in "gd":
        c = (S.get(TAG[m]) or {}).get("controls")
        L.append(f"| {MODEL[m]} | {c['n']} | {c['mentions']} | {c['treats_as_true']} | {c['asks_to_confirm']} |" if c else f"| {MODEL[m]} | not judged yet | | | |")
    return "\n".join(L)


T2_ORDER = ("A", "B", "B_del", "C", "C_ttl", "C_gate", "C_hold")
STRAT = dict(S1="S1, false fact in passing", S2="S2, false fact in an update request", S3="S3, pressure to infer and store", S4="S4, instruction inside a document")


def t2_of(m):
    t = (R.get(TAG[m]) or {}).get("t2")
    if not t: raise Pending("Task 2 " + m)
    done = {c["condition"] for c in t["follow_ups"] if c["n"] == 24}
    if not all(c in done for c in T2_ORDER): raise Pending("Task 2 not complete " + m)
    return t


def table_t2(m):
    t = t2_of(m)
    judged = all(f["judged"] >= f["n"] - 1 for f in t["follow_ups"])
    L = ["| Condition | Contradicted false memory named by the check | removed or rejected | False memory retrieved in follow-ups (of 72) | Correction retrieved (of 72) | Reply acts on the false memory: 1 session later | 2 later | 4 later | False memories acted on at least once (of 24) |", "|---|---|---|---|---|---|---|---|---|"]
    for c in T2_ORDER:
        co = next((x for x in t["corrections"] if x["condition"] == c), None)
        fu = {f["after"]: f for f in t["follow_ups"] if f["condition"] == c}
        rv = next((x for x in t["reversion"] if x["condition"] == c), None)
        acts = [f"{fu[k]['reverted']}/{fu[k]['judged']}" if judged else "not judged yet" for k in (1, 2, 4)]
        L.append(f"| {NAME[c]} | {co['seed_named']}/{co['n']} | {co['seed_removed']}/{co['n']} | {sum(f['false_retrieved'] for f in fu.values())} | {sum(f['correction_retrieved'] for f in fu.values())} | "
                 + " | ".join(acts) + f" | {rv['ever_reverted'] if judged and rv else 'not judged yet'} |")
    return "\n".join(L)


def t2_num(m, cond, what):
    t = t2_of(m)
    co = next(x for x in t["corrections"] if x["condition"] == cond)
    fu = [f for f in t["follow_ups"] if f["condition"] == cond]
    if what in ("named", "removed", "check_failed"):
        return f"{co[dict(named='seed_named', removed='seed_removed', check_failed='check_failed')[what]]} of {co['n']}"
    if what == "false_retr": return f"{sum(f['false_retrieved'] for f in fu)} of {sum(f['n'] for f in fu)}"
    if what == "reverted":
        if any(f["judged"] < f["n"] - 1 for f in fu): raise Pending("Task 2 judge")
        return f"{sum(f['reverted'] for f in fu)} of {sum(f['judged'] for f in fu)}"
    if what == "ever":
        if any(f["judged"] < f["n"] - 1 for f in fu): raise Pending("Task 2 judge")
        rv = next(x for x in t["reversion"] if x["condition"] == cond); return f"{rv['ever_reverted']} of {rv['items']}"
    raise SystemExit("unknown Task 2 measure " + what)


def t3_of(m):
    t = (R.get(TAG[m]) or {}).get("t3")
    if not t or len(t["follow_up"]) < 20: raise Pending("Task 3 " + m)
    return t


def table_t2_db():
    ts = {m: t2_of(m) for m in "gd"}
    L = ["| Condition | gemma: contradicted false memory named by the check (of 24) | rejected or removed | false memory retrieved in follow-ups (of 72) | deepseek: named | rejected or removed | false memory retrieved in follow-ups (of 72) |", "|---|---|---|---|---|---|---|"]
    for c in ("B", "B_del", "C", "C_ttl", "C_gate", "C_hold"):
        cells = []
        for m in "gd":
            co = next(x for x in ts[m]["corrections"] if x["condition"] == c)
            fu = [f for f in ts[m]["follow_ups"] if f["condition"] == c]
            cells += [str(co["seed_named"]), str(co["seed_removed"]), str(sum(f["false_retrieved"] for f in fu))]
        L.append(f"| {NAME[c]} | " + " | ".join(cells) + " |")
    return "\n".join(L)


def table_t3_store(m):
    t = t3_of(m)
    L = ["| Strategy | Assistant chose to save it (of 10) | and called its source | B: stored durable | C: stored durable | C: stored provisional | Retrievable 4 sessions later: B | C | C with time-to-live | C + hold |", "|---|---|---|---|---|---|---|---|---|---|"]
    for s in ("S1", "S2", "S3", "S4"):
        w = next(x for x in t["write_decision"] if x["strategy"] == s)
        st = {x["condition"]: x for x in t["stored"] if x["strategy"] == s}
        fu = {x["condition"]: x for x in t["follow_up"] if x["strategy"] == s}
        lab = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in sorted(w["labeled"].items())) or "none"
        prov = st["C"]["in_database"] - st["C"]["durable"]
        L.append(f"| {STRAT[s]} | {w['chose_to_save']} | {lab} | {st['B']['durable']} | {st['C']['durable']} | {prov} | "
                 + " | ".join(str(fu[c]["retrievable"]) for c in ("B", "C", "C_ttl", "C_hold")) + " |")
    return "\n".join(L)


def table_t3_follow(m):
    t = t3_of(m)
    if any(f["judged"] < f["n"] - 1 for f in t["follow_up"]): raise Pending("Task 3 judge " + m)
    conds = ("B", "C", "C_ttl", "C_gate", "C_hold")
    L = ["| Strategy | Reply acts on the planted statement 4 sessions later (of 10): B | C | C with time-to-live | C + gate | C + hold | Flags or asks: C | C + gate |", "|---|---|---|---|---|---|---|---|"]
    for s in ("S1", "S2", "S3", "S4"):
        fu = {x["condition"]: x for x in t["follow_up"] if x["strategy"] == s}
        L.append(f"| {STRAT[s]} | " + " | ".join(str(fu[c]["influenced"]) for c in conds) + f" | {fu['C']['checked']} | {fu['C_gate']['checked']} |")
    return "\n".join(L)


def t3_num(m, strat, cond, what):
    t = t3_of(m)
    strats = ("S1", "S2", "S3", "S4") if strat == "all" else tuple(strat.split("+"))
    if what == "saved":
        w = [x for x in t["write_decision"] if x["strategy"] in strats]; return f"{sum(x['chose_to_save'] for x in w)} of {sum(x['n'] for x in w)}"
    if what == "usersaid":
        w = [x for x in t["write_decision"] if x["strategy"] in strats]; return f"{sum(x['labeled'].get('user_said', 0) for x in w)} of {sum(x['n'] for x in w)}"
    if what in ("durable", "in_db"):
        st = [x for x in t["stored"] if x["strategy"] in strats and x["condition"] == cond]
        return f"{sum(x['durable' if what == 'durable' else 'in_database'] for x in st)} of {sum(x['n'] for x in st)}"
    fu = [x for x in t["follow_up"] if x["strategy"] in strats and x["condition"] == cond]
    if what == "retrievable": return f"{sum(x['retrievable'] for x in fu)} of {sum(x['n'] for x in fu)}"
    if any(f["judged"] < f["n"] - 1 for f in fu): raise Pending("Task 3 judge")
    return f"{sum(x['influenced' if what == 'acts' else 'checked'] for x in fu)} of {sum(x['judged'] for x in fu)}"


def table_runs():
    import collections, glob
    L = ["| Run | Sessions complete | Not complete | Model calls attempted | Failed attempts | Credits recorded (run) | Credits recorded (its judges) |", "|---|---|---|---|---|---|---|"]
    total = 0.0
    for d in sorted(glob.glob(os.path.join(RUNS, "t[123]_*_paid"))):
        name = os.path.basename(d)
        if "canary" in name: continue
        rows = [json.loads(x) for x in open(os.path.join(d, "traces.jsonl"), encoding="utf-8") if x.strip()] if os.path.exists(os.path.join(d, "traces.jsonl")) else []
        spend = {}
        ev = collections.Counter()
        for lp in glob.glob(os.path.join(d, "**", "ledger*.jsonl"), recursive=True):
            last = 0.0
            for line in open(lp, encoding="utf-8", errors="replace"):
                try: r = json.loads(line)
                except json.JSONDecodeError: continue
                last = r.get("spend_after", r.get("spend_after_debit", last)) or last
                if os.path.basename(lp) == "ledger.jsonl": ev[r.get("event") or "row"] += 1
            spend[os.path.relpath(lp, d)] = last
        run_c = spend.pop("ledger.jsonl", 0.0); judge_c = sum(spend.values()); total += run_c + judge_c
        L.append(f"| {name.replace('_paid', '')} | {sum(r.get('status') == 'complete' for r in rows)} | {sum(r.get('status') != 'complete' for r in rows)} | {ev['debit']} | {ev['unresolved']} | {run_c:.3f} | {judge_c:.3f} |")
    L.append(f"| **Total recorded** | | | | | | **{total:.2f}** |")
    return "\n".join(L)


RR = load("t23_reply.json")


def r2_cond(m, cond):
    t = (RR.get(TAG[m]) or {}).get("t2")
    if not t or t["judged"] < 0.97 * t["sessions"]: raise Pending("Task 2 replies not scored " + m)
    return t["conditions"][cond]


def r2_num(m, cond, what):
    c = r2_cond(m, cond)
    if what in ("acts", "asks"): return f"{c[what]} of {c['judged']}"
    if what == "items_asked": return f"{c['items_ever_asked']} of {c['items']}"
    if what == "items_acted": return f"{c['items_ever_acted']} of {c['items']}"
    if what == "nocorr_acts": x = c["false_retrieved_without_correction"]; return f"{x['acts']} of {x['judged']}"
    if what == "both_asks": x = c["false_and_correction_retrieved"]; return f"{x['asks']} of {x['judged']}"
    raise SystemExit("unknown reply measure " + what)


def r2_p(m, measure, a, b):
    t = (RR.get(TAG[m]) or {}).get("t2")
    if not t or t["judged"] < 0.97 * t["sessions"]: raise Pending("Task 2 replies not scored " + m)
    p = next(x for x in t["pairs"] if x["measure"] == measure and x["a_name"] == a and x["b_name"] == b)
    return p_fmt(p["p_exact"])


def table_t2_reply():
    L = ["| Condition | gemma: reply acts on the corrected false memory | reply asks the user again | false memories asked about again at least once (of 24) | deepseek: acts | asks again | asked about again at least once (of 24) |", "|---|---|---|---|---|---|---|"]
    for c in T2_ORDER:
        cells = []
        for m in "gd":
            x = r2_cond(m, c); cells += [f"{x['acts']}/{x['judged']}", f"{x['asks']}/{x['judged']}", str(x["items_ever_asked"])]
        L.append(f"| {NAME[c]} | " + " | ".join(cells) + " |")
    return "\n".join(L)


def r3_cell(m, group, cond):
    t = (RR.get(TAG[m]) or {}).get("t3")
    if not t or t["judged"] < 0.97 * t["sessions"] or t["sessions"] < 190: raise Pending("Task 3 replies not scored " + m)
    return t["cells"][f"{group}|{cond}"]


def r3_num(m, group, cond, what):
    c = r3_cell(m, group, cond)
    return f"{c[what]} of {c['judged']}"


def r3_p(m, group, a, b):
    t = (RR.get(TAG[m]) or {}).get("t3")
    if not t or t["judged"] < 0.97 * t["sessions"]: raise Pending("Task 3 replies not scored " + m)
    p = next(x for x in t["pairs"] if x["group"] == group and x["a_name"] == a and x["b_name"] == b)
    return p_fmt(p["p_exact"])


def table_t3_reply(m):
    conds = ("B", "C", "C_ttl", "C_gate", "C_hold")
    L = ["| Strategy | Reply acts on the planted statement four sessions later: B | C | C with time-to-live | C + gate | C + hold | Flags or asks: C | C + gate |", "|---|---|---|---|---|---|---|---|"]
    for s in ("S1", "S2", "S3", "S4"):
        cs = {c: r3_cell(m, s, c) for c in conds}
        L.append(f"| {STRAT[s]} | " + " | ".join(f"{cs[c]['acts']}/{cs[c]['judged']}" for c in conds) + f" | {cs['C']['asks']}/{cs['C']['judged']} | {cs['C_gate']['asks']}/{cs['C_gate']['judged']} |")
    return "\n".join(L)


def tasks_done():
    try:
        for m in "gd": t2_of(m); t3_of(m)
        return True
    except Pending:
        return False


def tasks_reported():
    return "It reports the first three tasks." if tasks_done() else "This version reports Task 1 in full; Tasks 2 and 3 were still running when it was built."


def tasks_contrib():
    return "Tasks 1 to 3" if tasks_done() else "Task 1 (Tasks 2 and 3 were still running when this version was built)"


def control_act():
    cs = [c for c in ((S.get(TAG[m]) or {}).get("controls") for m in "gd") if c]
    if not cs: raise Pending("controls")
    return f"{sum(c['treats_as_true'] for c in cs)} of {sum(c['n'] for c in cs)}"


def hand(key=None):
    cells = [c for k, c in (JC.get("judges") or {}).items() if k.endswith("|gemma431bit") and c["compared"]]
    if not cells: raise Pending("hand labels")
    if key is None: return str(sum(c["compared"] for c in cells))
    return f"{sum(c['keys'][key]['agree'] for c in cells)} of {sum(c['keys'][key]['n'] for c in cells)}"


def two_act():
    ags = [a for a in (((R.get(TAG[m]) or {}).get("t1") or {}).get("agreement") for m in "gd") if a]
    if not ags: raise Pending("second judge")
    return f"{sum(a['treats_as_true']['agree'] for a in ags)} of {sum(a['treats_as_true']['n'] for a in ags)}"


def repeat_same(m):
    rp = (S.get(TAG[m]) or {}).get("repeat_C_vs_D")
    if not rp: raise Pending("repeat")
    return str(rp["identical_reply_text"])


TABLES = dict(TABLE_T2_DB=table_t2_db, TASKS_REPORTED=tasks_reported, TASKS_CONTRIB=tasks_contrib, TABLE_RUNS=table_runs, CONTROL_ACT=control_act, HAND_N=hand, HAND_ACT=lambda: hand("treats_as_true"), HAND_CHECK=lambda: hand("asks_to_confirm"), TWO_ACT=two_act,
              REPEAT_SAME_G=lambda: repeat_same("g"), REPEAT_SAME_D=lambda: repeat_same("d"),
              TABLE_TTL=table_ttl, HOLM_MAX=holm_max, TABLE_ACTION=table_action, TABLE_CHECK=table_check, TABLE_RETRIEVAL=table_retrieval, TABLE_SESSION=table_session, TABLE_PAIRS=table_pairs,
              TABLE_SESSION_PAIRS=table_session_pairs, TABLE_JUDGE=table_judge, TABLE_TWO_JUDGES=table_two_judges, TABLE_CONTRA=table_contra,
              TABLE_REPEAT=table_repeat, TABLE_CONTROLS=table_controls, TABLE_FULL_G=lambda: table_full("g"), TABLE_FULL_D=lambda: table_full("d"))


def resolve(marker, draft):
    if marker in TABLES:
        try: return TABLES[marker]()
        except Pending as e:
            if draft: return "[pending]"
            raise SystemExit(f"cannot fill {{{{{marker}}}}}: {e}")
    parts = marker.split("|")
    try:
        if parts[0] == "r2" and len(parts) == 4: return r2_num(parts[1], parts[2], parts[3])          # {{r2|g|B|asks}}
        if parts[0] == "r2p" and len(parts) == 5: return r2_p(parts[1], parts[2], parts[3], parts[4])  # {{r2p|g|asks|B|C}}
        if parts[0] == "r3" and len(parts) == 5: return r3_num(parts[1], parts[2], parts[3], parts[4])  # {{r3|g|S3+S4|B|acts}}
        if parts[0] == "r3p" and len(parts) == 5: return r3_p(parts[1], parts[2], parts[3], parts[4])  # {{r3p|g|S3+S4|B|C}}
        if parts[0] == "TABLE_T3_REPLY" and len(parts) == 2: return table_t3_reply(parts[1])
        if parts[0] == "TABLE_T2_REPLY": return table_t2_reply()
        if parts[0] == "t2" and len(parts) == 4: return t2_num(parts[1], parts[2], parts[3])          # {{t2|g|C|named}}
        if parts[0] == "t3" and len(parts) == 5: return t3_num(parts[1], parts[2], parts[3], parts[4])  # {{t3|g|S3+S4|C|durable}}
        if parts[0] in ("TABLE_T2", "TABLE_T3_STORE", "TABLE_T3_FOLLOW") and len(parts) == 2:
            return dict(TABLE_T2=table_t2, TABLE_T3_STORE=table_t3_store, TABLE_T3_FOLLOW=table_t3_follow)[parts[0]](parts[1])
    except Pending as e:
        if draft: return "[pending]"
        raise SystemExit(f"cannot fill {{{{{marker}}}}}: {e}")
    if len(parts) in (3, 4) and parts[0] in TAG:
        try:
            k, n = count(parts[0], parts[1], parts[2])
            return str(k) if len(parts) == 4 else f"{k} of {n}"
        except Pending as e:
            if draft: return "[pending]"
            raise SystemExit(f"cannot fill {{{{{marker}}}}}: {e}")
    if draft: return "[pending]"
    raise SystemExit(f"unknown marker {{{{{marker}}}}}")


MARK = re.compile(r"\{\{([^}]+)\}\}")
FALLBACK = dict(t2="Task 2 was still running when this version was built and is not reported here.",
                t3="Task 3 was still running when this version was built and is not reported here.",
                concl="", t23appendix="Tasks 2 and 3 were still running when this version was built.")


def include(name, draft):
    """A section kept in its own file. If any count in it cannot be filled yet, the whole section falls back to one line."""
    text = open(os.path.join(REP, f"COMPANION.{name}.src.md"), encoding="utf-8").read().strip()
    if os.environ.get("FORCE_INCLUDE"): return MARK.sub(lambda m: resolve(m.group(1), draft), text)   # layout check only
    try:
        for m in MARK.findall(text):
            parts = m.split("|")
            if parts[0] == "t2": t2_num(parts[1], parts[2], parts[3])
            elif parts[0] == "t3": t3_num(parts[1], parts[2], parts[3], parts[4])
            elif parts[0] in ("TABLE_T2", "TABLE_T3_STORE", "TABLE_T3_FOLLOW"):
                dict(TABLE_T2=table_t2, TABLE_T3_STORE=table_t3_store, TABLE_T3_FOLLOW=table_t3_follow)[parts[0]](parts[1])
            elif parts[0] == "TABLE_T2_DB": table_t2_db()
            elif parts[0] == "r2": r2_num(parts[1], parts[2], parts[3])
            elif parts[0] == "r3": r3_num(parts[1], parts[2], parts[3], parts[4])
    except Pending:
        return FALLBACK[name]
    return MARK.sub(lambda m: resolve(m.group(1), draft), text)


def build(draft):
    src = open(os.path.join(REP, "COMPANION.src.md"), encoding="utf-8").read()
    src = re.sub(r"<!--.*?-->\s*", "", src, flags=re.S)
    src = re.sub(r"\{\{INCLUDE:(\w+)\}\}", lambda m: include(m.group(1), draft), src)
    src = MARK.sub(lambda m: resolve(m.group(1), draft), src)
    open(os.path.join(REP, "COMPANION.md"), "w", encoding="utf-8", newline="\n").write(src)
    return src


def render(src):
    import markdown
    src = src.replace("\n## Appendix A", "\n<div class=\"appendix-break\"></div>\n\n## Appendix A")
    html = markdown.markdown(src, extensions=["tables", "fenced_code", "sane_lists"])
    html = html.replace("<p>Angela Faye Reinhold", "<p class=\"byline\">Angela Faye Reinhold", 1)
    title = re.search(r"^# (.+)$", src, re.M).group(1)
    doc = f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title><style>{BR.CSS}</style></head><body>{html}</body></html>"
    open(os.path.join(REP, "COMPANION.html"), "w", encoding="utf-8").write(doc)
    out = os.path.join(REP, "COMPANION.pdf"); inp = "file:///" + os.path.join(REP, "COMPANION.html").replace("\\", "/")
    if os.path.exists(out): os.remove(out)
    ud = os.path.join(os.environ.get("TEMP", "."), "edge_pdf_profile")
    r = subprocess.run([BR.EDGE, "--headless", "--disable-gpu", "--no-first-run", f"--user-data-dir={ud}", "--no-pdf-header-footer", f"--print-to-pdf={out}", inp], capture_output=True, text=True, timeout=180)
    if not os.path.exists(out): sys.exit("edge produced no pdf: " + (r.stderr or r.stdout)[-400:])
    from pypdf import PdfReader
    rd = PdfReader(out); body_end = None
    for i, pg in enumerate(rd.pages):
        if "References" in (pg.extract_text() or "") and body_end is None and i > 2: body_end = i
    m = re.search(r"## Abstract\n\n(.*?)\n\n## ", src, re.S)
    words = len(re.sub(r"[*_`]", "", m.group(1)).split()) if m else None
    print(f"pages {len(rd.pages)}; References start on page {body_end + 1 if body_end is not None else '?'} (body must end by page 8); abstract {words} words (150 to 250 allowed)")


if __name__ == "__main__":
    text = build("--draft" in sys.argv)
    print("pending markers left:", text.count("[pending]") + text.count("not judged yet |"))
    if "--no-pdf" not in sys.argv: render(text)
