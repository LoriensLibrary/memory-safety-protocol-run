"""A CAMA process confined to one scratch directory. Speaks JSON lines on stdin/stdout.

Started only by memory_protocol/backend.py, with an environment that points every CAMA path at the scratch
directory. Before CAMA is imported this file installs three guards and they stay on for the life of the process:

  1. sqlite3.connect refuses any database path outside the scratch directory;
  2. open() for writing refuses any path outside the scratch directory;
  3. socket connections are refused (the embedding model is loaded from the local cache, offline).

So a bug in this harness, or a CAMA code path that ignores CAMA_DB_PATH, fails loudly instead of touching the
operator's real memory at ~/.cama/memory.db. Every path opened is recorded and returned by the `paths` op.

CAMA itself is the public repository at a pinned commit, unmodified: this file only calls its own tool functions.
"""
import asyncio, builtins, json, os, socket, sqlite3, sys

SCRATCH = os.path.realpath(os.environ["MEMPROTO_SCRATCH"])
CAMA_SRC = os.path.realpath(os.environ["MEMPROTO_CAMA_SRC"])
READ_OK = tuple(os.path.realpath(p) for p in os.environ.get("MEMPROTO_READ_OK", "").split(os.pathsep) if p)
TOUCHED = {"db": set(), "write": set(), "blocked": []}


def _inside(path, roots):
    try:
        rp = os.path.realpath(str(path))
    except Exception:   # noqa: BLE001
        return False
    return any(rp == r or rp.startswith(r + os.sep) for r in roots)


_real_connect = sqlite3.connect


def _guarded_connect(database, *a, **kw):
    name = str(database)
    if name != ":memory:" and not name.startswith("file::memory:"):
        target = name[5:].split("?")[0] if name.startswith("file:") else name
        if not _inside(target, (SCRATCH,)):
            TOUCHED["blocked"].append(("sqlite", target)); raise PermissionError(f"blocked database outside scratch: {target}")
        TOUCHED["db"].add(os.path.realpath(target))
    return _real_connect(database, *a, **kw)


sqlite3.connect = _guarded_connect
_real_open = builtins.open


def _guarded_open(file, mode="r", *a, **kw):
    if isinstance(file, (str, bytes, os.PathLike)) and any(ch in str(mode) for ch in "wax+"):
        if not _inside(file, (SCRATCH,)):
            TOUCHED["blocked"].append(("write", str(file))); raise PermissionError(f"blocked write outside scratch: {file}")
        TOUCHED["write"].add(os.path.realpath(str(file)))
    return _real_open(file, mode, *a, **kw)


builtins.open = _guarded_open
import pathlib as _pathlib                                 # noqa: E402
if hasattr(_pathlib, "_NormalAccessor"):                   # Python 3.10: Path.open goes through this accessor, not builtins.open
    _pathlib._NormalAccessor.open = staticmethod(_guarded_open)
LOOP = asyncio.new_event_loop()                            # made before the network guard: on Windows the loop wires itself with a loopback socket pair
_real_sock_connect = socket.socket.connect


def _no_network(self, address):
    TOUCHED["blocked"].append(("socket", str(address))); raise PermissionError(f"blocked network connection: {address}")


socket.socket.connect = _no_network

sys.path.insert(0, CAMA_SRC)
_out = sys.stdout
sys.stdout = sys.stderr                                    # CAMA logs to stdout/stderr; keep the reply channel clean
import cama_mcp                                            # noqa: E402
from mcp_sections import memory_lifecycle as ml, retrieval as rt   # noqa: E402

assert os.path.realpath(cama_mcp.DB_PATH).startswith(SCRATCH), cama_mcp.DB_PATH


def _rows(sql, params=()):
    c = cama_mcp.get_db()
    try:
        return [dict(r) for r in c.execute(sql, params).fetchall()]
    finally:
        c.close()


def _exec(sql, params=()):
    c = cama_mcp.get_db()
    try:
        n = c.execute(sql, params).rowcount; c.commit(); return n
    finally:
        c.close()


async def handle(op, a):
    if op == "store_teaching":
        return json.loads(await ml.cama_store_teaching(cama_mcp.StoreTeachingInput(raw_text=a["text"], memory_type=a.get("memory_type", "experience"),
                                                                                context=a.get("context"), evidence_quote=a.get("evidence_quote"))))
    if op == "store_inference":
        return json.loads(await ml.cama_store_inference(cama_mcp.StoreInferenceInput(raw_text=a["text"], memory_type=a.get("memory_type", "pattern"),
                                                                                  context=a.get("context"), confidence=a.get("confidence", 0.5),
                                                                                  evidence_quotes=a.get("evidence_quotes", []))))
    if op == "confirm": return json.loads(await ml.cama_confirm_memory(int(a["id"])))
    if op == "reject": return json.loads(await ml.cama_reject_memory(int(a["id"]), a.get("reason")))
    if op == "expire_stale": return json.loads(await ml.cama_expire_stale())
    if op == "set_review_after":                           # the paper's TTL: CAMA's own review_after column and its own expiry tool
        return {"updated": _exec("UPDATE memories SET review_after=? WHERE id=? AND status='provisional'", (a["review_after"], int(a["id"])))}
    if op == "query":
        out = json.loads(await rt.cama_query_memories(cama_mcp.QueryInput(query_text=a["text"], top_k=a.get("top_k", 5), current_affect=a.get("affect", {}),
                                                                         include_counterweight=bool(a.get("counterweight", False)), filters=a.get("filters"))))
        keep = ("id", "raw_text", "source_type", "status", "proposed_by", "confidence", "needs_user_confirmation", "context", "score", "rationale")
        return {"results": [{k: m.get(k) for k in keep} for m in out["results"]],
                "counterweights": [{k: m.get(k) for k in keep} for m in out.get("counterweights", [])],
                "used_embeddings": out.get("used_embeddings"), "candidates": out.get("candidates")}
    if op == "dump":
        return {"rows": _rows("SELECT id, raw_text, source_type, status, proposed_by, confidence, needs_user_confirmation, review_after, context, trust_score, trust_reason FROM memories ORDER BY id")}
    if op == "paths":
        return {"db": sorted(TOUCHED["db"]), "write": sorted(TOUCHED["write"]), "blocked": TOUCHED["blocked"], "db_path": os.path.realpath(cama_mcp.DB_PATH), "cama_src": CAMA_SRC}
    if op == "ping": return {"ok": True}
    raise ValueError(f"unknown op {op}")


def main():
    loop = LOOP
    _out.write(json.dumps({"ready": True, "db_path": os.path.realpath(cama_mcp.DB_PATH)}) + "\n"); _out.flush()
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        req = json.loads(line)
        try:
            res = {"ok": True, "result": loop.run_until_complete(handle(req["op"], req.get("args", {})))}
        except Exception as e:   # noqa: BLE001
            res = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        _out.write(json.dumps(res) + "\n"); _out.flush()


if __name__ == "__main__":
    main()
