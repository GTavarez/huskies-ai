# Model judge

141 records · 40 questions · hybrid retrieval, k=5

- answerer: `llama3.2:latest`
- judge: `qwen2.5:1.5b`
- grounded prompt: `v1`
- gate: `gemma2:2b`

| | | |
|---|---|---|
| correct refusals | 8/10 | declined when the corpus has no answer |
| answered, grounded | 21/30 | and the context supports it |
| **invented** | **0** | answered something the context does not say |
| **invented on unanswerable** | **0** | fabricated an answer where the documents have none |
| over-refused | 7 | declined although the answer was retrieved |
| mangled refusals | 1 | meant to refuse, dropped a word from the sentence |

For comparison, the best a retrieval score could do on the first row was **0/10** — on every ranker tried.

## The gate

`gemma2:2b` reads the question and the retrieved context and decides COVERED or MISSING before anything is generated. MISSING emits the refusal sentence and never calls the answerer, so a routed-out question has no path to a fabricated answer.

Scored against whether the answer was actually in the retrieved context — not against the label, because MISSING is the correct call on an answerable question the retriever missed.

| | |
|---|---|
| gate correct | 24/40 |
| COVERED when the answer was there | 19/24 |
| MISSING when it was not | 5/16 |

## Leaked — answered a question the corpus cannot answer

- **Do boys and girls play on the same teams?** — All Whatcom County Select teams participate in the North Puget Sound League (NPSL), which offers competition at a local level for boys and girls U9 to U19 soccer teams.
- **When are tryouts held?** — Each age group will have two 75-minute tryout sessions.

## Did you spot-check the judge?

_A 1.5B judge is wrong sometimes. Read ten rows of `out/judge.csv` by hand, say how many the judge got right, and quote that number next to every figure above. A judge you have not audited is the same mistake as an eval you have not audited._
