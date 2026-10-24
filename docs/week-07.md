# Week 7 — The judge that beat the threshold, and a number quoted on the wrong denominator

## The finding

A second model reading the retrieved context separates "the corpus answers
this" from "the corpus contains words that look like this." No retrieval score
does.

| | correct refusals |
| --- | --- |
| BM25 score threshold | 0/15 |
| embedding score threshold | 0/15 |
| RRF score threshold | 0/15 |
| **model judge reading the context** | **9/15** |

That `0` held for six weeks across three ranking functions and never moved by a
single question. It was not a tuning problem and no cutoff was going to fix it.
A ranking score measures similarity between a query and a passage; whether the
passage *answers* the question is a different property, and nothing in a ranking
function looks at it. A model does.

**9/15 is a floor, not an estimate** — see the refusal-string defect below.

---

## First, the correction: the denominator was wrong

Week 6 closed with `hit@5 100%` and that figure got quoted into a status
summary. It was measured on the **14** answerable questions the cold audit
produced. Eleven more answerable questions were added afterwards and never ran
through `retrieval_eval.py`.

| | 14-question subset | all 25 answerable |
| --- | --- | --- |
| answerable | 14/14 (100%) | **25/25 (100%)** |
| BM25 hit@5 | 7/14 (50%) | **11/25 (44%)** |
| embeddings hit@5 | 13/14 (92%) | **19/25 (76%)** |
| hybrid (RRF) hit@5 | 14/14 (100%) | **19/25 (76%)** |

`answerable` holding at 100% across the larger set is the one genuinely good
number here: **every answer sits intact inside one record.** The chunker is
done. Zero questions are lost to the corpus.

Everything missing is ranking. BM25 loses 14 of 25; embeddings lose 6.

The lesson is not that the number got worse. It is that **a metric and its
question set have to be re-run together**, because adding questions to the set
silently invalidates every figure computed before they existed — and it fails
quietly, by continuing to print a believable number.

---

## Two runs, and they disagree

| | run 1 | run 2 |
| --- | --- | --- |
| correct refusals | 9/15 | 9/15 |
| answered, grounded | 21/25 | 20/25 |
| invented | 0 | 0 |
| over-refused | 3 | 4 |

Same code, same models, `temperature=0`, `seed=7`, cached vectors. One
answerable question flipped from answered to declined.

**Ollama is not deterministic even fully pinned.** So a one-question difference
out of this harness is not a result, and every judge figure in this file is
quoted with the run count attached. The refusal result is the one that held
identically across both, which is why it is the week's finding and the others
are observations.

**The variance is in generation only, and that was worth isolating.**
`retrieval_eval.py` and `embed_eval.py` were each run twice and produced
byte-identical output — the same hit list, the same misses, the same scores to
three decimal places, the same `17.914` worst leak and `4.209` weakest hit. So:

| | reproducible? |
| --- | --- |
| BM25 | yes |
| embeddings (cached vectors) | yes |
| RRF | yes |
| the answerer's generated text | **no** |

That narrows the caveat considerably. `hit@5`, `answerable` and the refusal-floor
overlap can be quoted as facts about the system. Anything downstream of
`llama3.2` generating a sentence needs the run count beside it. Two different
confidence levels, in the same report, and conflating them would have meant
hedging the solid numbers and over-trusting the soft ones.

---

## The refusal check cannot be a substring match

`judge.py` treats the literal sentence as authoritative, overruling the judge:

```python
REFUSAL = "not covered in the club documents"
said_refusal = REFUSAL in answer.lower()
```

On q36 the answerer replied:

> *"That is covered in the club documents."*

The word **not** is gone. The substring did not match, so a content-free
sentence was scored as an answer, and the judge then rated it SUPPORTED.

The failure is asymmetric, which matters for how the numbers should be read:

- On a **must-refuse** row, a mangled refusal is scored as a leak. The system is
  punished for refusing correctly. **That makes 9/15 a floor.**
- On an **answerable** row, a mangled refusal is scored as an answer. That
  inflates "answered, grounded."

A magic string is a bad contract with a small model. The check needs to be
tolerant of corruption — a short answer containing `covered in the club
documents` is a refusal whatever happened to the negation.

---

## Where the metric and the product collide: four clubs, one question

Three of the six answerable misses are not retrieval failing.

| | the answer key | key's club | model answered from |
| --- | --- | --- | --- |
| q32 — How do I contact the club? | `● For club payment and uniform issues please contact the club registrar` | club-04 | Coaching Director / Age Coordinator — **another club** |
| q33 — Is there a code of conduct? | `By accepting a position in the club, parents and athletes agree to the` | club-04 | `[club-03-s9]`, `[club-03-s19]` — **another club** |
| q39 — How do I sign up to coach? | `filling out a SAY Soccer volunteer form` | club-02 | "**the** SAY Soccer volunteer form" |

On q32 and q33 the model returned a correct answer from a handbook that also
answers the question, and `contains_all` scored it a miss because the key binds
the question to one specific club.

**So metadata filtering by club is no longer just a product feature. It is a
precondition for the metric meaning anything** on any question that four
handbooks each answer differently. Without it, "right answer, wrong club" and
"no answer found" are the same measurement.

q39 is the thin end of the same wedge: the key says `a`, the record says `the`.
One article decides a question. Week 6's rule — *pick the key that IS the
answer, not one sitting next to it* — needs a companion: **pick the key from the
record the answer will actually come from.**

---

## The cheapest four questions on the board

| | retrieved | model's answer |
| --- | --- | --- |
| q09 — What happens if I yell at the referee? | **yes** | declined |
| q11 — Can my child play up an age group? | **yes** | declined |
| q28 — Is there a tryout? | **yes** | declined |
| q30 — Can my child switch to a different team? | **yes** | declined |

The answer was in the context the model was handed, and it refused anyway. That
is the grounded prompt frightened into uselessness — *"Do not guess. Do not use
general knowledge"* read as *"decline unless certain."*

Four questions for a prompt change. No model change, no index change, no new
build. It is the highest-value item in the file and the smallest.

---

## Correct, and still unshippable

Two refusals are right engineering and wrong product:

- **"Am I allowed to watch practice?"** — no handbook states it, because no
  handbook would. It is too obvious to write down.
- **"How much does it cost?"** on a corpus of four clubs — unanswerable without
  knowing which club.

A flat *"that is not covered in the club documents"* is technically correct and
reads as a brush-off. The refusal needs a second half: *"the handbook doesn't
cover that — your coach or the club registrar can tell you."* Correct refusal,
useful refusal. They are not the same deliverable.

---

## By document — BM25, of the questions each could answer

| | found |
| --- | --- |
| club-02 | 4/11 |
| club-03 | 1/4 |
| club-04 | 6/10 |

club-03 at 1 of 4 is the one to look at. It is also the smallest corpus (24
records) and the one with the duplicate records still in it.

---

## Which one ships — and why the metric can no longer answer it

| ranker | hit@5 | worst leak | weakest hit | separates? |
| --- | --- | --- | --- | --- |
| BM25 | 11/25 (44%) | 17.914 | 4.209 | no |
| embeddings | 19/25 (76%) | 0.743 | 0.540 | no |
| hybrid (RRF) | 19/25 (76%) | 0.033 | 0.029 | no |

Hybrid and embeddings tie at 19. **They are not the same nineteen.**

| | |
| --- | --- |
| RRF rescued | Do I need to buy a uniform? |
| RRF rescued | Is there a tryout? |
| RRF dropped | What happens if my child misses practice? |
| RRF dropped | How do I sign up to be a coach? |

Net +0, two rescued, two dropped. Week 6 read a tie as "hybrid adds nothing";
on the full set a tie turns out to be a **trade**, and the trade was invisible
until the script was changed to print set differences instead of counts. That
reporting gap existed for three weeks while two different "which one ships"
conclusions were drawn on top of it.

### Fusion found a question neither ranker found

*"Do I need to buy a uniform?"* does not appear in the BM25-versus-embeddings
disagreement list, because **both of them missed it.** Hybrid retrieved it.

This is RRF behaving exactly as designed and it is worth stating precisely,
because it is the strongest argument for the hybrid that exists in this project:

```
rrf score = sum over rankings of 1 / (60 + rank)
```

Each ranker is asked for the top `2k` and the pooled results are re-ranked. A
record sitting 7th in one ranking and 8th in the other scores
`1/67 + 1/68 = 0.0296` — more than a record ranked 3rd in one and 50th in the
other at `1/63 + 1/110 = 0.0250`. So **broad mediocre agreement beats narrow
strong preference**, and a record that neither ranker would have shown in its
own top 5 can enter the fused top 5. That is a different capability from
reordering, and no comparison of two hit lists can reveal it.

It cuts the other way too: RRF captured only one of BM25's two unique wins. It
took *Is there a tryout?* and left *Is there a code of conduct?* — a record BM25
ranked highly and the embedding model ranked nowhere gets outvoted by the
consensus.

### So the decision is no longer an engineering one

At 19 and 19 the metric is silent. What remains is which four questions matter:

| | |
| --- | --- |
| you gain | *Do I need to buy a uniform?* · *Is there a tryout?* |
| you pay | *What happens if my child misses practice?* · *How do I sign up to be a coach?* |

Both gains are things a parent asks **before** joining — cost of kit, and
whether their child has to try out. Both losses are asked **after** joining, and
one of them is asked by a volunteer rather than a parent. If the product's job is
answering a new family's first questions, that is not a wash. If the eval
weighted questions by how often a parent actually asks them, it would say so
numerically — and it does not, because every question in it is worth exactly
1/25.

**That is the recommendation this week: weight the question set before shipping
a ranker.** Not another confident ranker verdict on an unweighted set — three
have been written and each was decided by a question or two. The honest output of
25 equally-weighted questions is that BM25 alone is out at 44%, and the choice
between the other two needs information the eval does not currently carry.

---

## Carried into Week 8

1. **Fix the grounded prompt** — four over-refusals with the answer in context
2. **Make the refusal check corruption-tolerant** — a substring match on a
   negated sentence is not a contract
3. **Metadata filtering by club** — now blocking the eval, not just the product
4. **Weight the question set** by how often a parent actually asks each
   question — the hybrid-vs-embeddings choice is a tie at 19/25 and cannot
   be settled while every question is worth 1/25
5. **Spot-check the judge by hand** and quote the count next to 9/15
6. **Better refusal wording** — correct is not the same as useful
7. Re-check the four labels flipped during the audit's over-correction phase
8. club-03's duplicate records; club-02's oversized records; `club-04-s22`
   titled `'st'`; the swallowed rejection count in `read_real_handbook`
9. From Week 3: `POST /infer` with a typed schema, the Gradio tab,
   `pipelines_bench.py` still never run

---

## What the handbooks say, which is worth more than the scores

Unchanged from Week 6 and still the most saleable output of the project:

- **Five questions where all four handbooks state policy and never schedule** —
  game times, practice times, game locations, tryout dates, parent meetings
- **Four cross-club contradictions** — uniforms free vs ~$100; code of conduct
  signed vs agreed by accepting a position; coaching via volunteer form vs
  hiring process; tournament fees included vs not
- **No handbook tells a parent what to do about a concussion.** Four clubs, zero
  procedures — all four name a form or point at a state association
- **No handbook addresses a family who cannot afford the fees.** Amounts yes,
  payment plans yes, hardship provision nowhere

---

## What I would do differently

I would attach the denominator to every number I wrote down. `hit@5 100%` was
true of fourteen questions and got carried forward as though it were true of the
system, and nothing in the tooling objected — the script happily printed a
correct figure about a stale subset. The fix is not more care; it is making the
question count part of the number everywhere it appears, including in
conversation.

I would also stop answering "which one ships" on a set small enough for one
question to decide it. Three weeks produced three answers and the reasoning was
sound every time. The flaw was answering at all at that sample size, and the
honest output of a 25-question eval is a direction, not a verdict.

And I would treat a magic string as a defect on sight. `"not covered in the club
documents"` was load-bearing for an entire metric and it was defeated by a small
model dropping one word — a failure mode that was obvious in advance to anyone
who has watched a 3B model paraphrase an instruction.
