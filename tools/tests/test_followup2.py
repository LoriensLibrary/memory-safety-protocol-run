"""Checks for follow-up F5. No network, no spend.   python tools/tests/test_followup2.py"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import items, followup2 as f2   # noqa: E402

RESULTS = []


def check(name):
    def deco(fn):
        try:
            fn(); RESULTS.append((name, True, ""))
        except Exception as e:   # noqa: BLE001
            RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        return fn
    return deco


ALL = f2.all_items()


@check("V1 150 items, 30 per type, unique ids, none shared with the held-out or the first follow-up seeds")
def _():
    assert len(ALL) == 150 and len({it["tid"] for it in ALL}) == 150
    import collections
    assert set(collections.Counter(it["variant"] for it in ALL).values()) == {30}
    held = {items.make_item(v, i, 2026111501)["question"] + str(items.make_item(v, i, 2026111501)["truth"]) for v in f2.TYPES for i in range(30)}
    assert not any(it["question"] + str(it["truth"]) in held for it in ALL)


@check("V2 the user text is identical across the four record conditions; only the system prompt differs")
def _():
    for it in ALL:
        users = {c: f2.request(it, c)[1] for c in f2.CONDITIONS}
        assert len({users[c] for c in ("described", "unexplained", "reworded", "caveat")}) == 1
        assert "PLATFORM PROVENANCE" in users["described"] and "PLATFORM PROVENANCE" not in users["none"].replace(next((s["text"] for s in it["sources"] if s["role"] == "bad"), ""), "")
        systems = {c: f2.request(it, c)[0] for c in f2.CONDITIONS}
        assert len(set(systems.values())) == 4 and systems["none"] == systems["unexplained"] == items.SYSTEM_BASE


@check("V3 the unexplained condition says nothing about the record; the reworded note shares no sentence with the original; the caveat adds exactly one sentence")
def _():
    it = ALL[0]
    s_un, s_re, s_de, s_ca = (f2.request(it, c)[0] for c in ("unexplained", "reworded", "described", "caveat"))
    for w in ("platform", "provenance", "signature", "issuer", "verified", "retract"):
        assert w not in s_un.lower(), w
    orig = {x.strip() for x in (items.PROV_NOTE + items.NOTE_JSON).split(".") if x.strip()}
    new = {x.strip() for x in f2.REWORDED.split(".") if x.strip()}
    assert not (orig & new)
    for field in ("claimed_issuer", "issuer_verified", "status", "derived_from"): assert field in s_re
    assert s_ca == s_de + f2.CAVEAT and f2.CAVEAT.count(".") == 2
    for w in ("prefer", "ignore", "do not use", "abstain when", "should"):
        assert w not in f2.CAVEAT.lower() and w not in f2.REWORDED.lower(), w


@check("V4 every slot completes and is scored in a dry pass")
def _():
    n = 0
    for it in ALL:
        for c in f2.CONDITIONS:
            r = f2.run_cell(it, c, lambda system, user, _it=it, _c=c: dict(text=f2.canned(_it, _c))); n += 1
            assert r["status"] == "complete" and r["outcome"] in ("correct", "adopted_bad", "abstain"), (it["tid"], c, r)
    assert n == 750


if __name__ == "__main__":
    for name, ok, why in RESULTS:
        print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"\n        {why}"))
    bad = sum(not ok for _, ok, _ in RESULTS)
    print(f"\n{len(RESULTS) - bad}/{len(RESULTS)} passed")
    sys.exit(1 if bad else 0)
