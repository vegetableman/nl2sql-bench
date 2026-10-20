# Jev prompt variants (offline, same 264 items, same labels)

Labels and judge inputs as in judge_comparison.md (mnemiq's own schema/preview rebuild; ho14 tie and ho12 collation rules). Each variant is JevJudge with `MNEMIQ_JEV_PROMPT=<v>` (mnemiq/patches/jev-judge.patch); pass = noul >= 0.5. **Only 2 of the 132 same-call items (ho13 r1, r3) are wrong, so 'wrong caught' is a 0-2 count and must not drive the choice on its own; the decision metric is correct answers blocked.**

| variant | what changes | same 132 calls: wrong caught / passed | correct blocked | correct passed | all 264: wrong caught / passed | correct blocked | ho13 r1 | ho13 r3 | avg input tok | Jev cost (264 calls) |
|---|---|---|---|---|---|---|---|---|---|---|
| gpt-oss:120b judge (logged) | baseline | 2 / 0 | 3 | 127 | – | – | 0.10 | 0.15 | – | – |
| v1 (original run) | original prompt, 5-row preview (the run committed earlier) | 1 / 1 | 15 | 115 | 1 / 1 | 29 | 0.07 | 0.53 | 2,548 | $0.0283 |
| v1 (repeat) | same prompt, re-scored now (noise control) | 1 / 1 | 16 | 114 | 1 / 1 | 30 | 0.06 | 0.59 | 2,548 | $0.0283 |
| a | SQL-logic instruction + row counts / truncation flag + note, 5-row preview | 1 / 1 | 5 | 125 | 1 / 1 | 9 | 0.18 | 0.68 | 2,648 | $0.0294 |
| b | as a, 50-row sample | 1 / 1 | 5 | 125 | 1 / 1 | 9 | 0.10 | 0.57 | 2,687 | $0.0298 |
| c | as a, full result (<=250 rows; all items fit) | 1 / 1 | 5 | 125 | 1 / 1 | 9 | 0.16 | 0.77 | 2,714 | $0.0301 |

## Best threshold per variant (all 264 items)

Chosen as: fewest wrong passed, then fewest correct blocked, then the highest threshold. With 2 wrong items this is descriptive, not a tuned operating point.

| variant | threshold | wrong caught / passed | correct blocked | at the shipped 0.5: correct blocked |
|---|---|---|---|---|
| v1 (original run) | 0.55 | 2 / 0 | 35 | 29 |
| v1 (repeat) | 0.60 | 2 / 0 | 52 | 30 |
| a | 0.69 | 2 / 0 | 18 | 9 |
| b | 0.62 | 2 / 0 | 10 | 9 |
| c | 0.78 | 2 / 0 | 57 | 9 |

**Jev noise (v1 original vs v1 repeat, identical requests):** mean |delta noul| 0.027, max 0.21, pass/block flips at 0.5: 5 of 264.

| variant | correct answers blocked: 5-row preview was truncated (n=84) | not truncated (n=178) |
|---|---|---|
| v1 (original run) | 24 | 5 |
| v1 (repeat) | 24 | 6 |
| a | 5 | 4 |
| b | 5 | 4 |
| c | 5 | 4 |

## Correct answers still blocked at 0.5, per variant (same 132 calls)

| variant | blocked correct items (id rN, noul) |
|---|---|
| v1 (original run) | e02 r1 (0.25), e08 r1 (0.43), m01 r1 (0.46), h06 r1 (0.38), e02 r2 (0.35), e08 r2 (0.37), m01 r2 (0.37), m06 r2 (0.48), e02 r3 (0.35), e08 r3 (0.36), ho10 r1 (0.30), ho14 r1 (0.21), ho10 r2 (0.29), ho10 r3 (0.30), ho14 r3 (0.30) |
| v1 (repeat) | e02 r1 (0.32), e08 r1 (0.44), m01 r1 (0.42), h06 r1 (0.46), e02 r2 (0.26), e08 r2 (0.40), m01 r2 (0.48), h06 r2 (0.34), e02 r3 (0.37), e08 r3 (0.38), m01 r3 (0.30), ho10 r1 (0.32), ho14 r1 (0.34), ho10 r2 (0.29), ho10 r3 (0.31), ho14 r3 (0.23) |
| a | ho10 r1 (0.41), ho14 r1 (0.42), ho10 r2 (0.35), ho10 r3 (0.39), ho14 r3 (0.16) |
| b | ho10 r1 (0.42), ho14 r1 (0.15), ho10 r2 (0.42), ho10 r3 (0.41), ho14 r3 (0.16) |
| c | ho10 r1 (0.43), ho14 r1 (0.16), ho10 r2 (0.40), ho10 r3 (0.45), ho14 r3 (0.14) |
