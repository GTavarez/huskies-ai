# Model judge

141 records · 40 questions · hybrid retrieval, k=5

- answerer: `llama3.2:latest`
- judge: `qwen2.5:1.5b`
- grounded prompt: `v1`
- gate: `off`

| | | |
|---|---|---|
| correct refusals | 9/10 | declined when the corpus has no answer |
| answered, grounded | 10/30 | and the context supports it |
| **invented** | **0** | answered something the context does not say |
| **invented on unanswerable** | **0** | fabricated an answer where the documents have none |
| over-refused | 16 | declined although the answer was retrieved |
| mangled refusals | 1 | meant to refuse, dropped a word from the sentence |

For comparison, the best a retrieval score could do on the first row was **0/10** — on every ranker tried.

## Leaked — answered a question the corpus cannot answer

- **Do boys and girls play on the same teams?** — All Whatcom County Select teams participate in the North Puget Sound League (NPSL), which offers competition at a local level for boys and girls U9 to U19 soccer teams.

## Did you spot-check the judge?

_A 1.5B judge is wrong sometimes. Read ten rows of `out/judge.csv` by hand, say how many the judge got right, and quote that number next to every figure above. A judge you have not audited is the same mistake as an eval you have not audited._
