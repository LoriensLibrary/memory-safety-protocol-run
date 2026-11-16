"""Independent recount of the paper's headline numbers, straight from the raw run files.

Shares no code with analysis.py, collateral.py, t23_reply.py or build_companion.py: it reads traces.jsonl,
judgments_*.jsonl, corrections.jsonl and stored.jsonl itself and prints the counts, so a bug in the analysis
code would show up as a mismatch with the paper.

  python memory_protocol/recount.py
"""
import collections, json, os

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runs_mp")


def rows(*parts):
    p = os.path.join(ROOT, *parts)
    if not os.path.exists(p): return []
    out = []
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line: out.append(json.loads(line))
    return out


for tag in ("gemma431bit", "deepseekv4fl"):
    print("=====", tag)
    # ---- Task 1
    tr = rows(f"t1_{tag}_paid", "traces.jsonl")
    jd = {}
    for j in rows(f"t1_{tag}_paid", "judgments_gemma431bit.jsonl"):
        if j.get("status") == "complete": jd[(j["condition"], j["item"], j["phase"])] = j
    act = collections.Counter(); n = collections.Counter(); chk = collections.Counter(); retr = collections.Counter()
    for r in tr:
        k = (r["condition"], r["item"], r["phase"])
        retr[(r["condition"], r["phase"])] += bool(r.get("seed_retrieved"))
        if k not in jd: continue
        for sl in ("all", r["probe_kind"], f"p{r['phase']}"):
            n[(r["condition"], sl)] += 1
            act[(r["condition"], sl)] += bool(jd[k]["treats_as_true"])
            chk[(r["condition"], sl)] += bool(jd[k]["asks_to_confirm"] and not jd[k]["treats_as_true"])
    for c in ("A", "B", "C", "D", "C_ttl", "C_gate", "C_hold"):
        print(f" T1 {c:7s} acts all {act[(c,'all')]}/{n[(c,'all')]} recall {act[(c,'recall')]}/{n[(c,'recall')]} task {act[(c,'task')]}/{n[(c,'task')]}"
              f" | before {act[(c,'p1')]}/{n[(c,'p1')]} after {act[(c,'p2')]}/{n[(c,'p2')]} | check recall {chk[(c,'recall')]} task {chk[(c,'task')]}"
              f" | target retrieved before {retr[(c,1)]} after {retr[(c,2)]}")
    # ---- Task 2
    tr = rows(f"t2_{tag}_paid", "traces.jsonl")
    jd = {(j["condition"], j["item"], j["phase"]): j for j in rows(f"t2_{tag}_paid", "judgments_gemma431bit.jsonl") if j.get("status") == "complete"}
    ev = rows(f"t2_{tag}_paid", "corrections.jsonl")
    for c in ("A", "B", "B_del", "C", "C_ttl", "C_gate", "C_hold"):
        rs = [r for r in tr if r["condition"] == c]; js = [jd[k] for r in rs if (k := (r["condition"], r["item"], r["phase"])) in jd]
        e = [x for x in ev if x["condition"] == c]
        print(f" T2 {c:7s} sessions {len(rs)} false retrieved {sum(bool(r['seed_retrieved']) for r in rs)} | judged {len(js)} acts {sum(bool(j['treats_as_true']) for j in js)}"
              f" asks {sum(bool(j['asks_to_confirm'] and not j['treats_as_true']) for j in js)} | named {sum(bool(x.get('seed_named')) for x in e)} removed {sum(bool(x.get('seed_removed')) for x in e)} of {len(e)}")
    # ---- Task 3
    st = rows(f"t3_{tag}_paid", "stored.jsonl"); tr = rows(f"t3_{tag}_paid", "traces.jsonl")
    jd = {(j["condition"], j["item"], j["phase"]): j for j in rows(f"t3_{tag}_paid", "judgments_gemma431bit.jsonl") if j.get("status") == "complete"}
    for c in ("B", "C", "C_ttl", "C_gate", "C_hold"):
        d = [x for x in st if x["condition"] == c and x["strategy"] in ("S3", "S4")]
        rs = [r for r in tr if r["condition"] == c and r["strategy"] in ("S3", "S4")]
        js = [jd[k] for r in rs if (k := (r["condition"], r["item"], r["phase"])) in jd]
        print(f" T3 {c:7s} S3+S4 attacks {len(d)} durable {sum(any(p['status'] == 'durable' for p in x['planted']) for x in d)} | replies judged {len(js)} act {sum(bool(j['treats_as_true']) for j in js)}")
