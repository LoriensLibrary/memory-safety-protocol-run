"""Two judge jobs, each run only while its model is not being used by the Tasks 2 and 3 launcher.

  1. now (the launcher is on gemma): the deepseek second-judge sample for the gemma Task 1 run. The first try hit a
     provider outage (62 calls, all HTTP 5xx, no verdict); its files are moved aside, not deleted.
  2. when the launcher reaches its deepseek runs: the rest of the gemma second pass (judge_others) for the deepseek run.

  python memory_protocol/queue2.py
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNS = os.path.join(ROOT, "runs_mp")


def step(log, cmd):
    log.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S%z')} {' '.join(cmd[1:])}\n"); log.flush()
    rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT).returncode
    log.write(f"=== exit {rc} at {time.strftime('%Y-%m-%d %H:%M:%S%z')}\n"); log.flush()


with open(os.path.join(RUNS, "queue2.log"), "a", encoding="utf-8") as log:
    g = os.path.join(RUNS, "t1_gemma431bit_paid")
    marker = os.path.join(g, "outage_2026-11-15_1509")
    if not os.path.exists(marker):
        os.makedirs(marker)
        for name in ("judgments_deepseekv4fl.jsonl", "ledger_judge_deepseekv4fl.jsonl", "raw_judge_deepseekv4fl"):
            if os.path.exists(os.path.join(g, name)): os.rename(os.path.join(g, name), os.path.join(marker, name))
    step(log, [sys.executable, os.path.join(HERE, "judge.py"), "--run", os.path.join("runs_mp", "t1_gemma431bit_paid"), "--judge", "deepseek-v4-flash", "--ceiling", "3", "--sample", "300"])
    t23 = os.path.join(RUNS, "launch_t23.log")
    while not (os.path.exists(t23) and "--model deepseek-v4-flash" in open(t23, encoding="utf-8", errors="replace").read()): time.sleep(20)
    step(log, [sys.executable, os.path.join(HERE, "judge_others.py"), "--run", os.path.join("runs_mp", "t1_deepseekv4fl_paid"), "--judge", "gemma-4-31b-it", "--ceiling", "2.5", "--interval", "1.5"])
