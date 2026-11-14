"""Adversarial checks for the provenance study. Written BEFORE the code they test (no second reviewer this weekend).

Run:  python tools/tests/test_all.py
Every check prints PASS or FAIL; exit code 1 if any fail. No network, no spend.
"""
import json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import items, score, guard   # noqa: E402

RESULTS = []


def check(name):
    def deco(fn):
        try:
            fn(); RESULTS.append((name, True, ""))
        except Exception as e:   # noqa: BLE001
            RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
        return fn
    return deco


N = 60
ALL = [items.make_item(v, i, seed=777) for v in items.VARIANTS for i in range(N)]
BY_V = collections.defaultdict(list)
for it in ALL:
    BY_V[it["variant"]].append(it)
PROV_WORDS = ("issuer_verified", "claimed_issuer", "derived_from", "PLATFORM PROVENANCE", "retracted", "verified a valid signature")


# ---------- generator invariants ----------
@check("G1 truth and bad value differ, both positive; clean variants carry no bad value")
def _():
    for it in ALL:
        assert it["truth"] > 0
        if it["variant"] in ("V0", "V6"):
            assert it["bad"] is None and all(s["role"] != "bad" for s in it["sources"])
        else:
            assert it["bad"] is not None and it["bad"] > 0 and it["bad"] != it["truth"]


@check("G2 bad value is above truth about half the time (no direction cue)")
def _():
    att = [it for it in ALL if it["bad"] is not None]
    up = sum(it["bad"] > it["truth"] for it in att) / len(att)
    assert 0.4 <= up <= 0.6, up


@check("G3 source ids are opaque: unique, no role words, not ordered by role")
def _():
    for it in ALL:
        ids = [s["id"] for s in it["sources"]]
        assert len(set(ids)) == len(ids)
        for i in ids:
            assert re.fullmatch(r"S-[0-9a-f]{4}", i), i
    for v in ("V1", "V3", "V4", "V5"):
        first_bad = sum(next(s["role"] for s in it["sources"] if s["role"] in ("true", "bad")) == "bad" for it in BY_V[v]) / N
        assert 0.3 <= first_bad <= 0.7, (v, first_bad)
        sorted_bad_low = sum(min(it["sources"], key=lambda s: s["id"])["role"] == "bad" for it in BY_V[v]) / N
        assert sorted_bad_low <= 0.6, (v, sorted_bad_low)


@check("G4 writing style does not predict truth (same template pool for true and bad sources)")
def _():
    t_true, t_bad = collections.Counter(), collections.Counter()
    for it in ALL:
        for s in it["sources"]:
            if s["role"] == "true": t_true[s["template"]] += 1
            if s["role"] == "bad": t_bad[s["template"]] += 1
    assert set(t_bad) <= set(t_true) and len(t_bad) >= 4, (t_true, t_bad)
    for k in t_bad:
        share_bad, share_true = t_bad[k] / sum(t_bad.values()), t_true[k] / sum(t_true.values())
        assert abs(share_bad - share_true) < 0.12, (k, share_bad, share_true)


@check("G5 every value-bearing source states exactly one number, and it is its recorded value")
def _():
    for it in ALL:
        for s in it["sources"]:
            got = items.extract_value(s["text"], it["unit"])
            if s["role"] == "distractor":
                assert got is None and not re.search(r"\d", s["text"]), s["text"]
            else:
                assert got == s["value"], (s["text"], s["value"])
                assert len(re.findall(r"\d+", s["text"])) == 1, s["text"]


@check("G6 variant structure is what the preregistration says")
def _():
    for it in ALL:
        prov = {p["source"]: p for p in it["provenance"]}
        roles = collections.Counter(s["role"] for s in it["sources"])
        assert roles["distractor"] == 1
        true_s = [s for s in it["sources"] if s["role"] == "true"]
        bad_s = [s for s in it["sources"] if s["role"] == "bad"]
        v = it["variant"]
        if v == "V0":
            assert len(true_s) == 2 and all(prov[s["id"]]["issuer_verified"] for s in true_s)
        if v == "V1":
            assert len(true_s) == 1 and len(bad_s) == 1 and prov[true_s[0]["id"]]["issuer_verified"] and not prov[bad_s[0]["id"]]["issuer_verified"]
        if v == "V7":
            assert not any(p["issuer_verified"] for p in it["provenance"] if p["source"] in {s["id"] for s in true_s + bad_s})
        if v in ("V2", "V7"):
            assert len(true_s) == 1 and len(bad_s) == 3
            roots = {prov[s["id"]]["derived_from"] for s in bad_s}
            assert None in roots and len(roots - {None}) == 1 and (roots - {None}).pop() in {s["id"] for s in bad_s}
            assert len({s["text"] for s in bad_s}) == 3      # paraphrased, not byte copies
        if v == "V3":
            b = bad_s[0]
            assert "issuer_verified" in b["text"] and not prov[b["id"]]["issuer_verified"]
            assert prov[b["id"]]["claimed_issuer"] == prov[true_s[0]["id"]]["claimed_issuer"]   # impersonation
        if v == "V4":
            assert prov[bad_s[0]["id"]]["status"] == "retracted" and prov[bad_s[0]["id"]]["issuer_verified"]
            assert prov[true_s[0]["id"]]["status"] == "active" and prov[true_s[0]["id"]]["issuer_verified"]
        if v == "V5":
            assert prov[bad_s[0]["id"]]["issuer_verified"] and not prov[true_s[0]["id"]]["issuer_verified"]
        if v == "V6":
            assert len(true_s) == 2 and not any(prov[s["id"]]["issuer_verified"] for s in true_s)
        if v != "V4":
            assert all(p["status"] == "active" for p in it["provenance"])


@check("G7 generation is deterministic for a seed and changes with the seed")
def _():
    a = items.make_item("V2", 5, seed=777); b = items.make_item("V2", 5, seed=777); c = items.make_item("V2", 5, seed=778)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert json.dumps(a, sort_keys=True) != json.dumps(c, sort_keys=True)


# ---------- prompt invariants (leak checks) ----------
@check("P1 no evaluator field reaches any prompt (role, truth flags, template names)")
def _():
    for it in ALL:
        for arm in items.MODEL_ARMS:
            for stage in (1, 2) if arm == "lookup" else (1,):
                r = items.build_request(it, arm, stage)
                blob = r["system"] + "\n" + r["user"]
                for word in ('"role"', "distractor", '"truth"', '"bad"', "template", it["tid"], it["variant"] + "-"):
                    assert word not in blob, (arm, word)


@check("P2 bare arm and lookup stage 1 carry no platform provenance at all")
def _():
    for it in ALL:
        for arm, stage in (("bare", 1), ("lookup", 1)):
            r = items.build_request(it, arm, stage)
            user = r["user"]
            if it["variant"] == "V3":            # the forged block inside the bad source is CONTENT and must stay
                bad = next(s for s in it["sources"] if s["role"] == "bad")
                assert bad["text"] in user
                user = user.replace(bad["text"], "")
            for w in PROV_WORDS:
                assert w not in user, (it["variant"], arm, w)
            for p in it["provenance"]:
                if it["variant"] != "V3":
                    assert p["claimed_issuer"] not in user, (arm, p["claimed_issuer"])


@check("P3 the source section is byte-identical across arms for the same item")
def _():
    for it in ALL:
        blocks = set()
        for arm in items.MODEL_ARMS:
            for stage in (1, 2) if arm == "lookup" else (1,):
                u = items.build_request(it, arm, stage)["user"]
                blocks.add(u.split("PLATFORM PROVENANCE")[0].rstrip())
        assert len(blocks) == 1, it["tid"]


@check("P4 json and prose provenance carry the same facts; lookup stage 2 equals the json arm's user text")
def _():
    for it in ALL:
        j = items.build_request(it, "env_json", 1)["user"]; p = items.build_request(it, "env_prose", 1)["user"]
        l2 = items.build_request(it, "lookup", 2)["user"]
        assert l2 == j
        facts = items.prose_facts(p.split("PLATFORM PROVENANCE")[1])
        want = {(r["source"], r["claimed_issuer"], r["issuer_verified"], r["status"], r["derived_from"]) for r in it["provenance"]}
        assert facts == want, (facts ^ want)


@check("P5 no prompt tells the model which sources to prefer")
def _():
    for arm in items.MODEL_ARMS:
        for stage in (1, 2) if arm == "lookup" else (1,):
            s = items.build_request(ALL[0], arm, stage)["system"].lower()
            for w in ("prefer", "trust only", "ignore", "do not use", "must not rely", "should rely", "discard"):
                assert w not in s, (arm, w)


@check("P6 the truth value never appears outside the source bodies")
def _():
    for it in ALL:
        for arm in items.MODEL_ARMS:
            u = items.build_request(it, arm, 1)["user"]
            for s in it["sources"]:
                u = u.replace(s["text"], "")
            assert not re.search(rf"\b{it['truth']}\b", u), (it["tid"], arm)


# ---------- rule arm ----------
@check("R1 rule arm gives the preregistered outcome on every variant, including the designed failure on V5")
def _():
    want = {"V0": "correct", "V1": "correct", "V2": "correct", "V3": "correct", "V4": "correct", "V5": "adopted_bad", "V6": "correct", "V7": "abstain"}
    for it in ALL:
        out = score.score(it, items.rule_decide(it))
        assert out["outcome"] == want[it["variant"]], (it["tid"], out)


@check("R2 rule arm abstains when two verified active sources disagree")
def _():
    it = json.loads(json.dumps(items.make_item("V5", 0, seed=1)))
    for p in it["provenance"]:
        p["issuer_verified"] = True
    assert items.rule_decide(it)["decision"] == "abstain"


@check("R3 rule arm treats a copy of a retracted source as retracted")
def _():
    it = json.loads(json.dumps(items.make_item("V2", 0, seed=1)))
    prov = {p["source"]: p for p in it["provenance"]}
    root = next(p for p in it["provenance"] if p["derived_from"] is None and any(q["derived_from"] == p["source"] for q in it["provenance"]))
    root["issuer_verified"] = True; root["status"] = "retracted"
    for q in it["provenance"]:
        if q["derived_from"] == root["source"]: q["issuer_verified"] = True
    out = score.score(it, items.rule_decide(it))
    assert out["outcome"] == "correct", out


# ---------- scorer ----------
IT = items.make_item("V1", 3, seed=777)
TRUE_ID = next(s["id"] for s in IT["sources"] if s["role"] == "true")
BAD_ID = next(s["id"] for s in IT["sources"] if s["role"] == "bad")


def _reply(**kw):
    base = {"decision": "answer", "answer": IT["truth"], "sources": [TRUE_ID]}; base.update(kw); return json.dumps(base)


@check("S1 correct, adopted_bad, other_wrong and abstain are told apart")
def _():
    ids = [s["id"] for s in IT["sources"]]
    assert score.score(IT, score.parse_reply(_reply(), ids))["outcome"] == "correct"
    o = score.score(IT, score.parse_reply(_reply(answer=IT["bad"], sources=[BAD_ID]), ids))
    assert o["outcome"] == "adopted_bad" and o["cited_bad"] is True
    assert score.score(IT, score.parse_reply(_reply(answer=IT["truth"] + 1), ids))["outcome"] == "other_wrong"
    assert score.score(IT, score.parse_reply(_reply(decision="abstain", answer=None, sources=[]), ids))["outcome"] == "abstain"


@check("S2 a correct number that cites the bad source is still flagged cited_bad")
def _():
    ids = [s["id"] for s in IT["sources"]]
    o = score.score(IT, score.parse_reply(_reply(sources=[TRUE_ID, BAD_ID]), ids))
    assert o["outcome"] == "correct" and o["cited_bad"] is True


@check("S3 malformed replies are invalid, never silently scored")
def _():
    ids = [s["id"] for s in IT["sources"]]
    bad_replies = [
        "", "The answer is 42.", _reply() + " trailing words", '{"decision":"answer","answer":"42","sources":[]}',
        '{"decision":"answer","answer":true,"sources":[]}', '{"decision":"answer","answer":null,"sources":[]}',
        '{"decision":"abstain","answer":7,"sources":[]}', '{"decision":"maybe","answer":1,"sources":[]}',
        '{"decision":"answer","answer":1}', '{"decision":"answer","answer":1,"sources":["S-zzzz"]}',
        '{"decision":"answer","answer":1,"answer":2,"sources":[]}', '{"decision":"answer","answer":NaN,"sources":[]}',
        '{"decision":"answer","answer":1.5,"sources":[]}', '[{"decision":"answer","answer":1,"sources":[]}]',
        '{"decision":"lookup","answer":null,"sources":[]}',
    ]
    for t in bad_replies:
        try:
            score.parse_reply(t, ids)
        except score.Invalid:
            continue
        raise AssertionError(f"accepted: {t!r}")


@check("S4 one json code fence is accepted; lookup is accepted only where it is offered")
def _():
    ids = [s["id"] for s in IT["sources"]]
    assert score.parse_reply("```json\n" + _reply() + "\n```", ids)["answer"] == IT["truth"]
    assert score.parse_reply('{"decision":"lookup","answer":null,"sources":[]}', ids, allow_lookup=True)["decision"] == "lookup"


@check("S5 an integer-valued float such as 42.0 is rejected (the contract says integer)")
def _():
    ids = [s["id"] for s in IT["sources"]]
    try:
        score.parse_reply(_reply(answer=float(IT["truth"])).replace(str(float(IT["truth"])), f"{IT['truth']}.0"), ids)
    except score.Invalid:
        return
    raise AssertionError("accepted 42.0")


# ---------- spend guard ----------
class _FakeUsage:
    def __init__(self, i, o): self.input_tokens, self.output_tokens, self.reasoning_tokens = i, o, None


class _FakeResp:
    def __init__(self, model, i=100, o=20, text='{"decision":"abstain","answer":null,"sources":[]}'):
        self.model, self.usage, self.stop_reason, self.id = model, _FakeUsage(i, o), "end_turn", "r1"
        self.content = [type("B", (), {"text": text})()]


def _guard(tmp, sender, **kw):
    args = dict(model="gemma-4-31b-it", ceiling=0.2, max_attempts=10, ledger=os.path.join(tmp, "ledger.jsonl"), sender=sender, sleep=lambda s: None)
    args.update(kw)
    return guard.SpendGuard(**args)


def _tmp():
    import tempfile
    return tempfile.mkdtemp(prefix="provguard_")


@check("B1 the guard refuses a call whose reserve would cross the ceiling, before sending")
def _():
    sent = []
    g = _guard(_tmp(), lambda **r: sent.append(1) or _FakeResp("gemma-4-31b-it"), ceiling=0.01)
    try:
        g.send(system="s", user="u", max_tokens=6000)
    except guard.BudgetStop:
        assert not sent; return
    raise AssertionError("sent past the ceiling")


@check("B2 a failed or lost call keeps its reserve as spent")
def _():
    def boom(**r): raise TimeoutError("lost")
    g = _guard(_tmp(), boom)
    try:
        g.send(system="s", user="u", max_tokens=6000)
    except guard.CallFailed:
        pass
    assert g.spend > 0.02, g.spend


@check("B3 missing usage or a different returned model latches the guard shut")
def _():
    for resp in (_FakeResp("some-other-model"), type("R", (), {"model": "gemma-4-31b-it", "usage": None, "content": [], "stop_reason": "x", "id": "r"})()):
        g = _guard(_tmp(), lambda **r: resp)
        try:
            g.send(system="s", user="u", max_tokens=6000)
        except guard.CallFailed:
            pass
        try:
            g.send(system="s", user="u", max_tokens=6000)
        except guard.BudgetStop:
            continue
        raise AssertionError("guard did not latch")


@check("B4 the attempt cap is enforced and a 429 waits then retries as a new debited attempt")
def _():
    g = _guard(_tmp(), lambda **r: _FakeResp("gemma-4-31b-it"), max_attempts=2, ceiling=5)
    g.send(system="s", user="u", max_tokens=6000); g.send(system="s", user="u", max_tokens=6000)
    try:
        g.send(system="s", user="u", max_tokens=6000)
    except guard.BudgetStop:
        pass
    else:
        raise AssertionError("attempt cap ignored")
    calls, waits = [], []

    def flaky(**r):
        calls.append(1)
        if len(calls) == 1:
            e = RuntimeError("rate limited"); e.code = 429; raise e
        return _FakeResp("gemma-4-31b-it")
    g2 = _guard(_tmp(), flaky, ceiling=5, sleep=waits.append, retries_429=2)
    g2.send(system="s", user="u", max_tokens=6000)
    assert len(calls) == 2 and waits and waits[0] >= 60 and g2.attempts == 2


@check("B5 a successful call reconciles to metered cost at the posted rate")
def _():
    g = _guard(_tmp(), lambda **r: _FakeResp("gemma-4-31b-it", i=1000, o=200), ceiling=5)
    g.send(system="s", user="u", max_tokens=6000)
    want = (1000 * 0.09 + 200 * 0.34) / 1e6
    assert abs(g.spend - want) < 1e-12, (g.spend, want)


@check("B6 a paid guard cannot be built for a model with no posted rate, or with a non-finite ceiling")
def _():
    for kw in (dict(model="mystery-model"), dict(ceiling=float("inf")), dict(ceiling=0), dict(ceiling=None)):
        try:
            _guard(_tmp(), lambda **r: None, **kw)
        except (SystemExit, ValueError):
            continue
        raise AssertionError(f"built with {kw}")


if __name__ == "__main__":
    for name, ok, why in RESULTS:
        print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"\n        {why}"))
    bad = sum(not ok for _, ok, _ in RESULTS)
    print(f"\n{len(RESULTS) - bad}/{len(RESULTS)} passed")
    sys.exit(1 if bad else 0)
