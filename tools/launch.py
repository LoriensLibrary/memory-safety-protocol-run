"""Run frozen cohorts one after another (the provider's rate limit is per account, so cohorts never overlap).

  python tools/launch.py heldout_gemma31 heldout_deepseek

For each name: start the paid run, or resume it if this freeze already has a claim and traces; then write its tables.
Everything is appended to runs/launch_logs/<name>.log. Safe to start again after a crash, a sleep or a dead battery.
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main(names):
    logs = os.path.join(ROOT, "runs", "launch_logs"); os.makedirs(logs, exist_ok=True)
    for name in names:
        fdir = os.path.join(ROOT, "holdout", name)
        frz = json.load(open(os.path.join(fdir, "FREEZE.json"), encoding="utf-8"))
        out = os.path.join(ROOT, "runs", f"{name}_paid")
        claimed = os.path.exists(os.path.join(ROOT, "runs", "claims", f"{frz['freeze_id']}.json"))
        cmd = [sys.executable, os.path.join(HERE, "run.py"), "run", "--freeze", fdir, "--mode", "paid"]
        if claimed and os.path.exists(os.path.join(out, "traces.jsonl")): cmd.append("--resume")
        with open(os.path.join(logs, f"{name}.log"), "a", encoding="utf-8") as log:
            log.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S%z')} {' '.join(cmd[2:])}\n"); log.flush()
            rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT).returncode
            log.write(f"=== exit {rc} at {time.strftime('%Y-%m-%d %H:%M:%S%z')}\n"); log.flush()
            if os.path.exists(os.path.join(out, "traces.jsonl")):
                subprocess.run([sys.executable, os.path.join(HERE, "analyze.py"), "--run", out, "--freeze", fdir], stdout=subprocess.DEVNULL, stderr=log)


if __name__ == "__main__":
    main(sys.argv[1:])
