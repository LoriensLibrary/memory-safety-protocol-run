"""Hand labels for the judge check.

  python memory_protocol/handlabel.py sample --run runs_mp/t1_gemma431bit_paid --n 60
      writes runs_mp/handlabel_<run>_sample.jsonl  (sid, statement, message, reply: what the judge sees, nothing else)
      and    runs_mp/handlabel_<run>_key.jsonl     (sid -> condition, item, phase; not opened while labeling)

  python memory_protocol/handlabel.py score
      joins runs_mp/labels_hand.jsonl with the keys and every judgments_*.jsonl, prints and saves accuracy per judge

The sample is the first n replies in the same hash order judge.py uses for its --sample, so every hand-labeled reply
is also scored by both judge models. The order shown to the labeler is a second, unrelated hash order.
Labels are written before any judge output for those replies is read.
"""
import argparse, glob, hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "runs_mp")
KEYS = ("mentions", "treats_as_true", "asks_to_confirm", "contradicts")


def read(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try: rows.append(json.loads(line))
                except json.JSONDecodeError: pass
    return rows


def h(*parts):
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()


def sample(run, n):
    run_dir = run if os.path.isabs(run) else os.path.join(ROOT, run)
    name = os.path.basename(run_dir.rstrip("\\/"))
    rows = [r for r in read(os.path.join(run_dir, "traces.jsonl")) if r["status"] == "complete" and r.get("reply")]
    rows.sort(key=lambda r: h(r["condition"], r["item"], r["phase"]))          # judge.py's order
    rows = rows[:n]
    rows.sort(key=lambda r: h("shown", name, r["item"], r["phase"], r["condition"]))
    prefix = "g" if "gemma" in name else "d"
    with open(os.path.join(OUT, f"handlabel_{name}_sample.jsonl"), "w", encoding="utf-8", newline="\n") as fs, \
         open(os.path.join(OUT, f"handlabel_{name}_key.jsonl"), "w", encoding="utf-8", newline="\n") as fk:
        for i, r in enumerate(rows, 1):
            sid = f"{prefix}{i:03d}"
            fs.write(json.dumps(dict(sid=sid, statement=r["false_inference"], message=r["probe"], reply=r["reply"]), ensure_ascii=False) + "\n")
            fk.write(json.dumps(dict(sid=sid, run=name, condition=r["condition"], item=r["item"], phase=r["phase"], probe_kind=r["probe_kind"])) + "\n")
    print(f"{len(rows)} replies written for {name}")


def kappa(a, b):
    n = len(a)
    if not n: return None
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else (po - pe) / (1 - pe)


def score():
    labels = {r["sid"]: r for r in read(os.path.join(OUT, "labels_hand.jsonl"))}
    keys = {}
    for p in glob.glob(os.path.join(OUT, "handlabel_*_key.jsonl")):
        for r in read(p): keys[r["sid"]] = r
    result = dict(labeled=len(labels), judges={})
    for run in sorted({k["run"] for k in keys.values()}):
        for jp in sorted(glob.glob(os.path.join(OUT, run, "judgments_*.jsonl"))):
            jtag = os.path.basename(jp)[len("judgments_"):-len(".jsonl")]
            judged = {(r["condition"], r["item"], r["phase"]): r for r in read(jp) if r.get("status") == "complete"}
            cell = dict(run=run, judge=jtag, compared=0, missing=0, keys={}, disagreements=[])
            pairs = {k: ([], []) for k in KEYS}
            for sid, lab in sorted(labels.items()):
                key = keys.get(sid)
                if not key or key["run"] != run: continue
                j = judged.get((key["condition"], key["item"], key["phase"]))
                if not j: cell["missing"] += 1; continue
                cell["compared"] += 1
                for k in KEYS:
                    pairs[k][0].append(bool(lab[k])); pairs[k][1].append(bool(j[k]))
                    if bool(lab[k]) != bool(j[k]): cell["disagreements"].append(dict(sid=sid, key=k, hand=bool(lab[k]), judge=bool(j[k])))
            for k in KEYS:
                hand, jud = pairs[k]
                tp = sum(x and y for x, y in zip(hand, jud)); fp = sum((not x) and y for x, y in zip(hand, jud))
                fn = sum(x and (not y) for x, y in zip(hand, jud)); tn = sum((not x) and (not y) for x, y in zip(hand, jud))
                kp = kappa(hand, jud)
                cell["keys"][k] = dict(agree=tp + tn, n=len(hand), hand_yes=tp + fn, judge_yes=tp + fp, both_yes=tp,
                                       judge_yes_hand_no=fp, judge_no_hand_yes=fn, kappa=None if kp is None else round(kp, 3))
            result["judges"][f"{run}|{jtag}"] = cell
    with open(os.path.join(OUT, "judge_check.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, indent=1)
    for name, cell in result["judges"].items():
        print(f"\n{name}: {cell['compared']} compared, {cell['missing']} not judged")
        for k, v in cell["keys"].items():
            print(f"  {k:16s} agree {v['agree']}/{v['n']}  hand yes {v['hand_yes']}  judge yes {v['judge_yes']}  "
                  f"judge-only {v['judge_yes_hand_no']}  hand-only {v['judge_no_hand_yes']}  kappa {v['kappa']}")
        for d in cell["disagreements"]: print("   ", d)


if __name__ == "__main__":
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample"); s.add_argument("--run", required=True); s.add_argument("--n", type=int, default=60)
    sub.add_parser("score")
    a = p.parse_args()
    sample(a.run, a.n) if a.cmd == "sample" else score()
