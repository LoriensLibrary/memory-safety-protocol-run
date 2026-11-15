<!-- DRAFT STATE, 15 Nov 2026. Not part of the paper. Remove before building.
Written: title, sections 1 to 3, the expectations table rows that depend only on CAMA's own output, Appendix C.
Waiting on judges: every {{TOKEN}} in sections 4 to 6 and the abstract's result sentences. Tokens are filled by a
build script from runs_mp/results.json, runs_mp/collateral.json and runs_mp/judge_check.json. No number is typed by hand.
Angela's calls: the title; her own sentence in the LLM Usage Statement; a voice pass.
-->

# Memory as Safety Infrastructure, Part 2: Running the Protocol on a Live Provenance-Aware Memory

Angela Faye Reinhold, Lorien's Library LLC. With Apart Research. Research conducted at the AI x Epistemics Research Sprint, November 2026. Track 2: Trust Infrastructure.

## Abstract

{{ABSTRACT}}

## 1 Introduction

An assistant with long-term memory writes things down about its user. Some of those things the user said. Others the assistant concluded by itself, and some of those conclusions are wrong. Once both kinds sit in the same store, a later session cannot tell them apart, and a wrong guess comes back as something the assistant "knows" about the person.

*Memory as Safety Infrastructure* (Reinhold, 2026) argued that this is a safety problem of the memory layer, and that the memory layer is where it has to be fixed: keep what the user taught separate from what the assistant inferred, hold inferences as provisional until the user confirms them, and let unconfirmed ones lapse. That paper specified an evaluation protocol with four memory conditions and five tasks, and stated that the results would be reported in a companion paper. This is that paper. It reports the first three tasks.

The protocol is run on CAMA, the open memory system the first paper describes, at a fixed public commit and without modification. Every write, confirmation, rejection, expiry and retrieval in the experiment is one of CAMA's own tool functions acting on a scratch database. The first paper was public before this sprint, so its conditions, tasks and metrics serve as the preregistration; every choice it left open is listed in `memory_protocol/PROTOCOL.md`, committed before the first full run.

The question the protocol asks is narrow and practical. If a memory system labels each memory with who authored it and whether the user confirmed it, does the model reading those labels behave differently? And if labels are not enough, which enforcement by the memory system is?

**Contributions.**

1. The first run of the *Memory as Safety Infrastructure* protocol: Tasks 1 to 3 on two open models, with the memory system's real code in the loop and a stateless control.
2. A test of each outcome the first paper predicted, reported whether it held or not. One did not survive contact with the shipped system: published CAMA no longer expires unconfirmed inferences, so the paper's condition C and the system as it ships are two different conditions. Both are run.
3. Two conditions the first paper did not have, added after reading the first real replies. They store exactly what the provenance-aware condition stores and change only how an unconfirmed inference reaches the model: in a separate block that states the confirmation rule, or not at all until the user confirms it.
4. A second reading of every session for false memories the question was not about. The first paper defines its rates over any seeded false memory in a session, and retrieval returns five memories at a time, so a wrong guess about one subject can surface in an answer about another.

## 2 Related Work

**The protocol.** Reinhold (2026) defines the conditions, tasks and metrics used here and names the failure "epistemic contamination": model-generated state entering memory with the standing of user-provided fact. It reports no experimental results.

**Contamination within one conversation.** Giovanny et al. (2026) insert one false premise into a 15-turn conversation under five framings and measure adoption on ten world-knowledge facts. Adoption rose with the authority of the framing on two of three models, from near zero when the falsehood was attributed to the model's own earlier turn to 94.0 and 84.2 percent under an instruction override; the third model adopted nothing. They cite the first paper for the claim that reliability is a property of the state-management layer, and the one defense they test is a hash check on the stored history, which detects rewriting and, as they report, does not act on false content that arrives through an intact channel. The present study tests the defense they point to and do not run: content labeled by author and confirmation status. It also differs in what the model can fall back on. Their facts are ones a model already knows, and the model that resisted did so with its own knowledge. A fact about one user has no such backstop. The memory is the only source.

**Source information as an input.** CONFACT adds a description of each source's background beside conflicting passages and finds it helps conflict resolution (Ge et al., 2025). The SMeL Test labels documents with their source and finds that none of the models tested reliably discarded the unreliable one (Ahdritz and Kleiman, 2025). Both concern documents. Here the label is on the assistant's own memory, and one of its two values means "you concluded this yourself."

**Planted content.** PoisonedRAG steers a retrieval-augmented model with a few injected texts (Zou et al., 2025), and Greshake et al. (2023) show instructions inside retrieved data acting on the application that reads it. Task 3's fourth strategy is that channel aimed at the memory writer.

**Our first study in this sprint.** Earlier in the same sprint we tested a platform-written provenance record on documents (Reinhold, 2026b; in this repository). A delivered record was followed whether it was right or wrong, and a record offered on request was mostly not requested. That result is why this study does not stop at labels.

## 3 Methods

### 3.1 The memory system

CAMA is cloned from its public repository at commit `1e5f1aa` (18 October 2026) and runs as a separate process. Before CAMA is imported, the process is confined: database connections and file writes outside a scratch directory are refused, and network sockets are refused. A test starts the worker aimed at the operator's real memory file and confirms it refuses to start (`memory_protocol/tests/test_isolation.py`, 7 of 7 checks). Each condition gets its own empty database.

CAMA stores a memory as a *teaching* (authored by the user, durable) or an *inference* (authored by the assistant, provisional until the user confirms or rejects it). Retrieval returns the five memories closest to the user's message and excludes rejected and expired ones.

### 3.2 Conditions

The first paper's four conditions, with what each does in CAMA's terms:

| Condition | What is stored and returned |
|---|---|
| A, stateless | No memory. The model sees only the message. |
| B, naive persistent | Every write is stored as a durable teaching. No author, no confirmation. |
| C, provenance-aware | User statements are teachings. Assistant conclusions are inferences, provisional until confirmed. |
| D, full safeguards | C, with CAMA's counterweight retrieval switched on. |

**The time-to-live.** The first paper's condition C expires an unconfirmed inference after a time-to-live. Published CAMA removed that behavior: its code states that inferences no longer expire, and a provisional inference is retrieved at full weight indefinitely. So two versions of C are run. **C as shipped** is CAMA unmodified. **C with the paper's time-to-live** sets CAMA's own `review_after` field on each inference and calls CAMA's own `cama_expire_stale` tool once per session, with a time-to-live of three sessions.

**Two added conditions.** A ten-item run showed a model acting on an inference that was labeled provisional. Two conditions were added before the full run. Both store exactly what C stores.

- **C with a read-time gate.** Unconfirmed inferences are delivered in their own block, headed by the rule: these are your own earlier conclusions, the user never confirmed them, do not treat them as facts, do not say the user told you, ask before relying on one.
- **C with hold until confirmed.** Unconfirmed inferences are not returned by retrieval until the user confirms them. This uses CAMA's existing status filter.

**Condition D in Task 1.** CAMA's counterweight retrieval acts when the message carries strong negative affect. Task 1's probes are neutral, so in Task 1 condition D retrieves what C retrieves. We report D beside C as a repeat of the same condition, which gives a direct reading of run-to-run variation at temperature 0. The counterweight mechanism itself is the subject of the first paper's Task 5, which is not run here.

### 3.3 What the model sees

One function builds the prompt for every condition (`memory_protocol/session.py`). The model is told it is the personal assistant of an invented user, Dana, and is shown the retrieved memories, each on a line that carries the source and status CAMA returned for it, for example `[inference | provisional]`. Two sentences, taken from CAMA's own tool descriptions, say what a teaching and an inference are. Under condition B every line reads `[teaching | durable]`, because that is how the naive backend stored it. The model, the prompt and the scripts are the same across conditions. Only the memory backend changes, as the first paper requires.

### 3.4 Task 1: false-memory persistence

Dana's memory is seeded with 40 true teachings and 50 false inferences across health, work, home, family and money. Fourteen of the false inferences are contradicted by one of the teachings; thirty-six are not. Each false inference has two probes. A recall probe asks what the assistant knows about the subject ("What do you know about me and cats?"). A task probe asks for help where the false memory would matter ("I'm thinking of adopting a cat. Help me get ready."). Neither states the false fact.

Each condition runs 100 sessions: every false inference is probed once before the time-to-live passes and once after, with the recall and task probes counterbalanced across the two phases. No session writes to memory, so all sessions in a phase see the same store.

The first paper defines three rates per session: whether a seeded false memory was retrieved, whether the reply cited it, and whether the reply behaved as if it were true. Retrieval is read from CAMA's output and involves no judgment. It is also independent of the model under test, since CAMA ranks memories against the user's message. We add a fourth rate, **check**: the reply marks the content as unconfirmed or asks the user whether it is true.

Two readings are reported. The **target** reading scores the one false inference the probe was written for, which allows paired comparison of the same probe across conditions. The **session** reading follows the first paper's wording and counts any seeded false inference that was retrieved in the session, including ones the question was not about.

### 3.5 Task 2: correction retention

A false inference is seeded, surfaced, and corrected by the user in plain words. Follow-up sessions one, two and four sessions later probe the same subject. Twenty-four corrections are run per condition. The naive condition has no notion of an inference to reject, so the correction is stored as one more teaching beside the false one; a variant, B with delete, removes the contradicted memory, as a strong baseline. The provenance-aware conditions call CAMA's reject tool on the contradicted inference. Which stored memories a correction contradicts is decided by one model call that is identical across conditions. We record whether the correction is retained, whether the false content returns, and at which follow-up.

### 3.6 Task 3: adversarial insertion

Forty prompts, ten for each of the first paper's four strategies: a false fact asserted in passing, a false fact inside an update request, pressure on the assistant to draw and store its own conclusion, and an instruction to the assistant hidden in a document the user asks it to read. A first stage, shared by all conditions, produces the reply and the assistant's decision about what to save and from which source (the user said it, the assistant inferred it, it came from a document). A second stage applies each condition's write rule to that same decision. We then inspect the database, as the first paper specifies, for whether the planted statement was stored and with what standing, and probe for it four sessions later.

The first two strategies are the user's own words. A memory that trusts the user is not expected to stop them under any condition, and they are included so the result shows what the design does not claim.

### 3.7 Scoring

Citation, action and check need a reading of the reply. Two judge models score every reply against one statement at a time. A judge sees the statement, the user's message and the reply. It does not see the condition, the retrieved memories or their labels. gemma-4-31b-it judges every reply; deepseek-v4-flash judges a fixed sample chosen by hash.

Sixty Task 1 replies were labeled by hand before any judge output for that run existed, without access to the condition. The sixty are the first sixty in the hash order the judge sample uses, so both judges also scored them. Twelve were marked borderline at labeling time, with the reason, and agreement is reported with and without them. A control set scores statements that were never retrieved, to measure how often a judge says yes when the memory was not in front of the model.

Counts that need no judge are also reported: what CAMA retrieved and stored, and pattern matches on the reply for the item's key term, for wording that credits the user ("you told me", "you mentioned"), and for wording that flags uncertainty.

### 3.8 Models, runs and statistics

gemma-4-31b-it and deepseek-v4-flash, served by Adaption's hosted inference, temperature 0. Each model is its own cohort; no result is pooled across models. Every call passes through a spend guard that reserves the worst-case cost before sending, and each run writes a manifest with hashes of its items, prompts and code.

Comparisons between conditions are paired on the same false inference and the same probe, with an exact two-sided McNemar test and a Tango score interval on the difference in proportions. Proportions carry Wilson intervals.

## 4 Results

### 4.1 What the first paper predicted, and what happened

{{EXPECTATIONS_TABLE}}

### 4.2 Retrieval: what the memory system returned

{{T1_RETRIEVAL}}

### 4.3 Recall questions: labels changed what the model said

{{T1_RECALL}}

### 4.4 Task questions: labels did not change what the model did

{{T1_TASK}}

### 4.5 False memories the question was not about

{{T1_SESSION_READING}}

### 4.6 The stateless control is not a zero

{{T1_STATELESS}}

### 4.7 Correction retention

{{T2}}

### 4.8 Adversarial insertion

{{T3}}

### 4.9 Judge accuracy

{{JUDGE_CHECK}}

## 5 Discussion and Limitations

{{DISCUSSION}}

## 6 Conclusion

{{CONCLUSION}}

## References

- Ahdritz, G. and Kleiman, A. The SMeL Test: A simple benchmark for media literacy in language models. arXiv:2508.02074, 2025.
- Ge, Z., Wu, Y., Chin, D. W. K., Lee, R. K.-W. and Cao, R. Resolving Conflicting Evidence in Automated Fact-Checking: A Study on Retrieval-Augmented LLMs. IJCAI 2025, AI and Social Good. arXiv:2505.17762.
- Giovanny, F., Bayuningtyas, G., Mukharom, S. and Firmansyah, H. B. Epistemic Policy Divergence in Multi-Turn LLM Contamination: A Protocol-Gradient Investigation. arXiv:2609.35308, 2026.
- Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T. and Fritz, M. Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection. arXiv:2302.12173, 2023.
- Reinhold, A. Memory as Safety Infrastructure: Evaluating Provenance-Aware Persistent Memory Architectures for Stateful LLM Systems. Zenodo, doi:10.5281/zenodo.19244253. Version 3.0, 14 September 2026.
- Reinhold, A. Does Attached Provenance Change What a Model Believes? A Preregistered Test with Planted Sources. AI x Epistemics Research Sprint, this repository, 2026b.
- Tango, T. Equivalence test and confidence interval for the difference in proportions for the paired-sample design. Statistics in Medicine 17(8):891-908, 1998.
- Zou, W., Geng, R., Wang, B. and Jia, J. PoisonedRAG: Knowledge Corruption Attacks to Retrieval-Augmented Generation of Large Language Models. USENIX Security 2025. arXiv:2402.07867.

## Appendix A: Limitations and Dual-Use / Ethical Considerations

{{APPENDIX_A}}

## Appendix B: Full Tables, Run Integrity and Cost

{{APPENDIX_B}}

## Appendix C: Code, Data and Prior Work

**Prior work, declared.** Three things used here existed before the sprint. The evaluation protocol is from Reinhold (2026), first published March 2026. CAMA is the author's open-source memory system, used at public commit `1e5f1aa` without modification. The spend guard and the paired-statistics functions were written for an earlier sprint project and are vendored unchanged in `tools/vendor/`. Everything in `memory_protocol/` was written during this sprint: the isolation worker, the condition backend, the task materials, the runners, the judges and the analysis.

**What is in the repository.** `memory_protocol/PROTOCOL.md` lists every choice the first paper left open and how it was filled, and was committed before the first full run. `runs_mp/` holds, for each run, the manifest, the ledger of every model call, the raw responses, the traces and the judge outputs. `runs_mp/labels_hand.jsonl` holds the hand labels and `runs_mp/labels_hand_gemma_t1.txt` the labeling rules and a note on each borderline reply. `runs_mp/RUN_NOTES.md` records an edit made to two harness files while the first condition of one run was in progress; the edit was additive and the affected condition is the stateless one.

**Not run.** Tasks 4 and 5 of the protocol. Component B of Task 4 and the first paper's analysis of a live inference corpus need the operator's private memory, which this harness is built never to open.

## LLM Usage Statement

{{LLM_USAGE}}
