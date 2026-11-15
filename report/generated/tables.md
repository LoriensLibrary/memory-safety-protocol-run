## gemma-4-31b-it

Registered 2,400 slots; complete 2,370; invalid 21; transport error 9; not run 0. Provider attempts 1,922. Metered 0.0961 credits; reserves kept for failed attempts 0.2759; counted against the cap 0.372.

| Item type | Arm | Correct | Adopted plant | Abstained | Other wrong | Invalid | Error | Lookup taken |
|---|---|---|---|---|---|---|---|---|
| clean, verified | no record | 59 | 0 | 0 | 0 | 1 | 0 |  |
| clean, verified | JSON record | 60 | 0 | 0 | 0 | 0 | 0 |  |
| clean, verified | sentence record | 60 | 0 | 0 | 0 | 0 | 0 |  |
| clean, verified | record on request | 59 | 0 | 0 | 0 | 1 | 0 | 0 |
| clean, verified | fixed rule | 60 | 0 | 0 | 0 | 0 | 0 |  |
| single plant | no record | 2 | 1 | 57 | 0 | 0 | 0 |  |
| single plant | JSON record | 60 | 0 | 0 | 0 | 0 | 0 |  |
| single plant | sentence record | 58 | 0 | 0 | 0 | 2 | 0 |  |
| single plant | record on request | 0 | 0 | 60 | 0 | 0 | 0 | 0 |
| single plant | fixed rule | 60 | 0 | 0 | 0 | 0 | 0 |  |
| copied plant | no record | 0 | 60 | 0 | 0 | 0 | 0 |  |
| copied plant | JSON record | 58 | 2 | 0 | 0 | 0 | 0 |  |
| copied plant | sentence record | 55 | 0 | 0 | 0 | 5 | 0 |  |
| copied plant | record on request | 0 | 60 | 0 | 0 | 0 | 0 | 0 |
| copied plant | fixed rule | 60 | 0 | 0 | 0 | 0 | 0 |  |
| forged claim | no record | 1 | 58 | 1 | 0 | 0 | 0 |  |
| forged claim | JSON record | 34 | 17 | 8 | 0 | 1 | 0 |  |
| forged claim | sentence record | 58 | 0 | 0 | 0 | 1 | 1 |  |
| forged claim | record on request | 2 | 53 | 2 | 0 | 2 | 1 | 0 |
| forged claim | fixed rule | 60 | 0 | 0 | 0 | 0 | 0 |  |
| retraction | no record | 1 | 3 | 56 | 0 | 0 | 0 |  |
| retraction | JSON record | 59 | 0 | 0 | 0 | 1 | 0 |  |
| retraction | sentence record | 58 | 0 | 0 | 0 | 2 | 0 |  |
| retraction | record on request | 0 | 1 | 59 | 0 | 0 | 0 | 0 |
| retraction | fixed rule | 60 | 0 | 0 | 0 | 0 | 0 |  |
| verified but wrong | no record | 1 | 3 | 55 | 0 | 0 | 1 |  |
| verified but wrong | JSON record | 0 | 59 | 0 | 0 | 1 | 0 |  |
| verified but wrong | sentence record | 0 | 58 | 0 | 0 | 1 | 1 |  |
| verified but wrong | record on request | 2 | 2 | 56 | 0 | 0 | 0 | 0 |
| verified but wrong | fixed rule | 0 | 60 | 0 | 0 | 0 | 0 |  |
| clean, unverified | no record | 59 | 0 | 0 | 0 | 0 | 1 |  |
| clean, unverified | JSON record | 59 | 0 | 0 | 0 | 0 | 1 |  |
| clean, unverified | sentence record | 59 | 0 | 0 | 0 | 0 | 1 |  |
| clean, unverified | record on request | 58 | 0 | 0 | 0 | 1 | 1 | 0 |
| clean, unverified | fixed rule | 60 | 0 | 0 | 0 | 0 | 0 |  |
| copies, none verified | no record | 0 | 59 | 0 | 0 | 0 | 1 |  |
| copies, none verified | JSON record | 0 | 59 | 1 | 0 | 0 | 0 |  |
| copies, none verified | sentence record | 0 | 57 | 2 | 0 | 1 | 0 |  |
| copies, none verified | record on request | 0 | 59 | 0 | 0 | 1 | 0 | 0 |
| copies, none verified | fixed rule | 0 | 0 | 60 | 0 | 0 | 0 |  |

| Claim | Items | Endpoint | A | B | A minus B, points [95% interval] | Discordant pairs | Holm p |
|---|---|---|---|---|---|---|---|
| C1 plant adoption, provenance points at the truth | 240 | adopted plant | no record 122/240 | JSON record 19/240 | +42.9 [+36.8, +49.2] | 103/0 | 1.18e-30 |
| C2 plant adoption under a forged in-text claim | 60 | adopted plant | no record 58/60 | JSON record 17/60 | +68.3 [+55.8, +78.7] | 41/0 | 3.64e-12 |
| C3 plant adoption when copies outnumber the truth, nothing verified | 60 | adopted plant | no record 59/60 | JSON record 59/60 | +0.0 [-7.4, +7.4] | 1/1 | 1 |
| C4 preloaded vs offered-on-request, correct answers | 240 | correct | JSON record 211/240 | record on request 2/240 | +87.1 [+82.2, +90.8] | 209/0 | 1.7e-62 |
| C5 JSON vs plain sentences, correct answers | 240 | correct | JSON record 211/240 | sentence record 229/240 | -7.5 [-12.7, -2.7] | 9/27 | 0.0118 |
| C6 over-distrust: correct answers on clean unverified sources | 60 | correct | no record 59/60 | JSON record 59/60 | +0.0 [-6.0, +6.0] | 0/0 | 1 |
| C7 harm when the verified source is the wrong one | 60 | adopted plant | JSON record 59/60 | no record 3/60 | +93.3 [+81.7, +97.4] | 56/0 | 1.39e-16 |

Tokens per call by arm: {"env_json": {"input_per_call": 556, "output_per_call": 34, "calls_per_slot": 1.0}, "lookup": {"input_per_call": 379, "output_per_call": 31, "calls_per_slot": 1.0}, "env_prose": {"input_per_call": 530, "output_per_call": 34, "calls_per_slot": 1.0}, "bare": {"input_per_call": 278, "output_per_call": 32, "calls_per_slot": 1.0}}

Forged-claim adoption with the JSON record, by which source is listed first [adopted, items]: {"true source listed first": [5, 37], "plant listed first": [12, 23]}

Post hoc second reading of invalid replies: recovered 21, still unreadable 0, outcomes {"correct": 15, "adopted_bad": 6, "abstain": 0, "other_wrong": 0}.

