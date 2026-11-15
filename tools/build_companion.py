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
        return "pending"


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
        if not t or not t["pairs"]: L.append(f"| pending | {MODEL[m]} | | | | | | | |"); continue
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
    return "\n".join(L) if len(L) > 2 else "pending"


def table_judge():
    if not JC: return "pending"
    names = dict(mentions="mentions it", treats_as_true="acts as if true (action)", asks_to_confirm="flags it or asks (check)", contradicts="says it is not true")
    L = ["| Replies from | Judge | Compared | Question | Agree with hand label | Kappa | Agree, replies not marked borderline |", "|---|---|---|---|---|---|---|"]
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
        if not ag: L.append(f"| {MODEL[m]} | pending | | | | |"); continue
        n = ag["treats_as_true"]["n"]
        L.append(f"| {MODEL[m]} | {n} | {ag['treats_as_true']['agree']}/{n} | {ag['asks_to_confirm']['agree']}/{n} | {ag['mentions']['agree']}/{n} | {ag['contradicts']['agree']}/{n} |")
    return "\n".join(L)


def table_full(m):
    L = ["| Condition | Phase | Sessions | Target retrieved | Judged | Mentions | Acts | Flags or asks | Reply credits the user (pattern) |", "|---|---|---|---|---|---|---|---|---|"]
    t = (R.get(TAG[m]) or {}).get("t1")
    if not t: return "pending"
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
        if not rp: L.append(f"| {MODEL[m]} | pending | | | | |"); continue
        L.append(f"| {MODEL[m]} | {rp['pairs']} | {rp['same_retrieved']} | {rp['identical_reply_text']} | {cell(m, 'C', 'act')} | {cell(m, 'D', 'act')} |")
    return "\n".join(L)


def table_controls():
    L = ["| Replies from | Never-retrieved statements judged | judge says mentions | acts | flags or asks |", "|---|---|---|---|---|"]
    for m in "gd":
        c = (S.get(TAG[m]) or {}).get("controls")
        L.append(f"| {MODEL[m]} | {c['n']} | {c['mentions']} | {c['treats_as_true']} | {c['asks_to_confirm']} |" if c else f"| {MODEL[m]} | pending | | | |")
    return "\n".join(L)


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


TABLES = dict(CONTROL_ACT=control_act, HAND_N=hand, HAND_ACT=lambda: hand("treats_as_true"), HAND_CHECK=lambda: hand("asks_to_confirm"), TWO_ACT=two_act,
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
    if len(parts) in (3, 4) and parts[0] in TAG:
        try:
            k, n = count(parts[0], parts[1], parts[2])
            return str(k) if len(parts) == 4 else f"{k} of {n}"
        except Pending as e:
            if draft: return "[pending]"
            raise SystemExit(f"cannot fill {{{{{marker}}}}}: {e}")
    if draft: return "[pending]"
    raise SystemExit(f"unknown marker {{{{{marker}}}}}")


def build(draft):
    src = open(os.path.join(REP, "COMPANION.src.md"), encoding="utf-8").read()
    src = re.sub(r"<!--.*?-->\s*", "", src, flags=re.S)
    src = re.sub(r"\{\{([^}]+)\}\}", lambda m: resolve(m.group(1), draft), src)
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
    print("pending markers left:", text.count("[pending]") + text.count("pending |"))
    if "--no-pdf" not in sys.argv: render(text)
