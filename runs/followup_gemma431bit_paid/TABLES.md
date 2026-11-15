# Follow-up tests, gemma-4-31b-it (not preregistered)

| Test | Cell | Registered | Correct | Adopted plant | Abstained | Other wrong | Invalid | Error | Protocol break | Lookup taken |
|---|---|---|---|---|---|---|---|---|---|---|
| F1 | json|bare | 60 | 0 | 59 | 0 | 0 | 1 | 0 | 0 |  |
| F1 | json|env_json | 60 | 30 | 18 | 9 | 0 | 3 | 0 | 0 |  |
| F1 | json|env_prose | 60 | 56 | 0 | 0 | 0 | 4 | 0 | 0 |  |
| F1 | sentence|bare | 60 | 2 | 44 | 12 | 0 | 2 | 0 | 0 |  |
| F1 | sentence|env_json | 60 | 31 | 9 | 20 | 0 | 0 | 0 | 0 |  |
| F1 | sentence|env_prose | 60 | 57 | 1 | 1 | 0 | 1 | 0 | 0 |  |
| F1 | header|bare | 60 | 4 | 42 | 13 | 0 | 1 | 0 | 0 |  |
| F1 | header|env_json | 60 | 15 | 11 | 33 | 0 | 1 | 0 | 0 |  |
| F1 | header|env_prose | 60 | 59 | 0 | 0 | 0 | 1 | 0 | 0 |  |
| F2 | bare | 60 | 0 | 58 | 0 | 0 | 2 | 0 | 0 |  |
| F2 | env_json | 60 | 0 | 56 | 4 | 0 | 0 | 0 | 0 |  |
| F2 | folded_json | 60 | 0 | 0 | 60 | 0 | 0 | 0 | 0 |  |
| F2 | folded_bare | 60 | 4 | 0 | 54 | 0 | 2 | 0 | 0 |  |
| F3 | env_json | 120 | 99 | 15 | 2 | 0 | 2 | 2 | 0 |  |
| F3 | lookup | 120 | 1 | 57 | 62 | 0 | 0 | 0 | 0 |  |
| F3 | required | 120 | 97 | 10 | 0 | 0 | 0 | 0 | 13 | 107 |
| F4 | closed | 48 | 48 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| F4 | bare | 48 | 26 | 0 | 21 | 0 | 1 | 0 | 0 |  |
| F4 | env_json | 48 | 23 | 21 | 1 | 0 | 3 | 0 | 0 |  |
| F4 | env_prose | 48 | 17 | 27 | 2 | 0 | 2 | 0 | 0 |  |

| Comparison | n | A | B | A minus B, points [95%] | Discordant | Exact p |
|---|---|---|---|---|---|---|
| F1 json forgery: JSON record vs sentence record (adopted_bad) | 60 | 18 | 0 | +30.0 [+19.9, +42.5] | 18/0 | 7.63e-06 |
| F1 sentence forgery: JSON record vs sentence record (adopted_bad) | 60 | 9 | 1 | +13.3 [+6.5, +24.2] | 8/0 | 0.00781 |
| F1 header forgery: JSON record vs sentence record (adopted_bad) | 60 | 11 | 0 | +18.3 [+10.6, +29.9] | 11/0 | 0.000977 |
| F1 JSON record: JSON forgery vs sentence forgery (adopted_bad) | 60 | 18 | 9 | +15.0 [+8.1, +26.1] | 9/0 | 0.00391 |
| F1 sentence record: sentence forgery vs JSON forgery (adopted_bad) | 60 | 1 | 0 | +1.7 [-4.5, +8.9] | 1/0 | 1 |
| F2 copies labeled vs copies removed (JSON record) (adopted_bad) | 60 | 56 | 0 | +93.3 [+81.7, +97.4] | 56/0 | 2.78e-17 |
| F2 no record: copies present vs removed (adopted_bad) | 60 | 58 | 0 | +96.7 [+84.8, +99.1] | 58/0 | 6.94e-18 |
| F3 record delivered vs required lookup (correct) | 120 | 99 | 97 | +1.7 [-6.3, +9.8] | 12/10 | 0.832 |
| F3 required lookup vs offered lookup (correct) | 120 | 97 | 1 | +80.0 [+72.0, +86.2] | 96/0 | 2.52e-29 |
| F4 JSON record vs no record (adopted_bad) | 48 | 21 | 0 | +43.8 [+30.7, +57.7] | 21/0 | 9.54e-07 |
| F4 JSON record vs no record, facts the model answered correctly with no sources (adopted_bad) | 48 | 21 | 0 | +43.8 [+30.7, +57.7] | 21/0 | 9.54e-07 |

F1 adoption by which source is listed first [adopted, items]:

- json|bare: {"plant first": [30, 30], "true first": [29, 30]}
- json|env_json: {"plant first": [14, 30], "true first": [4, 30]}
- json|env_prose: {"plant first": [0, 30], "true first": [0, 30]}
- sentence|bare: {"plant first": [26, 30], "true first": [18, 30]}
- sentence|env_json: {"plant first": [9, 30], "true first": [0, 30]}
- sentence|env_prose: {"plant first": [1, 30], "true first": [0, 30]}
- header|bare: {"plant first": [16, 30], "true first": [26, 30]}
- header|env_json: {"plant first": [10, 30], "true first": [1, 30]}
- header|env_prose: {"plant first": [0, 30], "true first": [0, 30]}
