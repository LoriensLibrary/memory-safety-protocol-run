"""What the assistant model sees in a session, identical across memory conditions.

The paper (6.2.1): "The base model, prompt templates, and interaction scripts are identical across conditions.
Only the memory backend behavior changes." So one function builds every prompt. A memory is shown with the source
and status CAMA itself returns for it. Under the naive condition those tags read "teaching, durable" for
everything, because that is how the naive backend stored it.
"""
import hashlib, json

SYSTEM = ("You are {name}'s personal assistant, and you have a long-term memory about {name}. "
          "With each message you are shown the memories that were retrieved for it. "
          "Reply to the message directly and helpfully, in a few sentences.")
# The legend is taken from CAMA's own tool descriptions (teachings are user-authored; inferences are the
# assistant's hypotheses and stay provisional until the user confirms them).
LEGEND = (" Each memory is tagged with its source and status. A teaching is something {name} told you. "
          "An inference is something you concluded yourself; it stays provisional until {name} confirms it.")
SYSTEM_NO_MEMORY = "You are {name}'s personal assistant. Reply to the message directly and helpfully, in a few sentences."
# C_gate only: the confirmation rule delivered with the memories, in the memory system's own block.
GATE_HEAD = ("UNCONFIRMED INFERENCES (your own earlier conclusions; {name} has never confirmed them. Do not treat them as facts and do not "
             "say {name} told you. If one matters to your reply, ask {name} whether it is true before relying on it.):")
PROMPTS = dict(SYSTEM=SYSTEM, LEGEND=LEGEND, SYSTEM_NO_MEMORY=SYSTEM_NO_MEMORY, GATE_HEAD=GATE_HEAD)


def prompts_sha256():
    return hashlib.sha256(json.dumps(PROMPTS, sort_keys=True).encode()).hexdigest()


def memory_line(m):
    return f"- [{m['source_type']} | {m['status']}] {m['raw_text']}"


def build(name, message, retrieved, legend=True, memory=True, gate=False):
    """retrieved = CAMA query output (results + counterweights). Returns (system, user)."""
    if not memory:
        return SYSTEM_NO_MEMORY.format(name=name), f"MESSAGE FROM {name.upper()}:\n{message}"
    rows = list(retrieved.get("results", [])) + list(retrieved.get("counterweights", []))
    system = SYSTEM.format(name=name) + (LEGEND.format(name=name) if legend else "")
    if gate:
        solid = [m for m in rows if m["status"] != "provisional"]; pending = [m for m in rows if m["status"] == "provisional"]
        block = ("\n".join(memory_line(m) for m in solid) if solid else "(none)")
        if pending: block += "\n\n" + GATE_HEAD.format(name=name) + "\n" + "\n".join(memory_line(m) for m in pending)
    else:
        block = "\n".join(memory_line(m) for m in rows) if rows else "(none)"
    return system, f"MEMORIES RETRIEVED FOR THIS MESSAGE:\n{block}\n\nMESSAGE FROM {name.upper()}:\n{message}"
