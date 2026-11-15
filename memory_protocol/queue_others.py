"""Run the second judge pass (judge_others.py, gemma judge) for both Task 1 runs, but only once the Task 1 launcher
has stopped using the gemma judge, so two gemma jobs do not share one rate limit. Safe to start again: resumes.

  python memory_protocol/queue_others.py
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LOG1 = os.path.join(ROOT, "runs_mp", "launch_t1.log")


def gemma_judge_free():
    text = open(LOG1, encoding="utf-8", errors="replace").read()
    return "--judge deepseek-v4-flash" in text          # the launcher's remaining steps use the deepseek judge


while not gemma_judge_free(): time.sleep(20)
with open(os.path.join(ROOT, "runs_mp", "queue_others.log"), "a", encoding="utf-8") as log:
    for run in ("t1_gemma431bit_paid", "t1_deepseekv4fl_paid"):
        cmd = [sys.executable, os.path.join(HERE, "judge_others.py"), "--run", os.path.join("runs_mp", run), "--judge", "gemma-4-31b-it", "--ceiling", "2.5", "--interval", "1.5"]
        log.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S%z')} {' '.join(cmd[1:])}\n"); log.flush()
        rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT).returncode
        log.write(f"=== exit {rc} at {time.strftime('%Y-%m-%d %H:%M:%S%z')}\n"); log.flush()
