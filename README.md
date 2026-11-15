# Provenance Study

Does a platform-attached provenance record change what a model believes when some of its sources are planted?

Built for Apart Research's AI x Epistemics Research Sprint (Nov 13 to 15, 2026), Track 2: Trust Infrastructure. Team: Lorien's Library.

**Status (2026-11-14, evening): held-out run complete for gemma-4-31b-it; deepseek-v4-flash finishing.** The design and the claims are fixed in [PREREGISTRATION.md](PREREGISTRATION.md). Generated tables and the figure are in `report/generated/`.

## Results at a glance (gemma-4-31b-it, 60 items per type)

| Item type | No record | JSON record |
|---|---|---|
| Single plant | abstained 57, adopted the plant 1 | correct 60 |
| Copied plant | adopted the plant 60 | correct 58 |
| Forged "verified" claim in the text | adopted the plant 58 | correct 34, adopted the plant 17 |
| Retraction | abstained 56, adopted the plant 3 | correct 59 |
| Verified source is the wrong one | abstained 55, adopted the plant 3 | adopted the plant 59 |
| Copies outnumber the truth, nothing verified | adopted the plant 59 | adopted the plant 59 |

Offered the record on request, the model asked for it 0 times in 480 items. Full tables: `report/generated/tables.md`.

## What was built this weekend, and what was not

Written during the sprint (2026-11-14 onward):

- `tools/items.py`: item generator, the five arms' prompts, the rule arm
- `tools/score.py`: strict reply parsing and scoring
- `tools/run.py`: freeze, dry run, paid run, resume
- `tools/analyze.py`: tables and the seven preregistered comparisons
- `tools/sensitivity.py`: a second reading of invalid replies, added after the results and labeled as such
- `tools/report_tables.py`: every table and figure the report uses, generated from the traces
- `tools/launch.py`: runs frozen cohorts one after another and resumes them after a crash or a sleep
- `tools/tests/`: 33 checks, plus a mutation check that plants 29 deliberate bugs and confirms the tests catch each one
- `PREREGISTRATION.md`

Pre-existing, from our Swarm Alignment sprint project (github.com/LoriensLibrary/SwarmHive, commit 02ff19b, 2026-11-09):

- `tools/vendor/adaption_send.py`: REST adapter for Adaption's hosted models, copied byte for byte
- `tools/vendor/swarm_analysis.py`: paired score interval, Holm, Wilson and sign test, copied byte for byte
- `tools/guard.py`: the spend-guard contract (reserve and debit before sending, keep the reserve on any failed call, attempt cap, integrity latch) is last weekend's design. The module itself was rewritten this weekend, with pacing and rate-limit waits added.

The research question, the task, the items, the arms and every result here are new.

## Run it

No network and no credits needed for any of these:

```bash
python tools/tests/test_all.py
```

```bash
python tools/tests/test_runner.py
```

```bash
python tools/tests/mutation_check.py
```

```bash
python tools/run.py freeze --name demo --split dev --seed 5 --n 6 --model gemma-4-31b-it --ceiling 1
```

```bash
python tools/run.py run --freeze holdout/demo --mode dry
```

```bash
python tools/analyze.py --run runs/demo_dry --freeze holdout/demo
```

A dry run uses a scripted stand-in reader. Its numbers prove the pipeline, not model behaviour.

A paid run (`--mode paid`) needs an Adaption API key and spends credits up to the ceiling written in the freeze.
