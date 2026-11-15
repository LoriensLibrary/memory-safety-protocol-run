"""Task 1 of the Paper 5 protocol: false-memory persistence.

  python memory_protocol/run_t1.py --model gemma-4-31b-it --mode dry
  python memory_protocol/run_t1.py --model gemma-4-31b-it --mode paid --ceiling 3 [--resume] [--limit 6]

Procedure (Reinhold 2026, section 6.3), per memory condition:
  seed    40 true teachings from the user and 50 false assistant inferences, through the condition's own write path
  phase 1 one probe session per false inference (50 sessions), before any time-to-live has passed
  ----    time passes: the session clock advances past the time-to-live
  phase 2 the second probe session per false inference (50 sessions)
Recorded per session: what CAMA retrieved (was the seeded false memory in it, at what rank, with what tags) and
the model's reply. Citation and action are scored afterwards by judge.py, blind to the condition.

No session writes to memory, so every session in a phase sees the same memory state.
"""
import argparse, hashlib, json, os, random, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "tools"))
import backend, session, items_t1   # noqa: E402
import guard, run as mainrun        # noqa: E402  (spend guard and helpers from the supporting study)

SEED = 2026111510
CONDITIONS = ("A", "B", "C_ttl", "C", "D", "C_gate", "C_hold")
TTL_SESSIONS = 3
CODE = ("backend.py", "cama_worker.py", "session.py", "items_t1.py", "run_t1.py")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def manifest(model, legend):
    return dict(task="T1 false-memory persistence", protocol="Reinhold (2026) Memory as Safety Infrastructure, section 6.3", model=model, seed=SEED,
                conditions=list(CONDITIONS), ttl_sessions=TTL_SESSIONS, top_k=5, legend=legend, max_tokens=6000, temperature=0.0,
                cama_commit=backend.CAMA_COMMIT, prompts_sha256=session.prompts_sha256(),
                items_sha256=hashlib.sha256(json.dumps([items_t1.BACKGROUND, items_t1.FALSE, sorted(items_t1.CONTRADICTED_BY_TEACHING)]).encode()).hexdigest(),
                code_sha256={f: sha(os.path.join(HERE, f)) for f in CODE})


def seed_memory(mem):
    """Background teachings and false inferences interleaved in one fixed order, so storage order tells nothing."""
    writes = [("user", t, None) for t in items_t1.BACKGROUND] + [("assistant", f[1], f[0]) for f in items_t1.FALSE]
    random.Random(SEED).shuffle(writes)
    seeded = {}
    for author, text, fid in writes:
        r = mem.write(text, author)
        if fid and r: seeded[fid] = r["memory_id"]
    return seeded


def canned(retrieved, seed_id, item):
    hit = next((m for m in retrieved.get("results", []) if m["id"] == seed_id), None)
    if hit is None: return "Here is a simple plan that should work for you."
    if hit["source_type"] == "inference": return f"I have an unconfirmed note that says: {item[1]} Is that right? If so I will plan around it."
    return f"Since {item[1][0].lower() + item[1][1:]} I would plan around that."


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True); p.add_argument("--mode", choices=("dry", "paid"), required=True)
    p.add_argument("--ceiling", type=float); p.add_argument("--resume", action="store_true"); p.add_argument("--limit", type=int)
    p.add_argument("--no-legend", action="store_true"); p.add_argument("--conditions", default=",".join(CONDITIONS)); p.add_argument("--tag", default="")
    a = p.parse_args()
    legend = not a.no_legend
    conds = a.conditions.split(",")
    tag = a.model.replace("-", "").replace(".", "")[:12] + ("_nolegend" if a.no_legend else "") + (f"_{a.tag}" if a.tag else "")
    out = os.path.join(ROOT, "runs_mp", f"t1_{tag}_{a.mode}")
    traces_path, ledger = os.path.join(out, "traces.jsonl"), os.path.join(out, "ledger.jsonl")
    man = manifest(a.model, legend)
    if os.path.exists(out) and not a.resume:
        if a.mode == "paid": raise SystemExit(f"{out} exists; use --resume or a --tag")
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, "raw"), exist_ok=True)
    mpath = os.path.join(out, "MANIFEST.json")
    if a.resume and os.path.exists(mpath):
        old = json.load(open(mpath, encoding="utf-8"))
        if {k: old[k] for k in man} != man: raise SystemExit("MANIFEST MISMATCH: code, items, prompts or settings changed since this run began")
    else:
        json.dump(dict(man, started=time.strftime("%Y-%m-%dT%H:%M:%S%z"), limit=a.limit), open(mpath, "w", encoding="utf-8"), indent=1)
    done = {(r["condition"], r["item"], r["phase"]) for r in mainrun.read_jsonl(traces_path)} if os.path.exists(traces_path) else set()
    g = None
    if a.mode == "paid":
        if not os.environ.get("ADAPTION_API_KEY"):
            os.environ["ADAPTION_API_KEY"] = open(mainrun.DEFAULT_KEY, encoding="utf-8-sig").read().strip()
        n_items = a.limit or len(items_t1.FALSE)
        calls = n_items * 2 * len(conds)
        g = guard.SpendGuard(a.model, a.ceiling, calls + max(20, calls // 10), ledger, min_interval=1.5, rawdir=os.path.join(out, "raw"))
        if a.resume and os.path.exists(ledger):
            spend = attempts = ncalls = 0
            for r in mainrun.read_jsonl(ledger):
                spend = r.get("spend_after", r.get("spend_after_debit", spend)); attempts = max(attempts, r.get("attempt", 0)); ncalls = max(ncalls, r.get("call", 0))
            g.restore(spend, attempts, ncalls)
        mainrun.hold_awake()
    falses = items_t1.FALSE[: a.limit] if a.limit else items_t1.FALSE
    t0, n_new, stopped = time.time(), 0, None
    with open(traces_path, "a", encoding="utf-8") as tf:
        for cond in conds:
            if stopped: break
            if all((cond, f[0], ph) in done for f in falses for ph in (1, 2)): continue
            db_dir = os.path.join(out, "db", cond)
            shutil.rmtree(db_dir, ignore_errors=True)       # memory is rebuilt from the same seed on a resume; no session writes to it
            mem = backend.Memory(cond, db_dir, ttl_sessions=TTL_SESSIONS, top_k=man["top_k"])
            try:
                seeded = seed_memory(mem)
                for phase in (1, 2):
                    if phase == 2:
                        for _ in range(TTL_SESSIONS + 1): mem.next_session()
                    state = collections_counter(mem.dump())
                    for item in falses:
                        if (cond, item[0], phase) in done or stopped: continue
                        # counterbalanced: half the items get the recall probe before the time-to-live and the task probe after, half the reverse
                        kind = ("recall", "task")[(phase - 1 + items_t1.FALSE.index(item)) % 2]
                        probe = item[2] if kind == "recall" else item[3]
                        retrieved = mem.retrieve(probe)
                        seed_id = seeded.get(item[0])
                        rank = next((i + 1 for i, m in enumerate(retrieved["results"]) if m["id"] == seed_id), None)
                        system, user = session.build(items_t1.USER_NAME, probe, retrieved, legend=legend, memory=(cond != "A"), gate=(cond == "C_gate"))
                        row = dict(task="T1", model=a.model, condition=cond, item=item[0], phase=phase, probe_kind=kind, probe=probe, false_inference=item[1],
                                   contradicted_by_teaching=item[0] in items_t1.CONTRADICTED_BY_TEACHING,
                                   retrieved=[dict(id=m["id"], text=m["raw_text"], source_type=m["source_type"], status=m["status"]) for m in retrieved["results"]],
                                   seed_retrieved=rank is not None, seed_rank=rank,
                                   seed_tag=next((f"{m['source_type']}|{m['status']}" for m in retrieved["results"] if m["id"] == seed_id), None),
                                   memory_state=state, status="complete")
                        try:
                            if g:
                                rec = g.send(system, user, man["max_tokens"])
                                row.update(reply=rec["text"], input_tokens=rec["input_tokens"], output_tokens=rec["output_tokens"], cost=rec["cost"], elapsed_s=rec["elapsed_s"])
                            else:
                                row.update(reply=canned(retrieved, seed_id, item))
                            if not (row["reply"] or "").strip(): row["status"] = "empty_reply"
                        except guard.BudgetStop as e:
                            stopped = str(e); row.update(status="budget_stopped", reply=None, error=str(e))
                        except guard.CallFailed as e:
                            row.update(status="error", reply=None, error=str(e))
                        tf.write(json.dumps(row) + "\n"); tf.flush(); n_new += 1
                        if g and n_new % 25 == 0: print(f"  {n_new} sessions, {g.attempts} attempts, {g.spend:.4f} credits, {time.time() - t0:.0f}s", flush=True)
                paths = mem.paths()
                if paths and (paths["blocked"] or not all(d.startswith(os.path.realpath(db_dir)) for d in paths["db"])):
                    raise SystemExit(f"ISOLATION FAILURE in condition {cond}: {paths}")
            finally:
                mem.close()
    ex = dict(mode=a.mode, new_sessions=n_new, stopped=stopped, finished=time.strftime("%Y-%m-%dT%H:%M:%S%z"), wall_s=round(time.time() - t0, 1),
              spend=round(g.spend, 6) if g else 0.0, attempts=g.attempts if g else 0)
    with open(os.path.join(out, "EXECUTION.jsonl"), "a", encoding="utf-8") as f: f.write(json.dumps(ex) + "\n")
    print(json.dumps(ex)); print("out:", out)


def collections_counter(rows):
    out = {}
    for r in rows:
        k = f"{r['source_type']}|{r['status']}"; out[k] = out.get(k, 0) + 1
    return out


if __name__ == "__main__":
    main()
