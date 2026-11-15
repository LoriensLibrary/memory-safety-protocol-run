"""Memory backends for the four conditions of the Paper 5 protocol, all running the real CAMA code.

Reinhold (2026), "Memory as Safety Infrastructure", section 6.2:
  A  stateless          no memory
  B  naive persistent   every write stored as a durable teaching, whatever its origin; no confirmation
  C  provenance-aware   writes classified by source; inferences provisional; confirmation required for promotion
  D  full safeguards    C plus counterweight retrieval

The paper gives condition C a time-to-live on unconfirmed inferences. Published CAMA (commit 1e5f1aa) no longer
expires them ("ttl_days removed, inferences no longer expire"). Both are run and named separately:
  C_ttl   provenance-aware as the paper specifies: unconfirmed inferences expire after `ttl_sessions` sessions,
          using CAMA's own review_after column and its own cama_expire_stale tool
  C       provenance-aware as CAMA ships today: unconfirmed inferences stay provisional and retrievable

Each backend owns one CAMA process confined to its own scratch directory (see cama_worker.py).
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CAMA_SRC = os.path.join(ROOT, "_deps", "cama")
CAMA_COMMIT = "1e5f1aadf0f240e8345824d9e265a05135cba231"
HF_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
CONDITIONS = ("A", "B", "C_ttl", "C", "D")
PAST, FUTURE = "2000-01-01T00:00:00+00:00", "2999-01-01T00:00:00+00:00"


def worker_env(scratch):
    home = os.path.join(scratch, "home")
    os.makedirs(home, exist_ok=True)
    env = dict(os.environ)
    env.update(CAMA_DB_PATH=os.path.join(scratch, "memory.db"), USERPROFILE=home, HOME=home, HOMEDRIVE=os.path.splitdrive(home)[0], HOMEPATH=os.path.splitdrive(home)[1],
               APPDATA=os.path.join(home, "AppData", "Roaming"), LOCALAPPDATA=os.path.join(home, "AppData", "Local"),
               HF_HOME=HF_CACHE, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false",
               MEMPROTO_SCRATCH=scratch, MEMPROTO_CAMA_SRC=CAMA_SRC, MEMPROTO_READ_OK=HF_CACHE, PYTHONIOENCODING="utf-8", CAMA_LOG_LEVEL="ERROR")
    for k in ("CAMA_PARTICIPANT_ID", "EMBEDDING_API_KEY", "ADAPTION_API_KEY", "ANTHROPIC_API_KEY"):
        env.pop(k, None)
    return env


class CamaProcess:
    def __init__(self, scratch):
        self.scratch = os.path.realpath(scratch)
        os.makedirs(self.scratch, exist_ok=True)
        self.log = open(os.path.join(self.scratch, "worker.log"), "ab")
        self.p = subprocess.Popen([sys.executable, os.path.join(HERE, "cama_worker.py")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
                                  env=worker_env(self.scratch), cwd=self.scratch, text=True, encoding="utf-8")
        first = self.p.stdout.readline()
        if not first:
            raise RuntimeError(f"CAMA worker failed to start; see {os.path.join(self.scratch, 'worker.log')}")
        ready = json.loads(first)
        if not os.path.realpath(ready["db_path"]).startswith(self.scratch):
            self.close(); raise RuntimeError(f"CAMA opened a database outside the scratch directory: {ready['db_path']}")

    def call(self, op, **args):
        self.p.stdin.write(json.dumps({"op": op, "args": args}) + "\n"); self.p.stdin.flush()
        line = self.p.stdout.readline()
        if not line: raise RuntimeError("CAMA worker died")
        res = json.loads(line)
        if not res["ok"]: raise RuntimeError(res["error"])
        return res["result"]

    def close(self):
        try:
            self.p.stdin.close(); self.p.wait(timeout=20)
        except Exception:   # noqa: BLE001
            self.p.kill()
        self.log.close()


class Memory:
    """One condition's memory. The harness tells it WHO authored each write; the condition decides what that means."""

    def __init__(self, condition, scratch, ttl_sessions=3, top_k=5):
        if condition not in CONDITIONS: raise ValueError(condition)
        self.condition, self.ttl_sessions, self.top_k, self.session = condition, ttl_sessions, top_k, 0
        self.cama = None if condition == "A" else CamaProcess(scratch)
        self.born = {}                                     # memory id -> session index when stored (for the paper's TTL)

    # ---- writes ----
    def write(self, text, author, evidence_quote=None, confidence=0.5):
        """author: 'user' (the person said it) or 'assistant' (the model inferred it) or 'document' (shared content)."""
        if self.cama is None: return None
        if self.condition == "B" or author == "user":
            r = self.cama.call("store_teaching", text=text, evidence_quote=evidence_quote)
        else:
            r = self.cama.call("store_inference", text=text, confidence=confidence, evidence_quotes=[evidence_quote] if evidence_quote else [],
                               context=f"origin:{author}")
            if self.condition == "C_ttl": self.cama.call("set_review_after", id=r["memory_id"], review_after=FUTURE)
        self.born[r["memory_id"]] = self.session
        return r

    def confirm(self, memory_id):
        return None if self.cama is None or self.condition == "B" else self.cama.call("confirm", id=memory_id)

    def reject(self, memory_id, reason=None):
        return None if self.cama is None or self.condition == "B" else self.cama.call("reject", id=memory_id, reason=reason)

    # ---- time ----
    def next_session(self):
        """Advance one session. Under C_ttl, unconfirmed inferences older than ttl_sessions are expired by CAMA's own tool."""
        self.session += 1
        if self.condition == "C_ttl":
            for mid, born in self.born.items():
                if self.session - born >= self.ttl_sessions:
                    self.cama.call("set_review_after", id=mid, review_after=PAST)
            return self.cama.call("expire_stale")
        return None

    # ---- reads ----
    def retrieve(self, query, negative_affect=False):
        if self.cama is None: return {"results": [], "counterweights": []}
        affect = {"valence": -0.8, "arousal": 0.6} if negative_affect else {}
        return self.cama.call("query", text=query, top_k=self.top_k, affect=affect, counterweight=(self.condition == "D"))

    def dump(self):
        return [] if self.cama is None else self.cama.call("dump")["rows"]

    def paths(self):
        return None if self.cama is None else self.cama.call("paths")

    def close(self):
        if self.cama: self.cama.close()
