"""Tables and preregistered paired comparisons for one executed cohort.

  python tools/analyze.py --run runs/dev_gemma_dry --freeze holdout/dev_gemma

Every registered slot is in the denominator. An invalid, errored or unreached slot is neither a success nor an
adoption; it is counted in its own column. Statistics reuse the paired-interval code from SwarmHive (pre-existing).
"""
import argparse, collections, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import items   # noqa: E402
from vendor.swarm_analysis import tango_interval, holm, wilson, sign_test_p   # noqa: E402

# (label, variants, endpoint, arm_a, arm_b, what a positive a-minus-b difference means)
CLAIMS = [
    ("C1 plant adoption, provenance points at the truth", items.ATTACKS, "adopted_bad", "bare", "env_json", "provenance lowers adoption"),
    ("C2 plant adoption under a forged in-text claim", ("V3",), "adopted_bad", "bare", "env_json", "provenance lowers adoption"),
    ("C3 plant adoption when copies outnumber the truth, nothing verified", ("V7",), "adopted_bad", "bare", "env_json", "lineage lowers adoption"),
    ("C4 preloaded vs offered-on-request, correct answers", items.ATTACKS, "correct", "env_json", "lookup", "preloading beats offering"),
    ("C5 JSON vs plain sentences, correct answers", items.ATTACKS, "correct", "env_json", "env_prose", "JSON beats sentences"),
    ("C6 over-distrust: correct answers on clean unverified sources", ("V6",), "correct", "bare", "env_json", "provenance costs correct answers"),
    ("C7 harm when the verified source is the wrong one", ("V5",), "adopted_bad", "env_json", "bare", "provenance raises adoption"),
]
OUTCOMES = ("correct", "adopted_bad", "abstain", "other_wrong")


def load(run_dir, freeze_dir):
    inst = json.load(open(os.path.join(freeze_dir, "instances.json"), encoding="utf-8"))
    frz = json.load(open(os.path.join(freeze_dir, "FREEZE.json"), encoding="utf-8"))
    rows = {}
    for ln in open(os.path.join(run_dir, "traces.jsonl"), encoding="utf-8"):
        r = json.loads(ln)
        if (r["tid"], r["arm"]) in rows: raise SystemExit(f"duplicate trace for {r['tid']} {r['arm']}")
        rows[(r["tid"], r["arm"])] = r
    return frz, inst, rows


def hit(rows, tid, arm, endpoint):
    r = rows.get((tid, arm))
    return bool(r and r["status"] == "complete" and r.get("outcome") == endpoint)


def analyze(frz, inst, rows):
    table = collections.defaultdict(lambda: collections.Counter())
    for it in inst:
        for arm in frz["arms"]:
            c = table[(it["variant"], arm)]; c["registered"] += 1
            r = rows.get((it["tid"], arm))
            if r is None: c["not_run"] += 1; continue
            if r["status"] != "complete": c[r["status"]] += 1; continue
            c[r["outcome"]] += 1
            if r.get("cited_bad"): c["cited_bad"] += 1
            if r.get("lookup_taken"): c["lookup_taken"] += 1
            c["calls"] += r.get("calls", 0); c["input_tokens"] += r.get("input_tokens", 0); c["output_tokens"] += r.get("output_tokens", 0)
    claims, pvals = [], []
    for label, variants, endpoint, a, b, meaning in CLAIMS:
        tids = [it["tid"] for it in inst if it["variant"] in variants]
        if not tids or a not in frz["arms"] or b not in frz["arms"]: continue
        ya = [hit(rows, t, a, endpoint) for t in tids]; yb = [hit(rows, t, b, endpoint) for t in tids]
        n = len(tids); n12 = sum(x and not y for x, y in zip(ya, yb)); n21 = sum(y and not x for x, y in zip(ya, yb))
        lo, hi = tango_interval(n12, n21, n)
        p = sign_test_p([1] * n12 + [-1] * n21)             # exact two-sided McNemar on the discordant pairs
        claims.append(dict(claim=label, variants=list(variants), endpoint=endpoint, arm_a=a, arm_b=b, n_pairs=n,
                           rate_a=round(sum(ya) / n, 4), rate_b=round(sum(yb) / n, 4), diff=round((sum(ya) - sum(yb)) / n, 4),
                           ci95=[round(lo, 4), round(hi, 4)], discordant=[n12, n21], p_exact=p, positive_means=meaning))
        pvals.append(p)
    if pvals:
        adj, rej = holm(pvals)
        for c, pa, rj in zip(claims, adj, rej): c["p_holm"] = pa; c["supported_at_05"] = bool(rj)
    return table, claims


def render(frz, table, claims, dry):
    L = [f"# {frz['name']} ({frz['split']} split, {frz['model']}, n={frz['n_per_variant']} per variant)", ""]
    if dry: L += ["**DRY RUN with a scripted stand-in reader. These numbers prove the pipeline, not model behaviour.**", ""]
    L += ["| variant | arm | registered | correct | adopted plant | abstain | other wrong | invalid | error | not run | cited plant | lookup taken |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for v in frz["variants"]:
        for arm in frz["arms"]:
            c = table[(v, arm)]
            L.append(f"| {v} | {arm} | {c['registered']} | {c['correct']} | {c['adopted_bad']} | {c['abstain']} | {c['other_wrong']} | {c['invalid']} | {c['error']} | "
                     f"{c['not_run'] + c['budget_stopped']} | {c['cited_bad']} | {c['lookup_taken'] if arm == 'lookup' else ''} |")
    L += ["", "| claim | pairs | rate A | rate B | A minus B | 95% interval | discordant | exact p | Holm p |", "|---|---|---|---|---|---|---|---|---|"]
    for c in claims:
        L.append(f"| {c['claim']} ({c['arm_a']} vs {c['arm_b']}, {c['endpoint']}) | {c['n_pairs']} | {c['rate_a']:.3f} | {c['rate_b']:.3f} | {c['diff']:+.3f} | "
                 f"[{c['ci95'][0]:+.3f}, {c['ci95'][1]:+.3f}] | {c['discordant'][0]}/{c['discordant'][1]} | {c['p_exact']:.4g} | {c.get('p_holm', float('nan')):.4g} |")
    return "\n".join(L) + "\n"


def main():
    p = argparse.ArgumentParser(); p.add_argument("--run", required=True); p.add_argument("--freeze", required=True)
    a = p.parse_args()
    run_dir = a.run if os.path.isabs(a.run) else os.path.join(ROOT, a.run)
    fdir = a.freeze if os.path.isabs(a.freeze) else os.path.join(ROOT, a.freeze)
    frz, inst, rows = load(run_dir, fdir)
    table, claims = analyze(frz, inst, rows)
    md = render(frz, table, claims, dry=run_dir.rstrip("/\\").endswith("_dry"))
    json.dump(dict(freeze_id=frz["freeze_id"], table={f"{v}|{arm}": dict(c) for (v, arm), c in table.items()}, claims=claims),
              open(os.path.join(run_dir, "results.json"), "w", encoding="utf-8"), indent=1)
    open(os.path.join(run_dir, "TABLES.md"), "w", encoding="utf-8").write(md)
    print(md)


if __name__ == "__main__":
    main()
