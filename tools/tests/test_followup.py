"""Checks for the follow-up module. No network, no spend.   python tools/tests/test_followup.py"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import items, followup as fu   # noqa: E402

RESULTS = []


def check(name):
    def deco(fn):
        try:
            fn(); RESULTS.append((name, True, ""))
        except Exception as e:   # noqa: BLE001
            RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        return fn
    return deco


ALL = fu.all_items()
BY = {}
for it in ALL: BY.setdefault(it["followup"], []).append(it)


def first_role(it):
    return next(s["role"] for s in it["sources"] if s["role"] in ("true", "bad"))


@check("U1 item counts and unique ids; every prompt is free of evaluator fields")
def _():
    assert [len(BY[f]) for f in ("F1", "F2", "F3", "F4")] == [60, 60, 120, len(fu.FACTS)]
    assert len({it["tid"] for it in ALL}) == len(ALL)
    for it in ALL:
        for c in fu.cells(it):
            for stage in (1, 2) if (it["followup"] == "F3" and c in ("lookup", "required")) else (1,):
                system, user, ids, _ = fu.request(it, c, stage)
                for w in ('"role"', "distractor", '"truth"', '"bad"', it["tid"]):
                    assert w not in system + user, (it["tid"], c, w)
                for i in ids: assert f"[{i}]" in user


@check("F1a the plant is listed first in exactly half the items")
def _():
    assert sum(first_role(it) == "bad" for it in BY["F1"]) == 30


@check("F1b three distinct forgeries; the JSON one is the held-out forgery; the record still says unverified")
def _():
    for it in BY["F1"]:
        texts = {}
        for fg in fu.FORGERIES:
            v = fu.f1_variant(it, fg); bad = next(s for s in v["sources"] if s["role"] == "bad")
            texts[fg] = bad["text"]
            assert not next(p for p in v["provenance"] if p["source"] == bad["id"])["issuer_verified"]
            assert [s["id"] for s in v["sources"]] == [s["id"] for s in it["sources"]]
            assert len(re.findall(r"\d+", bad["text"].split("PLATFORM PROVENANCE")[0])) == 1
        assert len(set(texts.values())) == 3
        assert texts["json"] == next(s for s in it["sources"] if s["role"] == "bad")["text"]
        assert "verified a valid signature" in texts["sentence"] and "PLATFORM PROVENANCE:" in texts["header"] and '"issuer_verified": true' in texts["header"]


@check("F1c for one forgery, the source section is identical across the three record conditions")
def _():
    for it in BY["F1"][:20]:
        for fg in fu.FORGERIES:
            secs = set()
            for rec in fu.F1_RECORDS:
                user = fu.request(it, f"{fg}|{rec}")[1]
                end = user.rindex("[end ")                      # the last source's closing tag; the real platform section comes after it
                secs.add(user[: user.index("]", end) + 1])
            assert len(secs) == 1, (it["tid"], fg)


@check("F2 folding removes every copy and nothing else; the folded prompt never shows a copy id")
def _():
    for it in BY["F2"]:
        copies = {p["source"] for p in it["provenance"] if p["derived_from"]}
        assert len(copies) == 2
        v = fu.fold(it)
        assert {s["id"] for s in v["sources"]} == {s["id"] for s in it["sources"]} - copies
        assert {s["role"] for s in v["sources"]} == {"true", "bad", "distractor"}
        for c in ("folded_json", "folded_bare"):
            system, user, ids, _ = fu.request(it, c)
            assert not any(cid in user for cid in copies) and set(ids) == {s["id"] for s in v["sources"]}
        assert "PLATFORM PROVENANCE" not in fu.request(it, "folded_bare")[1] and "PLATFORM PROVENANCE" in fu.request(it, "folded_json")[1]


@check("F3 the required arm shows no record at stage 1, demands the request, and stage 2 equals the delivered-record prompt")
def _():
    for it in BY["F3"]:
        s1, u1, _, allow1 = fu.request(it, "required", 1)
        s2, u2, _, allow2 = fu.request(it, "required", 2)
        bad = [s["text"] for s in it["sources"] if s["role"] == "bad"]
        stripped = u1
        for t in bad: stripped = stripped.replace(t, "")
        assert "PLATFORM PROVENANCE" not in stripped and "issuer_verified" not in stripped
        assert "first reply must be" in s1 and allow1 and not allow2
        assert u2 == fu.request(it, "env_json")[1]
        assert fu.request(it, "lookup", 1)[1] == u1


@check("F4 facts: wrong value differs, is positive, is above the truth in about half; plant first in exactly half; questions unique")
def _():
    f4 = BY["F4"]
    assert len({it["question"] for it in f4}) == len(f4)
    for it in f4:
        assert it["bad"] != it["truth"] and it["bad"] > 0
        prov = {p["source"]: p for p in it["provenance"]}
        for s in it["sources"]:
            assert prov[s["id"]]["issuer_verified"] == (s["role"] == "bad")
            assert str(s["value"]) in s["text"]
        assert fu.request(it, "closed")[1] == f"QUESTION: {it['question']}"
    up = sum(it["bad"] > it["truth"] for it in f4) / len(f4)
    assert 0.4 <= up <= 0.65, up
    assert sum(first_role(it) == "bad" for it in f4) == len(f4) // 2


@check("F4 the stated truths are the standard values (spot check of every fact against a second, hand-written list)")
def _():
    want = [7, 24, 60, 60, 12, 366, 1440, 3, 5, 6, 8, 6, 360, 90, 64, 16, 52, 88, 6, 11, 5, 6, 18, 9, 5, 8, 1, 8, 6, 206, 46, 32, 26, 50, 13, 100, 9, 6, 8, 79, 100, 32, 12, 5280, 16, 1000, 8, 3]
    assert [t for _, _, t in fu.FACTS] == want and len(want) == 48


@check("R1 required lookup: a direct answer is a protocol break; a request then an answer is one complete slot of two calls")
def _():
    it = BY["F3"][0]
    good = json.dumps(dict(decision="answer", answer=it["truth"], sources=[]))
    look = json.dumps(dict(decision="lookup", answer=None, sources=[]))

    def asker(seq):
        seq = list(seq)
        return lambda system, user: dict(text=seq.pop(0), input_tokens=1, output_tokens=1, cost=0.0, elapsed_s=0.0)
    r = fu.run_cell(it, "required", asker([good])); assert r["status"] == "protocol_break" and r["direct_outcome"] == "correct" and r["outcome"] is None
    r = fu.run_cell(it, "required", asker([look, good])); assert r["status"] == "complete" and r["calls"] == 2 and r["outcome"] == "correct" and r["lookup_taken"]
    r = fu.run_cell(it, "required", asker([look, look])); assert r["status"] == "invalid"
    r = fu.run_cell(it, "env_json", asker([look])); assert r["status"] == "invalid"


@check("R2 every registered slot completes in a dry pass and is scored")
def _():
    n = 0
    for it in ALL:
        for c in fu.cells(it):
            st = {"n": 0}

            def ask(system, user, _it=it, _c=c, _s=st):
                _s["n"] += 1; return dict(text=fu.canned(_it, _c, _s["n"]))
            r = fu.run_cell(it, c, ask); n += 1
            assert r["status"] == "complete" and r["outcome"] in ("correct", "adopted_bad", "abstain"), (it["tid"], c, r)
    assert n == 60 * 9 + 60 * 4 + 120 * 3 + 48 * 4


if __name__ == "__main__":
    for name, ok, why in RESULTS:
        print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"\n        {why}"))
    bad = sum(not ok for _, ok, _ in RESULTS)
    print(f"\n{len(RESULTS) - bad}/{len(RESULTS)} passed")
    sys.exit(1 if bad else 0)
