"""Every number, table and figure the report uses, generated from the committed traces and ledgers.

  python tools/report_tables.py heldout_gemma31 heldout_deepseek

Writes report/generated/tables.md, numbers.json and fig1_outcomes.png. Nothing here is typed by hand.
"""
import collections, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import analyze, items   # noqa: E402

ARM = dict(bare="no record", env_json="JSON record", env_prose="sentence record", lookup="record on request", rule="fixed rule")
ARM_SHORT = dict(bare="none", env_json="JSON", env_prose="text", lookup="offer", rule="rule")
VAR = dict(V0="clean, verified", V1="single plant", V2="copied plant", V3="forged claim", V4="retraction",
           V5="verified but wrong", V6="clean, unverified", V7="copies, none verified")
OUT = os.path.join(ROOT, "report", "generated")


def load(name):
    run, fdir = os.path.join(ROOT, "runs", f"{name}_paid"), os.path.join(ROOT, "holdout", name)
    frz, inst, rows = analyze.load(run, fdir)
    table, claims = analyze.analyze(frz, inst, rows)
    sens = json.load(open(os.path.join(run, "sensitivity.json"), encoding="utf-8")) if os.path.exists(os.path.join(run, "sensitivity.json")) else None
    ledger = [json.loads(ln) for ln in open(os.path.join(run, "ledger.jsonl"), encoding="utf-8") if ln.strip()]
    execs = [json.loads(ln) for ln in open(os.path.join(run, "EXECUTION.jsonl"), encoding="utf-8") if ln.strip()]
    return dict(name=name, frz=frz, inst=inst, rows=rows, table=table, claims=claims, sens=sens, ledger=ledger, execs=execs)


def integrity(c):
    st = collections.Counter(r["status"] for r in c["rows"].values())
    registered = len(c["inst"]) * len(c["frz"]["arms"])
    metered = sum(r.get("cost", 0) for r in c["ledger"] if r["event"] == "actual")
    kept = sum(r.get("reserve_kept", 0) for r in c["ledger"] if "reserve_kept" in r)
    ev = collections.Counter((r["event"], r.get("status")) for r in c["ledger"] if r["event"] in ("unresolved", "rate_limit_wait", "retry_5xx_wait"))
    reasons = collections.Counter(r.get("invalid_reason") for r in c["rows"].values() if r["status"] == "invalid")
    return dict(registered=registered, complete=st["complete"], invalid=st["invalid"], error=st["error"], budget_stopped=st["budget_stopped"],
                not_run=registered - len(c["rows"]), attempts=max((r.get("attempt", 0) for r in c["ledger"]), default=0),
                metered=round(metered, 4), kept_reserves=round(kept, 4), counted_spend=round(c["execs"][-1]["spend"], 4),
                ledger_events={f"{k[0]}:{k[1]}": v for k, v in ev.items()}, invalid_reasons=dict(reasons), executions=len(c["execs"]))


def per_arm_tokens(c):
    t = collections.defaultdict(lambda: [0, 0, 0, 0])
    for r in c["rows"].values():
        if r["arm"] != "rule" and r.get("calls"):
            t[r["arm"]][0] += r["input_tokens"]; t[r["arm"]][1] += r["output_tokens"]; t[r["arm"]][2] += r["calls"]; t[r["arm"]][3] += 1
    return {a: dict(input_per_call=round(v[0] / v[2]), output_per_call=round(v[1] / v[2]), calls_per_slot=round(v[2] / v[3], 3)) for a, v in t.items()}


def order_effect(c, variant="V3", arm="env_json"):
    by = {it["tid"]: it for it in c["inst"]}
    out = collections.defaultdict(lambda: [0, 0])
    for (tid, a), r in c["rows"].items():
        if a != arm or by[tid]["variant"] != variant: continue
        first = next(s["role"] for s in by[tid]["sources"] if s["role"] in ("true", "bad"))
        out[first][1] += 1; out[first][0] += r["status"] == "complete" and r.get("outcome") == "adopted_bad"
    return {("plant listed first" if k == "bad" else "true source listed first"): v for k, v in out.items()}


def _first(it):
    return "plant listed first" if next(s["role"] for s in it["sources"] if s["role"] in ("true", "bad")) == "bad" else "true source listed first"


def lookup_conditional(c):
    """Record-on-request arm: outcomes split by whether the model asked."""
    by = {it["tid"]: it for it in c["inst"]}
    out = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for (tid, arm), r in c["rows"].items():
        if arm == "lookup" and r["status"] == "complete":
            out[VAR[by[tid]["variant"]]]["asked" if r["lookup_taken"] else "did not ask"][r["outcome"]] += 1
    return {v: {k: dict(cn) for k, cn in d.items()} for v, d in out.items()}


def copies_cited(c):
    """When a model adopted a copied plant, how many of the three copies did it list as support?"""
    by = {it["tid"]: it for it in c["inst"]}
    out = collections.defaultdict(collections.Counter)
    for (tid, arm), r in c["rows"].items():
        it = by[tid]
        if it["variant"] in ("V2", "V7") and arm != "rule" and r["status"] == "complete" and r.get("outcome") == "adopted_bad":
            role = {s["id"]: s["role"] for s in it["sources"]}
            out[f"{VAR[it['variant']]} | {ARM[arm]}"][f"cited {sum(role[s] == 'bad' for s in r['sources'])} of the 3 copies"] += 1
    return {k: dict(v) for k, v in out.items()}


def one_vs_one(c):
    """No record, one source against one (single plant, retraction, verified but wrong)."""
    by = {it["tid"]: it for it in c["inst"]}
    cn = collections.Counter(r.get("outcome") or r["status"] for (tid, arm), r in c["rows"].items() if arm == "bare" and by[tid]["variant"] in ("V1", "V4", "V5"))
    return dict(cn, registered=sum(1 for it in c["inst"] if it["variant"] in ("V1", "V4", "V5")))


def order_effects(c):
    by = {it["tid"]: it for it in c["inst"]}
    out = {}
    for v, arm in (("V3", "bare"), ("V3", "env_json"), ("V3", "env_prose"), ("V7", "env_json"), ("V7", "bare")):
        d = collections.defaultdict(lambda: [0, 0])
        for (tid, a), r in c["rows"].items():
            if a == arm and by[tid]["variant"] == v:
                d[_first(by[tid])][1] += 1; d[_first(by[tid])][0] += r["status"] == "complete" and r.get("outcome") == "adopted_bad"
        out[f"{VAR[v]} | {ARM[arm]}"] = dict(d)
    return out


def reasoning(c):
    import statistics
    g = collections.defaultdict(list)
    for (tid, arm), r in c["rows"].items():
        if arm != "rule" and r["status"] == "complete" and r.get("calls") == 1:
            g[(ARM[arm], "conflict" if r["variant"] in ("V1", "V2", "V3", "V4", "V5", "V7") else "clean")].append((r.get("reasoning_tokens") or 0, r["output_tokens"]))
    return {f"{a} | {k}": dict(n=len(v), median_reasoning_tokens=statistics.median(x[0] for x in v), median_output_tokens=statistics.median(x[1] for x in v)) for (a, k), v in sorted(g.items())}


def example_item(c, tid="V3-000"):
    it = next(i for i in c["inst"] if i["tid"] == tid)
    return dict(question=it["question"], sources=items.source_section(it), json_record=items.prov_json(it), sentence_record=items.prov_prose(it),
                true_value=it["truth"], planted_value=it["bad"], roles={s["id"]: s["role"] for s in it["sources"]})


def followups():
    out = {}
    for d in sorted(os.listdir(os.path.join(ROOT, "runs"))):
        p = os.path.join(ROOT, "runs", d, "results.json")
        if d.startswith("followup_") and d.endswith("_paid") and os.path.exists(p):
            r = json.load(open(p, encoding="utf-8"))
            ex = [json.loads(ln) for ln in open(os.path.join(ROOT, "runs", d, "EXECUTION.jsonl"), encoding="utf-8") if ln.strip()]
            r["counted_spend"] = round(ex[-1]["spend"], 4); r["executions"] = len(ex)
            out[r["model"]] = r
    return out


def md(cohorts):
    L = []
    for c in cohorts:
        f, i = c["frz"], integrity(c)
        L += [f"## {f['model']}", "",
              f"Registered {i['registered']:,} slots; complete {i['complete']:,}; invalid {i['invalid']}; transport error {i['error']}; not run {i['not_run'] + i['budget_stopped']}. "
              f"Provider attempts {i['attempts']:,}. Metered {i['metered']} credits; reserves kept for failed attempts {i['kept_reserves']}; counted against the cap {i['counted_spend']}.", "",
              "| Item type | Arm | Correct | Adopted plant | Abstained | Other wrong | Invalid | Error | Lookup taken |", "|---|---|---|---|---|---|---|---|---|"]
        for v in f["variants"]:
            for arm in f["arms"]:
                t = c["table"][(v, arm)]
                L.append(f"| {VAR[v]} | {ARM[arm]} | {t['correct']} | {t['adopted_bad']} | {t['abstain']} | {t['other_wrong']} | {t['invalid']} | {t['error']} | {t['lookup_taken'] if arm == 'lookup' else ''} |")
        L += ["", "| Claim | Items | Endpoint | A | B | A minus B, points [95% interval] | Discordant pairs | Holm p |", "|---|---|---|---|---|---|---|---|"]
        for cl in c["claims"]:
            n = cl["n_pairs"]
            L.append(f"| {cl['claim']} | {n} | {cl['endpoint'].replace('adopted_bad', 'adopted plant')} | {ARM[cl['arm_a']]} {round(cl['rate_a'] * n)}/{n} | {ARM[cl['arm_b']]} {round(cl['rate_b'] * n)}/{n} | "
                     f"{cl['diff'] * 100:+.1f} [{cl['ci95'][0] * 100:+.1f}, {cl['ci95'][1] * 100:+.1f}] | {cl['discordant'][0]}/{cl['discordant'][1]} | {cl['p_holm']:.3g} |")
        L += ["", f"Tokens per call by arm: {json.dumps(per_arm_tokens(c))}", "", f"Forged-claim adoption with the JSON record, by which source is listed first [adopted, items]: {json.dumps(order_effect(c))}", ""]
        if c["sens"]:
            s = c["sens"]
            L += [f"Post hoc second reading of invalid replies: recovered {s['recovered']}, still unreadable {s['still_invalid']}, outcomes {json.dumps(s['recovered_outcomes'])}.", ""]
    return "\n".join(L) + "\n"


def figure(cohorts, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    variants = cohorts[0]["frz"]["variants"]; arms = [a for a in items.ARMS]
    fig, axes = plt.subplots(len(cohorts), len(variants), figsize=(13.5, 2.5 * len(cohorts) + 0.9), sharey=True, squeeze=False)
    cols = dict(correct="#3b6ea5", abstain="#c9c9c9", adopted_bad="#c0504d", other="#f0f0f0")
    for ri, c in enumerate(cohorts):
        for ci, v in enumerate(variants):
            ax = axes[ri][ci]; n = c["frz"]["n_per_variant"]
            for xi, arm in enumerate(arms):
                t = c["table"][(v, arm)]
                parts = [("correct", t["correct"]), ("abstain", t["abstain"]), ("adopted_bad", t["adopted_bad"]),
                         ("other", n - t["correct"] - t["abstain"] - t["adopted_bad"])]
                bottom = 0
                for key, val in parts:
                    ax.bar(xi, val, bottom=bottom, color=cols[key], edgecolor="#555" if key == "other" else "none", linewidth=0.4, width=0.78); bottom += val
            ax.set_xticks(range(len(arms))); ax.set_xticklabels([ARM_SHORT[a] for a in arms], fontsize=7, rotation=45, ha="right")
            ax.set_ylim(0, n); ax.set_yticks([0, n // 2, n]); ax.tick_params(axis="y", labelsize=7)
            for sp in ("top", "right"): ax.spines[sp].set_visible(False)
            if ri == 0: ax.set_title(VAR[v], fontsize=8.5)
            if ci == 0: ax.set_ylabel(f"{c['frz']['model']}\nitems of {n}", fontsize=8)
    handles = [plt.Rectangle((0, 0), 1, 1, color=cols[k]) for k in ("correct", "abstain", "adopted_bad")] + [plt.Rectangle((0, 0), 1, 1, facecolor=cols["other"], edgecolor="#555", linewidth=0.4)]
    fig.legend(handles, ["correct", "abstained", "adopted the plant", "invalid, error or other"], loc="lower center", ncol=4, fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(path, dpi=200); plt.close(fig)


def main(names):
    os.makedirs(OUT, exist_ok=True)
    cohorts = [load(n) for n in names]
    open(os.path.join(OUT, "tables.md"), "w", encoding="utf-8", newline="\n").write(md(cohorts))
    numbers = {c["frz"]["model"]: dict(integrity=integrity(c), tokens=per_arm_tokens(c), order_effect_forged_json=order_effect(c),
                                       order_effect_forged_bare=order_effect(c, "V3", "bare"),
                                       table={f"{v}|{a}": dict(t) for (v, a), t in c["table"].items()}, claims=c["claims"],
                                       sensitivity=c["sens"] and {k: c["sens"][k] for k in ("recovered", "still_invalid", "recovered_outcomes", "claims")},
                                       lookup_conditional=lookup_conditional(c), copies_cited=copies_cited(c), one_vs_one_no_record=one_vs_one(c),
                                       order_effects=order_effects(c), reasoning=reasoning(c)) for c in cohorts}
    numbers["_example_item"] = example_item(cohorts[0])
    numbers["_followups"] = followups()
    json.dump(numbers, open(os.path.join(OUT, "numbers.json"), "w", encoding="utf-8"), indent=1)
    figure(cohorts, os.path.join(OUT, "fig1_outcomes.png"))
    print("wrote", OUT)


if __name__ == "__main__":
    main(sys.argv[1:])
