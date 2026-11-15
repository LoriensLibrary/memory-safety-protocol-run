"""Run the follow-up cohorts one after another, resuming any that were interrupted, then write their tables.

  python tools/launch_followup.py gemma-4-31b-it deepseek-v4-flash
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import followup   # noqa: E402


def main(models):
    logs = os.path.join(ROOT, "runs", "launch_logs"); os.makedirs(logs, exist_ok=True)
    for model in models:
        fdir, out = followup.paths(model)
        frz = json.load(open(os.path.join(fdir, "FREEZE.json"), encoding="utf-8"))
        claimed = os.path.exists(os.path.join(ROOT, "runs", "claims", f"{frz['freeze_id']}.json"))
        cmd = [sys.executable, os.path.join(HERE, "followup.py"), "run", "--model", model, "--mode", "paid"]
        if claimed and os.path.exists(os.path.join(out + "_paid", "traces.jsonl")): cmd.append("--resume")
        with open(os.path.join(logs, f"{os.path.basename(fdir)}.log"), "a", encoding="utf-8") as log:
            log.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S%z')} {' '.join(cmd[2:])}\n"); log.flush()
            rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT).returncode
            log.write(f"=== exit {rc} at {time.strftime('%Y-%m-%d %H:%M:%S%z')}\n"); log.flush()
            if os.path.exists(os.path.join(out + "_paid", "traces.jsonl")):
                subprocess.run([sys.executable, os.path.join(HERE, "followup.py"), "analyze", "--model", model], stdout=subprocess.DEVNULL, stderr=log)


if __name__ == "__main__":
    main(sys.argv[1:])
