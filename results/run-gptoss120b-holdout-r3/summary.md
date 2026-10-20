# nl2sql-bench holdout report (live run, all systems in this run dir)

## Held-out set (15 new questions)

Source: `bench/questions_holdout.yaml`. Models/prompts/MDL **unchanged** (not tuned to these questions). 15 q × 3 runs each for `router`, `cube_v2`, `wrenai_mdl_noreason`, `dbgpt`, `mnemiq`, `mnemiq_failopen`, `mnemiq_verified`.
Results: `results/run-gptoss120b-holdout-r3/`. Chart: `results/holdout_summary.png`.

| System | EX exact | EX relaxed | wrong | exec err | tool err | timeout | unsupported | declined | p50 s | p95 s | avg prompt tok | avg LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Router (cube_v2 → Wren noreason) | 39/45 (87%) | 39/45 (87%) | 6 | 0 | 0 | 0 | 0 | 0 | 3.54 | 7.77 | 11,327 | 1.9 |
| cube_v2 | 25/45 (56%) | 25/45 (56%) | 7 | 1 | 0 | 1 | 11 | 0 | 1.92 | 5.26 | 3,436 | 1.2 |
| WrenAI + semantic, no reasoning | 42/45 (93%) | 42/45 (93%) | 3 | 0 | 0 | 0 | 0 | 0 | 4.06 | 6.89 | 20,811 | 2.0 |
| DB-GPT 0.8.2 | 39/45 (87%) | 39/45 (87%) | 6 | 0 | 0 | 0 | 0 | 0 | 2.61 | 4.32 | 1,693 | 1.0 |
| mnemiq a453b05 (defaults) | 5/45 (11%) | 5/45 (11%) | 0 | 0 | 40 | 0 | 0 | 0 | 3.33 | 5.40 | 4,830 | 2.2 |
| mnemiq a453b05, judge fail-open variant | 44/45 (98%) | 44/45 (98%) | 1 | 0 | 0 | 0 | 0 | 0 | 4.10 | 7.41 | 5,237 | 3.1 |
| mnemiq a453b05, judge 1200-token variant (fail-closed) | 39/45 (87%) | 39/45 (87%) | 2 | 0 | 0 | 0 | 0 | 4 | 5.13 | 9.79 | 5,250 | 3.0 |

### Router fallback / silent-wrong (holdout)

- Fallback rate: **17/45 (38%)**
- Triggers: cube_error=1, cube_unsupported=16
- Cube-answered path: EX 22/28 (79%), p50/p95 2.40/5.86 s
- Fallback path: EX 17/17 (100%), p50/p95 5.28/10.53 s
- Silent-wrong (Cube answered, no fallback, not EX): 6 — ho12@r1, ho12@r2, ho14@r2, ho04@r3, ho12@r3, ho14@r3
- Fell back but Wren still wrong: 0 — none

### DB-GPT 0.8.2: non-exact attempts (holdout)

| run | id | status | reason / error |
|---|---|---|---|
| 1 | ho12 | wrong_result | row count 50 != gold 110 |
| 1 | ho14 | wrong_result | no predicted column matches gold column 0 |
| 2 | ho12 | wrong_result | row count 50 != gold 110 |
| 2 | ho14 | wrong_result | no predicted column matches gold column 0 |
| 3 | ho12 | wrong_result | row count 50 != gold 110 |
| 3 | ho14 | wrong_result | no predicted column matches gold column 0 |

### mnemiq a453b05 (defaults): non-exact attempts (holdout)

| run | id | status | reason / error |
|---|---|---|---|
| 1 | ho03 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho04 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho05 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho06 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho07 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho09 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho10 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho11 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho12 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho13 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho14 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho15 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho01 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho02 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho03 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho04 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho05 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho06 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho07 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho09 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho10 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho11 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho12 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho13 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho14 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho15 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho01 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho02 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho03 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho04 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho05 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho06 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho07 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho08 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho09 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho10 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho11 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho12 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho13 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho14 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |

### mnemiq a453b05, judge fail-open variant: non-exact attempts (holdout)

| run | id | status | reason / error |
|---|---|---|---|
| 1 | ho14 | wrong_result | no predicted column matches gold column 0 |

### mnemiq a453b05, judge 1200-token variant (fail-closed): non-exact attempts (holdout)

| run | id | status | reason / error |
|---|---|---|---|
| 1 | ho13 | declined | declined: verification: The result may not correctly answer the question. |
| 1 | ho14 | declined | declined: verification: The result may not correctly answer the question. |
| 2 | ho14 | wrong_result | no predicted column matches gold column 0 |
| 3 | ho10 | declined | declined: verification: The result may not correctly answer the question. |
| 3 | ho13 | declined | declined: verification: The result may not correctly answer the question. |
| 3 | ho14 | wrong_result | no predicted column matches gold column 0 |

### Per-question statuses (holdout)

| id | diff | question | Router (cube_v2 → Wren noreason) | cube_v2 | WrenAI + semantic, no reasoning | DB-GPT 0.8.2 | mnemiq a453b05 (defaults) | mnemiq a453b05, judge fail-open variant | mnemiq a453b05, judge 1200-token variant (fail-closed) |
|---|---|---|---|---|---|---|---|---|---|
| ho01 | easy | How many distinct media types are there? | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho02 | easy | How many customers have a fax number recorded? | ✅ ✅ ✅ | ⛔ ⛔ ⛔ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho03 | easy | How many tracks are larger than 15 megabytes (bytes > 15 * 1 | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho04 | easy | How many invoices have a billing address that contains the w | ✅ ✅ ❌ | ❌ ❌ ❌ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho05 | medium | What is the average track file size in bytes for each media  | ✅ ✅ ✅ | ✅ ⛔ ⛔ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho06 | medium | How many playlists contain tracks from at least 10 different | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho07 | medium | List employees born in the 1970s. Return first name, last na | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho08 | medium | How many customers have a phone number that starts with '+55 | ✅ ✅ ✅ | ⛔ ⛔ ⛔ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho09 | medium | What percentage of total sales revenue (unit price times qua | ✅ ✅ ✅ | ✅ ❌ ❌ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho10 | hard | For each day of the week in 2024, how many invoices were iss | ✅ ✅ ✅ | ✅ ✅ ⏱️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ 🚫 |
| ho11 | hard | For each support representative, which customer has the high | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho12 | hard | Which artists have never had any track appear on an invoice  | ❌ ❌ ❌ | ❌ 💥 ❌ | ✅ ✅ ✅ | ❌ ❌ ❌ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho13 | hard | For each quarter of 2024, show the total invoice revenue and | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | 🚫 ✅ 🚫 |
| ho14 | hard | Which ISO week numbers of 2023 had the highest invoice reven | ✅ ❌ ❌ | ✅ ✅ ✅ | ❌ ❌ ❌ | ❌ ❌ ❌ | ⚠️ ⚠️ ⚠️ | ❌ ✅ ✅ | 🚫 ❌ ❌ |
| ho15 | hard | How many distinct billing postal codes appear on invoices bi | ✅ ✅ ✅ | ⛔ ⛔ ⛔ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |

Legend: ✅ exact, 🟡 extra columns, ❌ wrong, 💥 exec error, ⚠️ tool/API error, ⏱️ timeout, ⛔ unsupported (Cube), 🚫 declined (mnemiq deferral).
