# Week 3 — Model selection and the corpus decision

## The four things this week taught

1. Split the fee table into per-band records; 17 → 21
2. The eval couldn't see the fix, because it hardcoded which document to retrieve
3. Adding more retrieved context made the better model worse — qwen went from £150 to
   £120 when handed three records instead of one
4. Accuracy has no noise floor on this stack; latency has one of 10–20%

---

## Measured — candidate models

Nine cases (6 grounded, 3 must-refuse) against the 21-record corpus, temperature 0,
seed 7, run locally through Ollama.

| model | size GB | grounded | refusal | median s | tok/s |
| --- | --- | --- | --- | --- | --- |
| llama3.2:1b | 1.32 | 0/6 | 3/3 | ~1.5 | 6.1 |
| **llama3.2:latest** | **2.02** | **5/6** | **3/3** | **~3.0** | **4.4** |
| qwen2.5:0.5b | 0.40 | 6/6 | 1/3 | ~1.0 | 23.2 |
| qwen2.5:1.5b | 0.99 | 5/6 | 3/3 | ~1.85 | 12.5 |

**Chosen: `llama3.2:latest`.** Tied at 8/9 with `qwen2.5:1.5b`. Both missed the same
case. llama refused; qwen answered £120, which is the U7–U9 fee. When the topic is
money, the model that declines is shippable and the model that guesses is not.
Full argument in `docs/model-recommendation.md`.

`llama3.2:1b` scored 3/3 on refusal by refusing all nine questions, including the six
it was handed the answers to. Kept in the table as a reminder that a single metric can
be gamed.

`qwen2.5:0.5b`'s refusal score reads 0/3 in the tool output and is really 1/3 — the
scorer missed *"not explicitly mentioned in the provided documents"* because the word
*explicitly* broke the substring match.

## Measured — reproducibility

| | |
| --- | --- |
| Identical bench runs | 3 |
| Accuracy variation across runs | **none — every score identical** |
| Latency variation across runs | **10–20%** (llama3.2:1b moved 19%) |

Consequence: a score change is a real change and needs no repeats. A latency claim
smaller than 20% is not a finding, and needs a median of several runs.

## Measured — corpus

| | |
| --- | --- |
| Records | 21 (7 faq · 11 handbook · 3 announcement) |
| Rejected at ingestion | 2 — blank answer, and a body repeating its title |
| Tokens, whole corpus | 1,123 (tiktoken cl100k_base) |
| Tokens, 4 retrieved records | 214 |
| Ratio | 5.2x |
| Week 1 ratio's prediction | 1,083 — low by 3.7% |

The 5.2x is unimpressive because 21 short records fit in one prompt. A real 40-page
handbook is roughly 26,000 tokens and the comparison stops being a rounding error.

## What broke

- **My own ingestion.** The fee table extracted as one unbroken run of text —
  `U7 – U9 £120 £30 x 4 Yes U10 – U12 £150 ...` — with no row boundaries. Two of four
  models reached in and pulled the neighbouring band's price. Fixed by emitting one
  self-contained record per age band, each naming its own band inside its own text.
- **The eval harness was hiding it.** Cases named the document to supply by id. After
  the split, `handbook-s2` held no fees at all, so four models were asked the U11 fee
  while being handed a paragraph about hardship arrangements — and the scores did not
  move. An eval coupled to chunking decisions goes stale the moment chunking changes.
- **The refusal scorer failed three separate times** on honest paraphrases. Substring
  matching on natural language keeps breaking in new ways. Week 6 replaces it with a
  model judge.
- **PowerShell.** `.venv\Scripts\Activate.ps1` from the wrong directory, and without the
  leading `.\` it goes looking for a module rather than a script.

## Still open

- `POST /infer` with a typed schema, and the Gradio tab — not started
- Weekday B (three pipelines, latency and peak memory) — waiting on `pipelines_bench.py`
- The corpus manifest is a dry run. It freezes when real club documents replace Northside.
- License and context window are unfilled in the recommendation

## What I would do differently

_your turn — two or three sentences_

## Next

_what you are watching for in Week 4_
