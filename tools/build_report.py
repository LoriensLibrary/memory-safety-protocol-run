"""Assemble report/REPORT.md from report/REPORT.src.md and the generated numbers, then render the PDF.

  python tools/report_tables.py heldout_gemma31 heldout_deepseek      (first: regenerates report/generated/)
  python tools/build_report.py

Every table in the report is built here from report/generated/numbers.json. The prose in REPORT.src.md is hand-written;
`python tools/build_report.py --facts` prints the numbers the prose quotes, for the sentence-by-sentence check.
The PDF step is adapted from our earlier sprint project's renderer (pre-existing): markdown -> HTML -> Edge headless.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REP = os.path.join(ROOT, "report")
N = json.load(open(os.path.join(REP, "generated", "numbers.json"), encoding="utf-8"))
MODELS = [m for m in N if not m.startswith("_")]
ARMS = [("bare", "no record"), ("env_json", "JSON record"), ("env_prose", "sentence record"), ("lookup", "record on request"), ("rule", "fixed rule")]
VARS = [("V0", "clean, verified"), ("V1", "single plant"), ("V2", "copied plant"), ("V3", "forged claim"), ("V4", "retraction"),
        ("V5", "verified but wrong"), ("V6", "clean, unverified"), ("V7", "copies, none verified")]
CLAIM_NAMES = ["C1 record lowers plant adoption, four attack types pooled", "C2 record lowers adoption under a forged in-text claim",
               "C3 copy labels lower adoption when copies outnumber the truth", "C4 delivered record beats record on request",
               "C5 JSON record against sentence record (no direction expected)", "C6 record costs correct answers on clean unverified sources",
               "C7 record raises adoption when the verified source is wrong"]
ARMNAME = dict(ARMS)
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def p_fmt(p):
    return "< 0.001" if p < 0.001 else f"{p:.3f}" if p < 0.995 else "1.0"


def table_claims():
    L = ["| Claim | Endpoint | " + " | ".join(f"{m}: A vs B | difference [95%], Holm p" for m in MODELS) + " |", "|---|---|" + "---|---|" * len(MODELS)]
    for i, name in enumerate(CLAIM_NAMES):
        cells = []
        for m in MODELS:
            c = N[m]["claims"][i]; n = c["n_pairs"]
            cells += [f"{ARMNAME[c['arm_a']]} {round(c['rate_a'] * n)}/{n} vs {ARMNAME[c['arm_b']]} {round(c['rate_b'] * n)}/{n}",
                      f"{c['diff'] * 100:+.1f} [{c['ci95'][0] * 100:+.1f}, {c['ci95'][1] * 100:+.1f}], {p_fmt(c['p_holm'])}"]
        ep = N[MODELS[0]]["claims"][i]["endpoint"].replace("adopted_bad", "adopted plant")
        L.append(f"| {name} | {ep} | " + " | ".join(cells) + " |")
    return "\n".join(L)


def table_main():
    """Compact body table: per item type, each model with no record and with the JSON record."""
    def cell(t):
        parts = [f"{t.get(k, 0)} {lab}" for k, lab in (("correct", "correct"), ("adopted_bad", "adopted"), ("abstain", "abstained")) if t.get(k, 0)]
        return ", ".join(parts) or "0"
    L = ["| Item type | " + " | ".join(f"{m}, no record | {m}, JSON record" for m in MODELS) + " |", "|---|" + "---|---|" * len(MODELS)]
    for v, name in VARS:
        L.append(f"| {name} | " + " | ".join(f"{cell(N[m]['table'][f'{v}|bare'])} | {cell(N[m]['table'][f'{v}|env_json'])}" for m in MODELS) + " |")
    return "\n".join(L)


def table_pertype(m):
    L = ["| Item type | Arm | Correct | Adopted plant | Abstained | Other wrong | Invalid | Error | Record requested |", "|---|---|---|---|---|---|---|---|---|"]
    for v, vn in VARS:
        for a, an in ARMS:
            t = N[m]["table"][f"{v}|{a}"]
            L.append(f"| {vn} | {an} | {t.get('correct', 0)} | {t.get('adopted_bad', 0)} | {t.get('abstain', 0)} | {t.get('other_wrong', 0)} | {t.get('invalid', 0)} | {t.get('error', 0)} | {t.get('lookup_taken', 0) if a == 'lookup' else ''} |")
    return "\n".join(L)


def table_integrity():
    L = ["| Model | Registered slots | Complete | Invalid | Transport error | Not run | Provider attempts | Metered credits | Reserves kept | Counted against cap |", "|---|---|---|---|---|---|---|---|---|---|"]
    for m in MODELS:
        i = N[m]["integrity"]
        L.append(f"| {m} | {i['registered']:,} | {i['complete']:,} | {i['invalid']} | {i['error']} | {i['not_run'] + i['budget_stopped']} | {i['attempts']:,} | {i['metered']:.3f} | {i['kept_reserves']:.3f} | {i['counted_spend']:.3f} |")
    return "\n".join(L)


def table_tokens():
    L = ["| Model | Arm | Input tokens per call | Output tokens per call | Calls per item |", "|---|---|---|---|---|"]
    for m in MODELS:
        for a, an in ARMS[:-1]:
            t = N[m]["tokens"][a]
            L.append(f"| {m} | {an} | {t['input_per_call']} | {t['output_per_call']} | {t['calls_per_slot']:.2f} |")
    return "\n".join(L)


def table_lookup():
    L = ["| Model | Item type | Asked: outcomes | Did not ask: outcomes |", "|---|---|---|---|"]
    lab = dict(correct="correct", adopted_bad="adopted plant", abstain="abstained", other_wrong="other wrong")
    for m in MODELS:
        d = N[m]["lookup_conditional"]
        for _, vn in VARS:
            if vn not in d: continue
            f = lambda k: ", ".join(f"{n} {lab[o]}" for o, n in d[vn].get(k, {}).items()) or "none"   # noqa: E731
            L.append(f"| {m} | {vn} | {f('asked')} | {f('did not ask')} |")
    return "\n".join(L)


def table_order():
    L = ["| Model | Item type and arm | Plant listed first: adopted / items | True source listed first: adopted / items |", "|---|---|---|---|"]
    for m in MODELS:
        for k, d in N[m]["order_effects"].items():
            a, b = d.get("plant listed first", [0, 0]), d.get("true source listed first", [0, 0])
            L.append(f"| {m} | {k.replace(' | ', ', ')} | {a[0]} / {a[1]} | {b[0]} / {b[1]} |")
    return "\n".join(L)


FU_CELL = {"json|bare": "JSON forgery, no record", "json|env_json": "JSON forgery, JSON record", "json|env_prose": "JSON forgery, sentence record",
           "sentence|bare": "sentence forgery, no record", "sentence|env_json": "sentence forgery, JSON record", "sentence|env_prose": "sentence forgery, sentence record",
           "header|bare": "header forgery, no record", "header|env_json": "header forgery, JSON record", "header|env_prose": "header forgery, sentence record",
           "bare": "no record", "env_json": "JSON record", "folded_json": "copies removed, JSON record", "folded_bare": "copies removed, no record",
           "lookup": "record on request", "required": "record required", "closed": "question only, no sources", "env_prose": "sentence record"}
FU_NAME = dict(F1="F1 forgery format (60 items)", F2="F2 copies removed (60 items)", F3="F3 required request (120 items)", F4="F4 well-known facts (48 items)")


def table_followup():
    fu = N.get("_followups") or {}
    ms = [m for m in MODELS if m in fu]
    if not ms: return "_Follow-up results are not in yet._"
    L = ["| Test | Condition | " + " | ".join(f"{m}: correct / adopted plant / abstained / other" for m in ms) + " |", "|---|---|" + "---|" * len(ms)]
    keys = list(fu[ms[0]]["table"])
    for k in keys:
        f, c = k.split("|", 1)
        cells = []
        for m in ms:
            t = fu[m]["table"][k]
            other = t["registered"] - t.get("correct", 0) - t.get("adopted_bad", 0) - t.get("abstain", 0)
            cells.append(f"{t.get('correct', 0)} / {t.get('adopted_bad', 0)} / {t.get('abstain', 0)} / {other}" + (f" (requested {t['lookup_taken']})" if t.get("lookup_taken") else ""))
        L.append(f"| {FU_NAME[f]} | {FU_CELL[c]} | " + " | ".join(cells) + " |")
    return "\n".join(L)


F5_TYPE = dict(V1="single plant", V3="forged claim", V5="verified but wrong", V7="copies, none verified", V6="clean, unverified")
F5_COND = dict(none="no record", described="record, original note", unexplained="record, no note", reworded="record, reworded note", caveat="record, original note plus caveat")


def table_f5():
    fu = N.get("_followups_f5") or {}
    ms = [m for m in MODELS if m in fu]
    if not ms: return "_F5 results are not in yet._"
    L = ["| Item type (30 items) | Condition | " + " | ".join(f"{m}: correct / adopted plant / abstained / other" for m in ms) + " |", "|---|---|" + "---|" * len(ms)]
    for k in fu[ms[0]]["table"]:
        v, c = k.split("|", 1); cells = []
        for m in ms:
            t = fu[m]["table"][k]
            cells.append(f"{t.get('correct', 0)} / {t.get('adopted_bad', 0)} / {t.get('abstain', 0)} / {t['registered'] - t.get('correct', 0) - t.get('adopted_bad', 0) - t.get('abstain', 0)}")
        L.append(f"| {F5_TYPE[v]} | {F5_COND[c]} | " + " | ".join(cells) + " |")
    return "\n".join(L)


def example_box():
    e = N["_example_item"]
    return ("```\nQUESTION: " + e["question"] + "\n\nSOURCES:\n\n" + e["sources"] + "\n\nPLATFORM PROVENANCE:\n" + e["json_record"] + "\n```")


CSS = """
@page { size: Letter; margin: 0.75in 0.8in; }
body { font-family: 'Times New Roman', Georgia, serif; font-size: 10.5pt; line-height: 1.3; color: #111; }
h1 { font-size: 17pt; margin: 0 0 6pt 0; line-height: 1.2; }
h2 { font-size: 12.5pt; margin: 14pt 0 5pt 0; page-break-after: avoid; }
h3 { font-size: 11pt; margin: 10pt 0 4pt 0; page-break-after: avoid; }
p { margin: 0 0 6pt 0; text-align: justify; }
li { margin-bottom: 2pt; }
table { border-collapse: collapse; width: 100%; font-size: 8pt; margin: 6pt 0 8pt 0; }
tr { page-break-inside: avoid; }
th, td { border: 0.5pt solid #777; padding: 2pt 3.5pt; vertical-align: top; text-align: left; }
th { background: #eee; }
code { font-family: Consolas, 'Courier New', monospace; font-size: 8.6pt; }
pre { font-family: Consolas, 'Courier New', monospace; font-size: 7.4pt; line-height: 1.25; background: #f6f6f6; border: 0.5pt solid #999; padding: 5pt 6pt; white-space: pre-wrap; word-break: break-word; page-break-inside: avoid; }
pre code { font-size: 7.4pt; }
.byline { color: #333; font-size: 10pt; margin-bottom: 10pt; }
.appendix-break { page-break-before: always; }
figure.fig { margin: 4pt 0 8pt 0; break-inside: avoid; page-break-inside: avoid; }
figcaption { font-size: 9.5pt; margin-top: 2pt; text-align: justify; }
img { width: 100%; display: block; margin: 4pt auto 2pt auto; page-break-inside: avoid; }
"""


def build():
    src = open(os.path.join(REP, "REPORT.src.md"), encoding="utf-8").read()
    subs = {"TABLE_MAIN": table_main(), "TABLE_CLAIMS": table_claims(), "TABLE_INTEGRITY": table_integrity(), "TABLE_TOKENS": table_tokens(),
            "TABLE_LOOKUP": table_lookup(), "TABLE_ORDER": table_order(), "TABLE_FOLLOWUP": table_followup(), "TABLE_F5": table_f5(), "EXAMPLE_ITEM": example_box()}
    for m in MODELS: subs[f"TABLE_PERTYPE:{m}"] = table_pertype(m)
    for k, v in subs.items(): src = src.replace("{{" + k + "}}", v)
    left = re.findall(r"\{\{[^}]+\}\}", src)
    if left: raise SystemExit(f"unfilled markers: {left}")
    open(os.path.join(REP, "REPORT.md"), "w", encoding="utf-8", newline="\n").write(src)
    return src


def render(src):
    import markdown
    src = src.replace("\n## Appendix A", "\n<div class=\"appendix-break\"></div>\n\n## Appendix A")
    html = markdown.markdown(src, extensions=["tables", "fenced_code", "sane_lists"])
    html = html.replace("<p>Angela Faye Reinhold", "<p class=\"byline\">Angela Faye Reinhold", 1)
    html = re.sub(r'<p>(<img[^>]*>)</p>\s*<p><em>(Figure \d\..*?)</em></p>', r'<figure class="fig">\1<figcaption><em>\2</em></figcaption></figure>', html, flags=re.S)
    doc = f"<!doctype html><html><head><meta charset='utf-8'><title>Does Attached Provenance Change What a Model Believes?</title><style>{CSS}</style></head><body>{html}</body></html>"
    open(os.path.join(REP, "REPORT.html"), "w", encoding="utf-8").write(doc)
    out = os.path.join(REP, "REPORT.pdf"); inp = "file:///" + os.path.join(REP, "REPORT.html").replace("\\", "/")
    if os.path.exists(out): os.remove(out)
    ud = os.path.join(os.environ.get("TEMP", "."), "edge_pdf_profile")
    r = subprocess.run([EDGE, "--headless", "--disable-gpu", "--no-first-run", f"--user-data-dir={ud}", "--no-pdf-header-footer", f"--print-to-pdf={out}", inp], capture_output=True, text=True, timeout=180)
    if not os.path.exists(out): sys.exit("edge produced no pdf: " + (r.stderr or r.stdout)[-400:])
    from pypdf import PdfReader
    rd = PdfReader(out); body_end = None; abstract_words = None
    for i, pg in enumerate(rd.pages):
        if "References" in (pg.extract_text() or "") and body_end is None and i > 2: body_end = i
    m = re.search(r"## Abstract\n\n(.*?)\n\n## ", src, re.S)
    if m: abstract_words = len(re.sub(r"[*_`]", "", m.group(1)).split())
    print(f"pages {len(rd.pages)}; References start on page {body_end + 1 if body_end is not None else '?'} (body must end by page 8); abstract {abstract_words} words (150 to 250 allowed)")


if __name__ == "__main__":
    if "--facts" in sys.argv:
        for m in MODELS:
            print(m, json.dumps({k: N[m][k] for k in ("integrity", "one_vs_one_no_record", "copies_cited", "tokens")}, indent=1))
    else:
        render(build())
