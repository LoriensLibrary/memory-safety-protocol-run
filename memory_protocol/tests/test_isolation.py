"""The first thing to prove: the experiment's CAMA never touches the operator's real memory.

  python memory_protocol/tests/test_isolation.py

Runs real CAMA (pinned public commit) in a scratch directory, stores and retrieves, and checks every database and
every written file it opened. No model calls, no network.
"""
import hashlib, os, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import backend   # noqa: E402

REAL_DB = os.path.join(os.path.expanduser("~"), ".cama", "memory.db")
RESULTS = []


def check(name, fn):
    try:
        fn(); RESULTS.append((name, True, ""))
    except Exception as e:   # noqa: BLE001
        RESULTS.append((name, False, f"{type(e).__name__}: {e}"))


scratch = tempfile.mkdtemp(prefix="memproto_iso_")
state = {}


def t_pinned():
    import subprocess
    head = subprocess.run(["git", "-C", backend.CAMA_SRC, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", backend.CAMA_SRC, "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
    assert head == backend.CAMA_COMMIT, head
    assert not dirty, f"pinned CAMA has local changes: {dirty[:200]}"


def t_roundtrip():
    m = backend.Memory("C", os.path.join(scratch, "c"))
    state["m"] = m
    a = m.write("The user's dog is named Biscuit.", "user", evidence_quote="my dog Biscuit")
    b = m.write("The user may be allergic to cats.", "assistant", confidence=0.4)
    assert a["source_type"] == "teaching" and a["status"] == "durable", a
    assert b["source_type"] == "inference" and b["status"] == "provisional" and b["needs_user_confirmation"], b
    got = m.retrieve("Tell me about my pets")
    assert got["used_embeddings"] is True, "retrieval ran without the embedding model"
    texts = {r["raw_text"]: r for r in got["results"]}
    assert "The user's dog is named Biscuit." in texts and "The user may be allergic to cats." in texts, list(texts)
    assert texts["The user may be allergic to cats."]["source_type"] == "inference" and texts["The user may be allergic to cats."]["status"] == "provisional"
    state["inf_id"] = b["memory_id"]


def t_paths():
    p = state["m"].paths()
    root = os.path.realpath(scratch)
    assert p["blocked"] == [], p["blocked"]
    assert p["db"] and all(d.startswith(root) for d in p["db"]), p["db"]
    assert all(w.startswith(root) for w in p["write"]), p["write"]
    assert os.path.realpath(REAL_DB) not in p["db"]


def t_reject_and_confirm():
    m = state["m"]
    m.reject(state["inf_id"], "user said no")
    got = m.retrieve("Tell me about my pets")
    assert all(r["id"] != state["inf_id"] for r in got["results"]), "a rejected inference was retrieved"
    c = m.write("The user probably prefers morning meetings.", "assistant")
    m.confirm(c["memory_id"])
    row = next(r for r in m.dump() if r["id"] == c["memory_id"])
    assert row["status"] == "durable" and row["source_type"] == "inference", row


def t_conditions():
    b = backend.Memory("B", os.path.join(scratch, "b"))
    r = b.write("The user may be allergic to cats.", "assistant")
    assert r["source_type"] == "teaching" and r["status"] == "durable", "naive condition must store everything as a durable teaching"
    b.close()
    t = backend.Memory("C_ttl", os.path.join(scratch, "t"), ttl_sessions=2)
    r = t.write("The user may be allergic to cats.", "assistant")
    keep = t.write("The user's dog is named Biscuit.", "user")
    t.next_session()
    assert any(x["id"] == r["memory_id"] for x in t.retrieve("allergic to cats")["results"]), "expired before its time-to-live"
    out = t.next_session()
    assert r["memory_id"] in out["ids"], out
    ids = [x["id"] for x in t.retrieve("allergic to cats")["results"]]
    assert r["memory_id"] not in ids and keep["memory_id"] in ids, "time-to-live must expire the inference and keep the teaching"
    t.close()
    a = backend.Memory("A", os.path.join(scratch, "a"))
    assert a.write("x", "user") is None and a.retrieve("x")["results"] == []


def t_gate_conditions():
    import session
    h = backend.Memory("C_hold", os.path.join(scratch, "h"))
    inf = h.write("Dana is allergic to cats.", "assistant"); h.write("Dana's dog is a beagle named Biscuit.", "user")
    assert all(r["id"] != inf["memory_id"] for r in h.retrieve("What do you know about me and cats?")["results"]), "C_hold retrieved an unconfirmed inference"
    h.confirm(inf["memory_id"])
    assert any(r["id"] == inf["memory_id"] for r in h.retrieve("What do you know about me and cats?")["results"]), "C_hold must retrieve an inference once the user confirms it"
    h.close()
    g = backend.Memory("C_gate", os.path.join(scratch, "g"))
    g.write("Dana is allergic to cats.", "assistant"); g.write("Dana's dog is a beagle named Biscuit.", "user")
    got = g.retrieve("What do you know about me and cats?")
    _, plain = session.build("Dana", "q", got); _, gated = session.build("Dana", "q", got, gate=True)
    head = session.GATE_HEAD.format(name="Dana")
    assert head not in plain and head in gated
    assert gated.index("Biscuit") < gated.index(head) < gated.index("allergic to cats"), "the unconfirmed inference must sit under the gate heading, the teaching above it"
    assert sorted(l for l in plain.splitlines() if l.startswith("- [")) == sorted(l for l in gated.splitlines() if l.startswith("- [")), "gate changes placement only, never the memories shown"
    g.close()


def t_guard_bites():
    """Point the worker at the real database on purpose: it must refuse to start."""
    import subprocess
    env = backend.worker_env(os.path.join(scratch, "evil"))
    env["CAMA_DB_PATH"] = REAL_DB
    p = subprocess.run([sys.executable, os.path.join(os.path.dirname(HERE), "cama_worker.py")], input="", capture_output=True, text=True, env=env, timeout=180)
    assert '"ready"' not in p.stdout, "worker started against the real database"
    assert "blocked" in p.stderr or "AssertionError" in p.stderr or "PermissionError" in p.stderr, p.stderr[-400:]


if __name__ == "__main__":
    before = (os.path.getsize(REAL_DB), ) if os.path.exists(REAL_DB) else None
    check("I1 CAMA source is the pinned public commit with no local changes", t_pinned)
    check("I2 real CAMA stores a teaching and an inference and retrieves both with provenance, using embeddings", t_roundtrip)
    check("I3 every database and every written file is inside the scratch directory; nothing was blocked", t_paths)
    check("I4 reject removes an inference from retrieval; confirm promotes one to durable", t_reject_and_confirm)
    check("I5 conditions: B stores an inference as a durable teaching; C_ttl expires it on schedule; A has no memory", t_conditions)
    check("I6 a worker pointed at the real memory database refuses to start", t_guard_bites)
    check("I7 added conditions: C_hold withholds an inference until confirmed; C_gate moves it under a gate heading and shows the same memories", t_gate_conditions)
    try:
        state["m"].close()
    except Exception:   # noqa: BLE001
        pass
    shutil.rmtree(scratch, ignore_errors=True)
    for name, ok, why in RESULTS:
        print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"\n        {why}"))
    bad = sum(not ok for _, ok, _ in RESULTS)
    print(f"\n{len(RESULTS) - bad}/{len(RESULTS)} passed")
    sys.exit(1 if bad else 0)
