# Follow-up tests, deepseek-v4-flash (not preregistered)

| Test | Cell | Registered | Correct | Adopted plant | Abstained | Other wrong | Invalid | Error | Protocol break | Lookup taken |
|---|---|---|---|---|---|---|---|---|---|---|
| F1 | json|bare | 60 | 0 | 35 | 23 | 0 | 0 | 2 | 0 |  |
| F1 | json|env_json | 60 | 59 | 0 | 0 | 0 | 0 | 1 | 0 |  |
| F1 | json|env_prose | 60 | 59 | 0 | 0 | 0 | 0 | 1 | 0 |  |
| F1 | sentence|bare | 60 | 0 | 29 | 30 | 0 | 0 | 1 | 0 |  |
| F1 | sentence|env_json | 60 | 59 | 0 | 0 | 0 | 0 | 1 | 0 |  |
| F1 | sentence|env_prose | 60 | 60 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| F1 | header|bare | 60 | 1 | 12 | 47 | 0 | 0 | 0 | 0 |  |
| F1 | header|env_json | 60 | 54 | 0 | 5 | 0 | 0 | 1 | 0 |  |
| F1 | header|env_prose | 60 | 59 | 0 | 0 | 0 | 0 | 1 | 0 |  |
| F2 | bare | 60 | 0 | 54 | 5 | 0 | 0 | 1 | 0 |  |
| F2 | env_json | 60 | 0 | 13 | 46 | 0 | 0 | 1 | 0 |  |
| F2 | folded_json | 60 | 0 | 0 | 59 | 0 | 0 | 1 | 0 |  |
| F2 | folded_bare | 60 | 0 | 0 | 60 | 0 | 0 | 0 | 0 |  |
| F3 | env_json | 120 | 117 | 0 | 0 | 0 | 0 | 3 | 0 |  |
| F3 | lookup | 120 | 90 | 28 | 0 | 0 | 0 | 2 | 0 | 90 |
| F3 | required | 120 | 114 | 0 | 0 | 0 | 0 | 4 | 2 | 114 |
| F4 | closed | 48 | 46 | 0 | 0 | 1 | 0 | 1 | 0 |  |
| F4 | bare | 48 | 27 | 0 | 21 | 0 | 0 | 0 | 0 |  |
| F4 | env_json | 48 | 4 | 32 | 10 | 0 | 0 | 2 | 0 |  |
| F4 | env_prose | 48 | 5 | 32 | 11 | 0 | 0 | 0 | 0 |  |

| Comparison | n | A | B | A minus B, points [95%] | Discordant | Exact p |
|---|---|---|---|---|---|---|
| F1 json forgery: JSON record vs sentence record (adopted_bad) | 60 | 0 | 0 | +0.0 [-6.0, +6.0] | 0/0 | 1 |
| F1 sentence forgery: JSON record vs sentence record (adopted_bad) | 60 | 0 | 0 | +0.0 [-6.0, +6.0] | 0/0 | 1 |
| F1 header forgery: JSON record vs sentence record (adopted_bad) | 60 | 0 | 0 | +0.0 [-6.0, +6.0] | 0/0 | 1 |
| F1 JSON record: JSON forgery vs sentence forgery (adopted_bad) | 60 | 0 | 0 | +0.0 [-6.0, +6.0] | 0/0 | 1 |
| F1 sentence record: sentence forgery vs JSON forgery (adopted_bad) | 60 | 0 | 0 | +0.0 [-6.0, +6.0] | 0/0 | 1 |
| F2 copies labeled vs copies removed (JSON record) (adopted_bad) | 60 | 13 | 0 | +21.7 [+13.1, +33.6] | 13/0 | 0.000244 |
| F2 no record: copies present vs removed (adopted_bad) | 60 | 54 | 0 | +90.0 [+78.6, +95.3] | 54/0 | 1.11e-16 |
| F3 record delivered vs required lookup (correct) | 120 | 117 | 114 | +2.5 [-2.9, +8.4] | 6/3 | 0.508 |
| F3 required lookup vs offered lookup (correct) | 120 | 114 | 90 | +20.0 [+11.6, +29.0] | 28/4 | 1.93e-05 |
| F4 JSON record vs no record (adopted_bad) | 48 | 32 | 0 | +66.7 [+52.5, +78.3] | 32/0 | 4.66e-10 |
| F4 JSON record vs no record, facts the model answered correctly with no sources (adopted_bad) | 46 | 32 | 0 | +69.6 [+55.2, +80.9] | 32/0 | 4.66e-10 |

F1 adoption by which source is listed first [adopted, items]:

- json|bare: {"plant first": [18, 30], "true first": [17, 30]}
- json|env_json: {"plant first": [0, 30], "true first": [0, 30]}
- json|env_prose: {"plant first": [0, 30], "true first": [0, 30]}
- sentence|bare: {"plant first": [15, 30], "true first": [14, 30]}
- sentence|env_json: {"plant first": [0, 30], "true first": [0, 30]}
- sentence|env_prose: {"plant first": [0, 30], "true first": [0, 30]}
- header|bare: {"plant first": [7, 30], "true first": [5, 30]}
- header|env_json: {"plant first": [0, 30], "true first": [0, 30]}
- header|env_prose: {"plant first": [0, 30], "true first": [0, 30]}
