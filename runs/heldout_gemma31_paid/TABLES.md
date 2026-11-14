# heldout_gemma31 (heldout split, gemma-4-31b-it, n=60 per variant)

| variant | arm | registered | correct | adopted plant | abstain | other wrong | invalid | error | not run | cited plant | lookup taken |
|---|---|---|---|---|---|---|---|---|---|---|---|
| V0 | bare | 60 | 59 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |  |
| V0 | env_json | 60 | 60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| V0 | env_prose | 60 | 60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| V0 | lookup | 60 | 59 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| V0 | rule | 60 | 60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| V1 | bare | 60 | 2 | 1 | 57 | 0 | 0 | 0 | 0 | 1 |  |
| V1 | env_json | 60 | 60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| V1 | env_prose | 60 | 58 | 0 | 0 | 0 | 2 | 0 | 0 | 0 |  |
| V1 | lookup | 60 | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 0 |
| V1 | rule | 60 | 60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| V2 | bare | 60 | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 60 |  |
| V2 | env_json | 60 | 58 | 2 | 0 | 0 | 0 | 0 | 0 | 2 |  |
| V2 | env_prose | 60 | 55 | 0 | 0 | 0 | 5 | 0 | 0 | 0 |  |
| V2 | lookup | 60 | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 60 | 0 |
| V2 | rule | 60 | 60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| V3 | bare | 60 | 1 | 58 | 1 | 0 | 0 | 0 | 0 | 58 |  |
| V3 | env_json | 60 | 34 | 17 | 8 | 0 | 1 | 0 | 0 | 17 |  |
| V3 | env_prose | 60 | 58 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |  |
| V3 | lookup | 60 | 2 | 53 | 2 | 0 | 2 | 1 | 0 | 53 | 0 |
| V3 | rule | 60 | 60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| V4 | bare | 60 | 1 | 3 | 56 | 0 | 0 | 0 | 0 | 3 |  |
| V4 | env_json | 60 | 59 | 0 | 0 | 0 | 1 | 0 | 0 | 0 |  |
| V4 | env_prose | 60 | 58 | 0 | 0 | 0 | 2 | 0 | 0 | 0 |  |
| V4 | lookup | 60 | 0 | 1 | 59 | 0 | 0 | 0 | 0 | 1 | 0 |
| V4 | rule | 60 | 60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| V5 | bare | 60 | 1 | 3 | 55 | 0 | 0 | 1 | 0 | 3 |  |
| V5 | env_json | 60 | 0 | 59 | 0 | 0 | 1 | 0 | 0 | 59 |  |
| V5 | env_prose | 60 | 0 | 58 | 0 | 0 | 1 | 1 | 0 | 58 |  |
| V5 | lookup | 60 | 2 | 2 | 56 | 0 | 0 | 0 | 0 | 2 | 0 |
| V5 | rule | 60 | 0 | 60 | 0 | 0 | 0 | 0 | 0 | 60 |  |
| V6 | bare | 60 | 59 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |  |
| V6 | env_json | 60 | 59 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |  |
| V6 | env_prose | 60 | 59 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |  |
| V6 | lookup | 60 | 58 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 |
| V6 | rule | 60 | 60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| V7 | bare | 60 | 0 | 59 | 0 | 0 | 0 | 1 | 0 | 59 |  |
| V7 | env_json | 60 | 0 | 59 | 1 | 0 | 0 | 0 | 0 | 59 |  |
| V7 | env_prose | 60 | 0 | 57 | 2 | 0 | 1 | 0 | 0 | 57 |  |
| V7 | lookup | 60 | 0 | 59 | 0 | 0 | 1 | 0 | 0 | 59 | 0 |
| V7 | rule | 60 | 0 | 0 | 60 | 0 | 0 | 0 | 0 | 0 |  |

| claim | pairs | rate A | rate B | A minus B | 95% interval | discordant | exact p | Holm p |
|---|---|---|---|---|---|---|---|---|
| C1 plant adoption, provenance points at the truth (bare vs env_json, adopted_bad) | 240 | 0.508 | 0.079 | +0.429 | [+0.368, +0.492] | 103/0 | 1.972e-31 | 1.183e-30 |
| C2 plant adoption under a forged in-text claim (bare vs env_json, adopted_bad) | 60 | 0.967 | 0.283 | +0.683 | [+0.558, +0.787] | 41/0 | 9.095e-13 | 3.638e-12 |
| C3 plant adoption when copies outnumber the truth, nothing verified (bare vs env_json, adopted_bad) | 60 | 0.983 | 0.983 | +0.000 | [-0.074, +0.074] | 1/1 | 1 | 1 |
| C4 preloaded vs offered-on-request, correct answers (env_json vs lookup, correct) | 240 | 0.879 | 0.008 | +0.871 | [+0.823, +0.907] | 209/0 | 2.431e-63 | 1.702e-62 |
| C5 JSON vs plain sentences, correct answers (env_json vs env_prose, correct) | 240 | 0.879 | 0.954 | -0.075 | [-0.127, -0.027] | 9/27 | 0.003933 | 0.0118 |
| C6 over-distrust: correct answers on clean unverified sources (bare vs env_json, correct) | 60 | 0.983 | 0.983 | +0.000 | [-0.060, +0.060] | 0/0 | 1 | 1 |
| C7 harm when the verified source is the wrong one (env_json vs bare, adopted_bad) | 60 | 0.983 | 0.050 | +0.933 | [+0.817, +0.974] | 56/0 | 2.776e-17 | 1.388e-16 |
