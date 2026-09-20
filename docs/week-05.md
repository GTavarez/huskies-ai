# Week 5 — Retrieval, and the end of judging by hand

## The finding

Three ranking functions — lexical, semantic, and the two fused — were run over
142 records from four real club handbooks with an identical set of questions.

| ranker | hit@5 | worst refusal leak | weakest genuine hit | separates? |
| --- | --- | --- | --- | --- |
| BM25 | 8/11 (72%) | 18.020 | 6.287 | **no** |
| nomic-embed-text | 8/11 (72%) | 0.766 | 0.652 | **no** |
| hybrid (RRF) | **9/11 (81%)** | 0.033 | 0.031 | **no** |

**No score threshold exists, on any of the three, that separates a question the
corpus answers from a question it does not.** In every case the worst leak
*exceeds* the weakest genuine hit — on BM25 by a factor of 2.9. A question with
no answer anywhere in the corpus scores higher than a question the retriever got
right.

That is not a tuning problem to be solved with a better cutoff. Retrieval score
measures similarity between a query and a passage. Whether the passage answers
the question is a different property, and nothing in the ranking function is
looking at it. Week 6's model judge exists for exactly this.

Note that the three leak figures are not comparable to each other: BM25 is
unbounded, cosine lives in [-1, 1], and RRF sums 1/(60 + rank) so it cannot
exceed about 0.033 however good the match. Each row compares only to itself. The
first version of this table printed one "worst leak" column across all three and
made hybrid look six hundred times safer than BM25, which was a fact about
arithmetic rather than about retrieval.

---

## Measured — the two rankers disagree more than the totals suggest

BM25 and the embedding model tie exactly at 8/11. They disagree on **four of the
eleven**, two each way:

| wins | question | why |
| --- | --- | --- |
| embeddings | What do I need to buy for my child to play? | the answer is *"Your child will need a size 3 ball"* — not one word of the question appears in it |
| embeddings | Do I have to volunteer? | |
| BM25 | What age groups does the club have? | the answer literally contains "age group"; the embedding model went to something merely soccer-adjacent |
| BM25 | When is practice and how often do teams practice? | |

The tie is not two rankers doing the same thing. It is two rankers solving
different questions, with the errors cancelling in the total. Lexical retrieval
wins on exact terminology; semantic retrieval wins on paraphrase. **Reading only
the totals would have produced the conclusion "embeddings add nothing here",
which is false.**

Hybrid then takes 9/11. That was predicted by the disagreement list before it
was run, which is the only prediction this month that came out right.

---

## Measured — the corpus

| | |
| --- | --- |
| Records | 142 (club-01 48 · club-02 36 · club-03 24 · club-04 34) |
| Questions | 19 — 11 answerable, 8 must-refuse |
| **answerable** | **10/11 (90%)** — one record contains the whole answer |
| Embedding cost | 274 MB model, 37.9s for 142 records, cached after |
| BM25 cost | no model, no download, indexes in milliseconds |

`answerable` at 90% is the objective replacement for the "self-contained rate"
that produced 20%, 10%, 15%, 25% and 15% across five hand reviews of the same
corpus. Every answer key is a verbatim string from a PDF, so the question it
asks is exact: *did chunking keep that span of source text inside one record?*
Ten of eleven survived. It returns the same number every run.

---

## What replaced hand-labelling, and why

Five reviews, five numbers, one corpus. Each time the variance traced back to
the instrument or the rubric, never to the documents:

| | what moved it |
| --- | --- |
| 20% | labels supplied by the TA and typed in — not a measurement at all |
| 10% | a viewer that truncated records at 600 characters, so every long record "ended mid-sentence" |
| 15% | same viewer |
| 25% | records shown whole |
| 15% | six records rejected for "contents dot leaders" that were ordinary bullet points |

The review earned its keep — it found the page-rotation bug, the word-spacing
bug, the empty-body merge and the truncating viewer, four real defects no
summary statistic would ever have surfaced. It cannot also produce a stable
number, and asking it to was the mistake.

What it could not do was distinguish **the corpus failing** from **the retriever
failing**. `answerable` and `hit@k` split exactly there: everything below
`answerable` is chunking, and the gap between `answerable` and `hit@k` is
ranking. "Under 60% means the chunking is the problem" had been printed as if it
were a fact for two weeks. It was a guess.

---

## What this number is NOT

Written down deliberately, because it will be tempting to quote 81% later.

- **The answer keys were proposed by a text search over the PDFs.** So the eval
  asks "can the retriever find, in a chunked corpus, what a plain text search
  found in the source?" A passage too mangled for text search to match never
  became a question. **Expect the number to be optimistic.**
- **Eleven answerable questions.** Each one is worth nine percentage points. A
  one-question difference is not a result.
- **At least four of the eight must-refuse cases are wrong.** Concussion,
  uniforms, players per team and game locations all have answers in the
  handbooks. The refusal *finding* survives regardless — the leaks that matter
  come from cases that genuinely have no answer — but `refused 0/8` as a rate is
  not trustworthy.
- **Duplicate qids.** `--keep` preserved the original ids and then renumbered new
  rows straight into them. Harmless to the metrics, confusing to read.

A first pass at authoring accepted 21 machine-proposed keys in a row, because
the tool showed one candidate and asked yes/no — a default with a confirmation
step, not a choice. Rewritten to show four candidates with no default, the
second pass overcorrected into 42% refusals. Both passes are the same lesson:
**an interface decides what the labels will be**, at least as much as the
labeller does.

---

## Carried forward

1. Fix the four mislabelled refusals — needed before `refused` means anything
2. Ship hybrid, not embeddings alone — but see the cost question below
3. club-02's 7 records over 2,000 characters — still the only structural defect left
4. Numbered list items read as headings
5. The swallowed rejection count in `read_real_handbook`
6. From Week 3: `POST /infer` with a typed schema, and the Gradio tab
7. `pipelines_bench.py` — written, committed, still never run

---

## Which one ships

_Name the cost as well as the score. 274 MB and a forward pass per record on a
club's laptop, for one extra question out of eleven — is that the trade you would
defend to a client paying for it?_

## What I would do differently

_your turn — two or three sentences_
