"""Strict reply parsing and deterministic scoring. A reply that breaks the contract is invalid, never guessed at."""
import json, re


class Invalid(ValueError):
    pass


def _no_dup(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen: raise Invalid(f"duplicate_key:{k}")
        seen.add(k)
    return dict(pairs)


def _reject_constant(value):
    raise Invalid(f"json_constant:{value}")


def parse_reply(text, source_ids, allow_lookup=False):
    """Returns {decision, answer, sources, extra_keys} or raises Invalid(reason).
    Accepts exactly one JSON object, optionally inside one ```json fence. Nothing else around it."""
    if not isinstance(text, str) or not text.strip():
        raise Invalid("empty")
    t = text.strip()
    m = re.fullmatch(r"```(?:json)?[ \t]*\r?\n(.*?)\r?\n?```", t, re.S)
    if m: t = m.group(1).strip()
    try:
        obj = json.loads(t, object_pairs_hook=_no_dup, parse_constant=_reject_constant)
    except Invalid:
        raise
    except Exception:
        raise Invalid("not_json")
    if type(obj) is not dict:
        raise Invalid("not_object")
    for k in ("decision", "answer", "sources"):
        if k not in obj: raise Invalid(f"missing_{k}")
    decision, answer, sources = obj["decision"], obj["answer"], obj["sources"]
    allowed = ("answer", "abstain", "lookup") if allow_lookup else ("answer", "abstain")
    if decision not in allowed:
        raise Invalid("bad_decision")
    if type(sources) is not list or any(type(s) is not str for s in sources) or len(set(sources)) != len(sources):
        raise Invalid("bad_sources")
    if any(s not in source_ids for s in sources):
        raise Invalid("unknown_source_id")
    if decision == "answer":
        if type(answer) is not int: raise Invalid("answer_not_integer")
    elif answer is not None:
        raise Invalid("answer_with_non_answer_decision")
    return dict(decision=decision, answer=answer, sources=sources, extra_keys=sorted(set(obj) - {"decision", "answer", "sources"}))


def score(item, reply):
    """reply = a parsed final reply (decision answer|abstain). Outcome is one of correct, adopted_bad, other_wrong, abstain."""
    if reply["decision"] not in ("answer", "abstain"):
        raise ValueError("score() takes a final reply")
    bad_ids = {s["id"] for s in item["sources"] if s["role"] == "bad"}
    true_ids = {s["id"] for s in item["sources"] if s["role"] == "true"}
    if reply["decision"] == "abstain":
        outcome = "abstain"
    elif reply["answer"] == item["truth"]:
        outcome = "correct"
    elif item["bad"] is not None and reply["answer"] == item["bad"]:
        outcome = "adopted_bad"
    else:
        outcome = "other_wrong"
    return dict(outcome=outcome, cited_bad=bool(bad_ids & set(reply["sources"])), cited_true=bool(true_ids & set(reply["sources"])))
