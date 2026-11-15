"""Tasks 2 and 3 on both models, then their judges, one step at a time. Waits for the Task 1 launcher first.
Safe to start again: every step resumes or skips what is finished.

  python memory_protocol/launch_t23.py [pid-to-wait-for]
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable
MODELS = (("gemma-4-31b-it", "gemma431bit", 3.0, 2.0), ("deepseek-v4-flash", "deepseekv4fl", 5.0, 4.0))


def alive(pid):
    return str(pid) in subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout


def step(log, cmd):
    log.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S%z')} {' '.join(cmd[1:])}\n"); log.flush()
    rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT).returncode
    log.write(f"=== exit {rc} at {time.strftime('%Y-%m-%d %H:%M:%S%z')}\n"); log.flush()


def main(wait_pid=None):
    while wait_pid and alive(wait_pid): time.sleep(20)
    with open(os.path.join(ROOT, "runs_mp", "launch_t23.log"), "a", encoding="utf-8") as log:
        for model, tag, c2, c3 in MODELS:
            for task, ceiling in (("t2", c2), ("t3", c3)):
                cmd = [PY, os.path.join(HERE, f"run_{task}.py"), "--model", model, "--mode", "paid", "--ceiling", str(ceiling)]
                if os.path.exists(os.path.join(ROOT, "runs_mp", f"{task}_{tag}_paid", "MANIFEST.json")): cmd.append("--resume")
                step(log, cmd)
        runs = [os.path.join("runs_mp", f"{task}_{tag}_paid") for _, tag, _, _ in MODELS for task in ("t2", "t3")]
        for r in runs: step(log, [PY, os.path.join(HERE, "judge.py"), "--run", r, "--judge", "gemma-4-31b-it", "--ceiling", "2"])
        for r in runs: step(log, [PY, os.path.join(HERE, "judge.py"), "--run", r, "--judge", "deepseek-v4-flash", "--ceiling", "3", "--sample", "200"])


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
