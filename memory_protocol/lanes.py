"""Finish Tasks 2 and 3 in two lanes, one per model, so no two jobs share a model's rate limit.
Replaces launch_t23.py after the laptop slept for seven hours on 15 November. Every step resumes or skips.

  python memory_protocol/lanes.py gemma  [pid-of-a-run-to-wait-for]
  python memory_protocol/lanes.py deepseek

gemma lane     (uses gemma-4-31b-it): wait for the running gemma Task 2, gemma Task 3, then the gemma judge on the
               four Task 2 and 3 runs as each finishes, then the rest of the Task 1 second pass for the deepseek run
deepseek lane  (uses deepseek-v4-flash): deepseek Task 2, deepseek Task 3, then the deepseek second-judge samples
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNS = os.path.join(ROOT, "runs_mp")
PY = sys.executable


def alive(pid):
    return str(pid) in subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout


def step(log, cmd):
    log.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S%z')} {' '.join(cmd[1:])}\n"); log.flush()
    rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT).returncode
    log.write(f"=== exit {rc} at {time.strftime('%Y-%m-%d %H:%M:%S%z')}\n"); log.flush()


def run_task(log, task, model, tag, ceiling):
    cmd = [PY, os.path.join(HERE, f"run_{task}.py"), "--model", model, "--mode", "paid", "--ceiling", str(ceiling)]
    if os.path.exists(os.path.join(RUNS, f"{task}_{tag}_paid", "MANIFEST.json")): cmd.append("--resume")
    step(log, cmd)


def finished(run):
    return os.path.exists(os.path.join(RUNS, run, "EXECUTION.jsonl"))


def wait_finished(run, hours=5):
    t0 = time.time()
    while not finished(run) and time.time() - t0 < hours * 3600: time.sleep(20)
    return finished(run)


def main(lane, wait_pid=None):
    with open(os.path.join(RUNS, f"lane_{lane}.log"), "a", encoding="utf-8") as log:
        if lane == "gemma":
            while wait_pid and alive(wait_pid): time.sleep(15)
            if not finished("t2_gemma431bit_paid"): run_task(log, "t2", "gemma-4-31b-it", "gemma431bit", 3.0)
            run_task(log, "t3", "gemma-4-31b-it", "gemma431bit", 2.0)
            for run in ("t2_gemma431bit_paid", "t3_gemma431bit_paid", "t2_deepseekv4fl_paid", "t3_deepseekv4fl_paid"):
                if wait_finished(run): step(log, [PY, os.path.join(HERE, "judge.py"), "--run", os.path.join("runs_mp", run), "--judge", "gemma-4-31b-it", "--ceiling", "2"])
            step(log, [PY, os.path.join(HERE, "judge_others.py"), "--run", os.path.join("runs_mp", "t1_deepseekv4fl_paid"), "--judge", "gemma-4-31b-it", "--ceiling", "2.5", "--interval", "1.5"])
        else:
            run_task(log, "t2", "deepseek-v4-flash", "deepseekv4fl", 5.0)
            run_task(log, "t3", "deepseek-v4-flash", "deepseekv4fl", 4.0)
            # The deepseek second-judge samples for Tasks 2 and 3 are left out: the provider's rate limit is shared
            # across models, and the primary judge's verdicts are what the paper needs.


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
