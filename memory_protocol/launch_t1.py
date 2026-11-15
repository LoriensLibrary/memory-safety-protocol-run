"""Task 1, start to finish, one step at a time (the provider's rate limit is per account). Safe to start again:
each step resumes what it had begun and skips what is finished.

  python memory_protocol/launch_t1.py
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable
MODELS = (("gemma-4-31b-it", "gemma431bit", 2.0), ("deepseek-v4-flash", "deepseekv4fl", 4.0))


def step(log, cmd):
    log.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S%z')} {' '.join(cmd[1:])}\n"); log.flush()
    rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT).returncode
    log.write(f"=== exit {rc} at {time.strftime('%Y-%m-%d %H:%M:%S%z')}\n"); log.flush()
    return rc


def main():
    os.makedirs(os.path.join(ROOT, "runs_mp"), exist_ok=True)
    with open(os.path.join(ROOT, "runs_mp", "launch_t1.log"), "a", encoding="utf-8") as log:
        for model, tag, ceiling in MODELS:
            out = os.path.join(ROOT, "runs_mp", f"t1_{tag}_paid")
            cmd = [PY, os.path.join(HERE, "run_t1.py"), "--model", model, "--mode", "paid", "--ceiling", str(ceiling)]
            if os.path.exists(os.path.join(out, "traces.jsonl")): cmd.append("--resume")
            step(log, cmd)
        for _, tag, _ in MODELS:                            # every reply judged by gemma; a fixed sample of 300 also judged by deepseek
            run_dir = os.path.join("runs_mp", f"t1_{tag}_paid")
            step(log, [PY, os.path.join(HERE, "judge.py"), "--run", run_dir, "--judge", "gemma-4-31b-it", "--ceiling", "2"])
        for _, tag, _ in MODELS:
            run_dir = os.path.join("runs_mp", f"t1_{tag}_paid")
            step(log, [PY, os.path.join(HERE, "judge.py"), "--run", run_dir, "--judge", "deepseek-v4-flash", "--ceiling", "3", "--sample", "300"])


if __name__ == "__main__":
    main()
