"""Exploratory tier (preregistration amendment 1): more Adaption-hosted models on the same held-out items.

  python tools/launch_exploratory.py [pid-to-wait-for]

For each model: run the development canary; apply the preregistered inclusion rule (at least 90% valid replies);
choose n by the preregistered latency rule (60 per type if the cohort projects under 6 hours, else 40); freeze the
held-out set with the same seed as the main cohorts; run it; write its tables. Cohorts run one after another because
the provider's rate limit is per account. Every decision is written to runs/launch_logs/exploratory_<tag>.json.
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import launch   # noqa: E402

MODELS = (("gemma26", "gemma-4-26b-a4b-it", 3.0), ("qwen27", "qwen3.8-27b", 8.0))
DEV_SEED, HELDOUT_SEED = 20261114, 2026111501


def alive(pid):
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
    return str(pid) in out


def freeze(name, split, seed, n, model, ceiling):
    if os.path.exists(os.path.join(ROOT, "holdout", name)): return
    subprocess.run([sys.executable, os.path.join(HERE, "run.py"), "freeze", "--name", name, "--split", split, "--seed", str(seed), "--n", str(n),
                    "--model", model, "--ceiling", str(ceiling), "--min-interval", "1.5"], check=True)


def main(wait_pid=None):
    logs = os.path.join(ROOT, "runs", "launch_logs"); os.makedirs(logs, exist_ok=True)
    while wait_pid and alive(wait_pid): time.sleep(30)
    for tag, model, ceiling in MODELS:
        note = dict(model=model, started=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        dev = f"dev_{tag}"
        freeze(dev, "dev", DEV_SEED, 2, model, 1.0)
        launch.main([dev])
        tp = os.path.join(ROOT, "runs", f"{dev}_paid", "traces.jsonl")
        rows = [json.loads(ln) for ln in open(tp, encoding="utf-8") if ln.strip()] if os.path.exists(tp) else []
        slots = [r for r in rows if r["arm"] != "rule"]
        valid = sum(r["status"] == "complete" for r in slots)
        secs = [r["elapsed_s"] for r in slots if r["status"] == "complete" and r.get("elapsed_s")]
        mean_s = sum(secs) / len(secs) if secs else None
        note.update(dev_model_slots=len(slots), dev_valid=valid, dev_valid_rate=round(valid / len(slots), 3) if slots else None, dev_mean_s_per_slot=mean_s and round(mean_s, 2))
        if len(slots) < 64 or valid / len(slots) < 0.9:
            note["decision"] = "excluded: under 90% valid replies in the development canary (or canary incomplete)"
        else:
            hours = 1920 * max(mean_s, 1.5) / 3600
            n = 60 if hours < 6 else 40
            note.update(projected_hours_at_n60=round(hours, 2), n_per_type=n, decision="included")
            held = f"heldout_{tag}"
            freeze(held, "heldout", HELDOUT_SEED, n, model, ceiling)
            launch.main([held])
        note["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        json.dump(note, open(os.path.join(logs, f"exploratory_{tag}.json"), "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
