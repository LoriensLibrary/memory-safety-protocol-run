# Memory as Safety Infrastructure, Part 2: Running the Protocol on a Live Provenance-Aware Memory

Angela Faye Reinhold, Lorien's Library LLC. Built for Apart Research's AI x Epistemics Research Sprint (Nov 13 to 15, 2026), Track 2: Trust Infrastructure.

**The paper: [report/COMPANION.pdf](report/COMPANION.pdf).** It is the companion paper that *Memory as Safety Infrastructure* (Reinhold, 2026) said would report the results of its evaluation protocol. The protocol is run here for the first time, on CAMA, the open memory system that paper describes, with CAMA's real code in the loop.

This repository also holds our first study from the same sprint, on platform-attached provenance records for documents: [report/REPORT.pdf](report/REPORT.pdf). Its README section is further down.

## Prior work, declared

- **The evaluation protocol** (conditions, tasks, metrics) is from Reinhold (2026), *Memory as Safety Infrastructure: Evaluating Provenance-Aware Persistent Memory Architectures for Stateful LLM Systems*, Zenodo, doi:10.5281/zenodo.19244253, first published March 2026. It was public before the sprint and serves as the preregistration. Every choice it left open is listed in [memory_protocol/PROTOCOL.md](memory_protocol/PROTOCOL.md), committed before the first full run.
- **CAMA** is the author's open-source memory system, github.com/LoriensLibrary/cama. It is used unmodified at commit `1e5f1aa` (18 October 2026) and is cloned into `_deps/` at run time; it is not copied into this repository.
- **`tools/vendor/`** holds the hosted-API sender and the paired-statistics functions from an earlier sprint project, unchanged.

Everything else here was written during the sprint.

## What the run found (Task 1, sessions where the reply acted on the targeted false memory)

| Memory condition | gemma-4-31b-it | deepseek-v4-flash |
|---|---|---|
| No memory | 9 of 99 | 6 of 100 |
| Naive memory (everything stored as something the user said) | 74 of 100 | 71 of 100 |
| Provenance labels, CAMA as shipped | 31 of 100 | 25 of 100 |
| Labels plus a read-time gate | 3 of 100 | 2 of 100 |
| Labels plus hold until confirmed | 4 of 100 | 5 of 100 |

- The first paper's main prediction held on both models: separating what the user taught from what the assistant inferred cut how often a wrong guess was treated as fact.
- Labels were weak on task questions (24 and 21 of 50 still acted). Enforcement by the memory system closed that gap.
- The first paper's time-to-live works (1 and 2 of 50 after expiry). Published CAMA no longer has it (15 and 10 of 50).
- After a user's correction, naive memory still retrieved the false memory in 54 of 72 follow-up sessions.

Every count in the paper is filled by `tools/build_companion.py` from `runs_mp/results.json`, `runs_mp/collateral.json` and `runs_mp/judge_check.json`.

## Layout

- `memory_protocol/`: the isolation worker that confines CAMA to a scratch directory, the condition backend, task materials, runners, judges, analysis. `memory_protocol/tests/test_isolation.py` proves no run can open a real memory file.
- `runs_mp/`: for each run, the manifest, the ledger of every model call, raw responses, traces and judge verdicts. Reference labels for the judge check are in `runs_mp/labels_hand.jsonl` (written by a model with the condition hidden, not by a person; the blind samples are there for a human to label).
- `report/COMPANION.src.md` and `tools/build_companion.py`: the paper source and the script that fills it.

## Reproduce the tables

```
python memory_protocol/analysis.py gemma431bit deepseekv4fl
python memory_protocol/collateral.py gemma431bit deepseekv4fl
python memory_protocol/handlabel.py score
python tools/build_companion.py
```

Re-running the experiments needs CAMA cloned into `_deps/cama` at the commit above and an Adaption API key in the environment.

---

## First study from the same sprint: Provenance Study

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
