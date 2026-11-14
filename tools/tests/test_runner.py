"""Adversarial checks for the freeze and the runner. No network, no spend.

Run:  python tools/tests/test_runner.py
"""
import json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import items, run, guard   # noqa: E402

NAME = "selftest_runner"
FDIR = os.path.join(ROOT, "holdout", NAME)
OUT = os.path.join(ROOT, "runs", f"{NAME}_dry")
RESULTS = []


def sh(*args):
    return subprocess.run([sys.executable, os.path.join(TOOLS, "run.py"), *args], capture_output=True, text=True)


def clean():
    shutil.rmtree(FDIR, ignore_errors=True); shutil.rmtree(OUT, ignore_errors=True)


def check(name, fn):
    try:
        fn(); RESULTS.append((name, True, ""))
    except Exception as e:   # noqa: BLE001
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))


def fresh():
    clean()
    r = sh("freeze", "--name", NAME, "--split", "dev", "--seed", "3", "--n", "4", "--model", "gemma-4-31b-it", "--ceiling", "1")
    assert r.returncode == 0, r.stderr or r.stdout


def edit(fname, fn):
    p = os.path.join(FDIR, fname); obj = json.load(open(p, encoding="utf-8")); fn(obj); json.dump(obj, open(p, "w", encoding="utf-8"), indent=1)


def t_tamper():
    cases = {
        "raised ceiling": ("FREEZE.json", lambda f: f.__setitem__("ceiling", 500)),
        "swapped model": ("FREEZE.json", lambda f: f.__setitem__("model", "deepseek-v4-flash")),
        "raised attempt cap": ("FREEZE.json", lambda f: f.__setitem__("max_attempts", 10 ** 6)),
        "edited truth": ("instances.json", lambda inst: inst[0].__setitem__("truth", inst[0]["truth"] + 1)),
        "edited source text": ("instances.json", lambda inst: inst[3]["sources"][0].__setitem__("text", inst[3]["sources"][0]["text"] + " ")),
        "reordered arms": ("instances.json", lambda inst: inst[1].__setitem__("arm_order", list(reversed(inst[1]["arm_order"])))),
        "dropped an item": ("instances.json", lambda inst: inst.pop()),
    }
    for label, (fname, fn) in cases.items():
        fresh(); edit(fname, fn)
        r = sh("run", "--freeze", FDIR, "--mode", "dry")
        assert r.returncode != 0 and "FREEZE MISMATCH" in (r.stderr + r.stdout), f"{label}: accepted"
        assert not os.path.exists(os.path.join(OUT, "traces.jsonl")), f"{label}: dispatched"


def t_refrozen_instances_still_caught():
    """Editing an item AND recomputing its hash in FREEZE.json must still fail (freeze_id and seed regeneration)."""
    fresh()
    edit("instances.json", lambda inst: inst[0].__setitem__("truth", inst[0]["truth"] + 1))
    inst = json.load(open(os.path.join(FDIR, "instances.json"), encoding="utf-8"))
    edit("FREEZE.json", lambda f: f.__setitem__("instances_sha256", run.sha_obj(inst)))
    r = sh("run", "--freeze", FDIR, "--mode", "dry")
    assert r.returncode != 0 and "FREEZE MISMATCH" in (r.stderr + r.stdout)


def t_dry_complete_and_resume():
    fresh()
    r = sh("run", "--freeze", FDIR, "--mode", "dry"); assert r.returncode == 0, r.stderr
    tp = os.path.join(OUT, "traces.jsonl"); lines = open(tp, encoding="utf-8").read().splitlines()
    inst = json.load(open(os.path.join(FDIR, "instances.json"), encoding="utf-8"))
    want = {(it["tid"], arm) for it in inst for arm in it["arm_order"]}
    assert {(json.loads(x)["tid"], json.loads(x)["arm"]) for x in lines} == want and len(lines) == len(want)
    open(tp, "w", encoding="utf-8").write("\n".join(lines[: len(lines) // 3]) + "\n")       # simulate a crash a third of the way in
    r = sh("run", "--freeze", FDIR, "--mode", "dry", "--resume"); assert r.returncode == 0, r.stderr
    after = [json.loads(x) for x in open(tp, encoding="utf-8").read().splitlines()]
    keys = [(x["tid"], x["arm"]) for x in after]
    assert len(keys) == len(set(keys)) == len(want), "resume duplicated or lost slots"
    assert [json.dumps(x) for x in after[: len(lines) // 3]] == [json.dumps(json.loads(x)) for x in lines[: len(lines) // 3]], "resume rewrote finished slots"


def t_power_loss():
    fresh()
    r = sh("run", "--freeze", FDIR, "--mode", "dry"); assert r.returncode == 0, r.stderr
    tp = os.path.join(OUT, "traces.jsonl"); lines = open(tp, encoding="utf-8").read().splitlines()
    open(tp, "w", encoding="utf-8").write("\n".join(lines[:20]) + "\n" + lines[20][: len(lines[20]) // 2])   # power died mid-write
    r = sh("run", "--freeze", FDIR, "--mode", "dry", "--resume"); assert r.returncode == 0, (r.stdout + r.stderr)[-300:]
    after = [json.loads(x) for x in open(tp, encoding="utf-8").read().splitlines()]
    keys = [(x["tid"], x["arm"]) for x in after]
    assert len(keys) == len(set(keys)) == len(lines), "a half-written line broke resume"
    open(tp, "w", encoding="utf-8").write("\n".join(lines[:5]) + "\n" + "{broken\n" + "\n".join(lines[6:10]) + "\n")   # damage in the middle
    r = sh("run", "--freeze", FDIR, "--mode", "dry", "--resume")
    assert r.returncode != 0 and "refusing to continue" in (r.stdout + r.stderr), "mid-file corruption must stop the run"


def t_paid_needs_key_and_single_claim():
    fresh()
    env = dict(os.environ); env.pop("ADAPTION_API_KEY", None)
    r = subprocess.run([sys.executable, os.path.join(TOOLS, "run.py"), "run", "--freeze", FDIR, "--mode", "paid", "--key-file", os.path.join(FDIR, "no_such.key")],
                       capture_output=True, text=True, env=env)
    assert r.returncode != 0 and "no Adaption key" in (r.stderr + r.stdout)
    frz = json.load(open(os.path.join(FDIR, "FREEZE.json"), encoding="utf-8"))
    claim = os.path.join(ROOT, "runs", "claims", f"{frz['freeze_id']}.json")
    assert not os.path.exists(claim), "a launch that failed its preconditions burned the single-use claim"
    fake = os.path.join(FDIR, "fake.key"); open(fake, "w").write("not-a-real-key")
    env_bad = dict(env, ADAPTION_BASE_URL="http://127.0.0.1:9")            # wrong endpoint: must be refused, and must not burn the claim either
    r = subprocess.run([sys.executable, os.path.join(TOOLS, "run.py"), "run", "--freeze", FDIR, "--mode", "paid", "--key-file", fake], capture_output=True, text=True, env=env_bad)
    assert r.returncode != 0 and "registered Adaption hosted endpoint" in (r.stderr + r.stdout), r.stderr[-300:]
    assert not os.path.exists(claim), "a refused endpoint burned the claim"
    os.makedirs(os.path.dirname(claim), exist_ok=True); open(claim, "w").write("{}")   # someone already executed this freeze
    try:
        r2 = subprocess.run([sys.executable, os.path.join(TOOLS, "run.py"), "run", "--freeze", FDIR, "--mode", "paid", "--key-file", fake], capture_output=True, text=True, env=env)
        assert r2.returncode != 0 and "already has a paid execution" in (r2.stderr + r2.stdout), (r2.stdout + r2.stderr)[-300:]
        r3 = subprocess.run([sys.executable, os.path.join(TOOLS, "run.py"), "run", "--freeze", FDIR, "--mode", "paid", "--resume", "--key-file", fake], capture_output=True, text=True, env=env)
        assert r3.returncode != 0 and "nothing to resume" in (r3.stderr + r3.stdout), "resume with no prior traces must be refused"
    finally:
        os.remove(claim); shutil.rmtree(os.path.join(ROOT, "runs", f"{NAME}_paid"), ignore_errors=True)


IT = items.make_item("V3", 2, seed=9)
IDS = [s["id"] for s in IT["sources"]]
GOOD = json.dumps(items.rule_decide(IT))
LOOK = json.dumps(dict(decision="lookup", answer=None, sources=[]))


def asker(replies):
    seq = list(replies); seen = []

    def ask(system, user):
        seen.append((system, user)); return dict(text=seq.pop(0), input_tokens=10, output_tokens=5, cost=0.001, elapsed_s=0.1, stop_reason="end_turn")
    ask.seen = seen
    return ask


def t_slot_logic():
    a = asker([LOOK, GOOD]); row = run.run_slot(IT, "lookup", a)
    assert row["status"] == "complete" and row["lookup_taken"] is True and row["calls"] == 2 and row["outcome"] == "correct"
    assert "PLATFORM PROVENANCE" not in a.seen[0][1] and "PLATFORM PROVENANCE" in a.seen[1][1]
    a = asker([GOOD]); row = run.run_slot(IT, "lookup", a)
    assert row["lookup_taken"] is False and row["calls"] == 1
    row = run.run_slot(IT, "lookup", asker([LOOK, LOOK]))
    assert row["status"] == "invalid" and row["calls"] == 2, "a second lookup must be invalid"
    row = run.run_slot(IT, "bare", asker([LOOK]))
    assert row["status"] == "invalid", "lookup must be invalid where it is not offered"
    row = run.run_slot(IT, "env_json", asker(["I think the answer is 42."]))
    assert row["status"] == "invalid" and row.get("outcome") is None
    row = run.run_slot(IT, "rule", asker([]))
    assert row["calls"] == 0 and row["outcome"] == "correct"
    for exc in (guard.BudgetStop("x"), guard.CallFailed("y")):
        def boom(system, user, _e=exc): raise _e
        try:
            run.run_slot(IT, "bare", boom)
        except type(exc):
            continue
        raise AssertionError("runner swallowed a guard exception inside the slot")


if __name__ == "__main__":
    check("F1 seven kinds of tampering with a freeze are refused before any dispatch", t_tamper)
    check("F2 an edited item with a recomputed hash is still refused", t_refrozen_instances_still_caught)
    check("F3 a dry run fills every registered slot once; resume after a crash neither duplicates nor rewrites", t_dry_complete_and_resume)
    check("F4 a failed launch does not burn the claim; an existing claim refuses a second launch; empty resume is refused", t_paid_needs_key_and_single_claim)
    check("F6 a half-written last line (power loss) is repaired on resume; damage in the middle stops the run", t_power_loss)
    check("F5 lookup is two stateless calls, a second lookup is invalid, guard stops are not swallowed", t_slot_logic)
    clean()
    for name, ok, why in RESULTS:
        print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"\n        {why}"))
    bad = sum(not ok for _, ok, _ in RESULTS)
    print(f"\n{len(RESULTS) - bad}/{len(RESULTS)} passed")
    sys.exit(1 if bad else 0)
