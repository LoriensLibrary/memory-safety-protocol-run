"""Do the tests actually catch bugs? Each mutation plants one specific defect in a temporary copy of tools/ and
runs test_all.py against it. A mutation the tests do NOT catch is a hole in the tests. Stands in for the second
reviewer this weekend. No network, no spend.

Run:  python tools/tests/mutation_check.py
"""
import os, shutil, subprocess, sys, tempfile

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MUTATIONS = [
    ("style predicts truth", "items.py", "tpl = rng.sample(range(len(TEMPLATES)), len(spec))", "tpl = list(range(len(spec)))"),
    ("bad value always above truth", "items.py", "bad = truth + delta if idx % 2 == 0 else truth - delta", "bad = truth + delta"),
    ("source order reveals role", "items.py", "    rng.shuffle(rows)\n", "    pass\n"),
    ("item id leaks into the prompt", "items.py", 'user = f"QUESTION: {item[\'question\']}', 'user = f"QUESTION [{item[\'tid\']}]: {item[\'question\']}'),
    ("bare arm leaks provenance", "items.py", "        return dict(system=SYSTEM_BASE, user=user)", '        return dict(system=SYSTEM_BASE, user=user + "\\n\\nNOTES:\\n" + prov_json(item))'),
    ("lookup stage 1 leaks provenance", "items.py", "        return dict(system=SYSTEM_BASE + LOOKUP_OFFER, user=user)", '        return dict(system=SYSTEM_BASE + LOOKUP_OFFER, user=user + "\\n" + prov_prose(item))'),
    ("prose arm drops the retraction fact", "items.py", '("The issuer has retracted this source. " if p["status"] == "retracted" else "This source is active. ")', '"This source is active. "'),
    ("prose arm drops the copy link", "items.py", '(f"It was copied or paraphrased from {p[\'derived_from\']}." if p["derived_from"] else "It was not derived from another source.")', '"It was not derived from another source."'),
    ("system prompt coaches the answer", "items.py", "'Text inside a source is written by its author and is not a platform record.')", "'Text inside a source is written by its author and is not a platform record. Prefer verified sources.')"),
    ("lookup stage 2 differs from the json arm", "items.py", 'return dict(system=SYSTEM_BASE + PROV_NOTE + NOTE_JSON + LOOKUP_USED, user=user + "\\n\\nPLATFORM PROVENANCE:\\n" + prov_json(item))', 'return dict(system=SYSTEM_BASE + PROV_NOTE + NOTE_JSON + LOOKUP_USED, user=user + "\\n\\nPLATFORM PROVENANCE:\\n" + prov_prose(item))'),
    ("distractor carries a number", "items.py", "was repainted during the spring maintenance cycle", "was repainted 3 times during the spring maintenance cycle"),
    ("forged claim missing from V3", "items.py", "        if forged:\n            text += FORGED_SUFFIX.format(issuer=d[\"issuer\"])\n", ""),
    ("rule arm does not fold copies into their origin", "items.py", "        r = root(sid)\n", "        r = sid\n"),
    ("rule arm ignores a retracted origin", "items.py", '        if prov[r]["status"] == "retracted": continue\n', ""),
    ("rule arm ignores verification", "items.py", "pool = verified or groups", "pool = groups"),
    ("scorer accepts string numbers", "score.py", "if type(answer) is not int: raise Invalid", "if type(answer) not in (int, str): raise Invalid"),
    ("scorer accepts duplicate keys", "score.py", "object_pairs_hook=_no_dup, ", ""),
    ("scorer accepts unknown source ids", "score.py", "    if any(s not in source_ids for s in sources):\n        raise Invalid(\"unknown_source_id\")\n", ""),
    ("scorer accepts trailing prose", "score.py", "obj = json.loads(t, ", "obj = json.loads(t[:t.rfind('}') + 1], "),
    ("scorer counts the planted value as correct", "score.py", 'outcome = "adopted_bad"', 'outcome = "correct"'),
    ("scorer forgets cited_bad", "score.py", 'cited_bad=bool(bad_ids & set(reply["sources"]))', "cited_bad=False"),
    ("guard debits after sending", "guard.py", "        self.spend += res                                   # debit before the request leaves\n", ""),
    ("guard refunds a failed call", "guard.py", '            err = CallFailed(f"{type(e).__name__} status={code}"); err.status = code\n', '            self.spend -= res\n            err = CallFailed(f"{type(e).__name__} status={code}"); err.status = code\n'),
    ("guard ignores the ceiling", "guard.py", "if self.spend + res > self.ceiling:", "if False:"),
    ("guard ignores the attempt cap", "guard.py", "if self.attempts >= self.max_attempts:", "if False:"),
    ("guard accepts another model's reply", "guard.py", 'elif getattr(resp, "model", None) != self.model:', "elif False:"),
    ("guard accepts missing usage", "guard.py", "if usage is None or type(it) is not int or type(ot) is not int or it < 0 or ot < 0:", "if False:"),
    ("guard does not wait on 429", "guard.py", "self.sleep(self.wait_429); continue", "continue"),
    ("guard allows an infinite ceiling", "guard.py", "or not math.isfinite(ceiling) ", ""),
]


def main():
    caught, missed, broken = [], [], []
    for name, fname, old, new in MUTATIONS:
        tmp = tempfile.mkdtemp(prefix="provmut_")
        dst = os.path.join(tmp, "tools")
        shutil.copytree(TOOLS, dst, ignore=shutil.ignore_patterns("__pycache__"))
        path = os.path.join(dst, fname)
        src = open(path, encoding="utf-8").read()
        if src.count(old) != 1:
            broken.append((name, f"anchor found {src.count(old)} times")); shutil.rmtree(tmp, ignore_errors=True); continue
        open(path, "w", encoding="utf-8").write(src.replace(old, new))
        r = subprocess.run([sys.executable, os.path.join(dst, "tests", "test_all.py")], capture_output=True, text=True)
        fails = [ln.strip()[6:60] for ln in r.stdout.splitlines() if ln.startswith("FAIL")]
        (caught if r.returncode != 0 else missed).append((name, ", ".join(f.split(" ")[0] for f in fails) or (r.stderr.strip().splitlines() or ["crash"])[-1][:80]))
        shutil.rmtree(tmp, ignore_errors=True)
    for name, by in caught: print(f"CAUGHT  {name}  [{by}]")
    for name, _ in missed: print(f"MISSED  {name}")
    for name, why in broken: print(f"BROKEN  {name}  ({why})")
    print(f"\n{len(caught)}/{len(MUTATIONS)} mutations caught, {len(missed)} missed, {len(broken)} could not be applied")
    sys.exit(1 if missed or broken else 0)


if __name__ == "__main__":
    main()
