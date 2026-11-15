"""Overnight queue, one cohort at a time (the provider's rate limit is per account):
  wait for the given pid (the F1 to F4 follow-up launcher) -> F5 on gemma-4-31b-it -> F5 on deepseek-v4-flash
  -> exploratory tier (launch_exploratory.py). Safe to start again: every step resumes or skips what is finished.

  python tools/launch_queue.py [pid-to-wait-for]
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import followup2, launch_exploratory   # noqa: E402

F5_MODELS = ("gemma-4-31b-it", "deepseek-v4-flash")


def f5(model, logs):
    fdir, out = followup2.paths(model)
    frz = json.load(open(os.path.join(fdir, "FREEZE.json"), encoding="utf-8"))
    paid = out + "_paid"
    if os.path.exists(os.path.join(paid, "EXECUTION.jsonl")) and len([1 for _ in open(os.path.join(paid, "traces.jsonl"), encoding="utf-8")]) >= frz["slots"]:
        return                                              # already complete
    claimed = os.path.exists(os.path.join(ROOT, "runs", "claims", f"{frz['freeze_id']}.json"))
    cmd = [sys.executable, os.path.join(HERE, "followup2.py"), "run", "--model", model, "--mode", "paid"]
    if claimed and os.path.exists(os.path.join(paid, "traces.jsonl")): cmd.append("--resume")
    with open(os.path.join(logs, f"{os.path.basename(fdir)}.log"), "a", encoding="utf-8") as log:
        log.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S%z')} {' '.join(cmd[2:])}\n"); log.flush()
        rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT).returncode
        log.write(f"=== exit {rc} at {time.strftime('%Y-%m-%d %H:%M:%S%z')}\n"); log.flush()
        if os.path.exists(os.path.join(paid, "traces.jsonl")):
            subprocess.run([sys.executable, os.path.join(HERE, "followup2.py"), "analyze", "--model", model], stdout=subprocess.DEVNULL, stderr=log)


def main(wait_pid=None):
    logs = os.path.join(ROOT, "runs", "launch_logs"); os.makedirs(logs, exist_ok=True)
    while wait_pid and launch_exploratory.alive(wait_pid): time.sleep(20)
    for m in F5_MODELS: f5(m, logs)
    launch_exploratory.main(None)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
