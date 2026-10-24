# Week 6 — The audit that halved the score, and the comparison that was rigged

## The finding

An eval set built in two contradictory sittings was audited cold, twelve days
later. Six rows were deleted, four were fixed, and the questions that had been
dropped were re-asked with better candidates.

**BM25's hit@5 fell from 72% to 35%.**

That is not a regression. It is the first honest number this project has
produced, and the reason it moved is the finding of the week.

---

## The old comparison was rigged, and the rig was in the tooling

`draft_answers.py` proposed each answer key by running a BM25 search over the
corpus. `retrieval_eval.py` scores by running a BM25 search over the same corpus.

**The proposer and the scorer were nearly the same system.** Every key was, by
construction, a string BM25 ranks highly. The eval was not measuring whether
retrieval could find the answer; it was measuring whether BM25 could find what
BM25 had picked.

That did two things, and the second is worse than the first:

1. It inflated the absolute score.
2. **It rigged the BM25-versus-embeddings comparison in BM25's favour**, because
   embeddings were being asked to compete on keys selected for their lexical
   match.

| | Sep 20 — machine-proposed keys | Oct 2 — audited keys |
| --- | --- | --- |
| BM25 | 8/11 (72%) | **5/14 (35%)** |
| embeddings | 8/11 (72%) | **12/14 (85%)** |
| hybrid (RRF) | 9/11 (81%) | 12/14 (85%) |
| disagreements | 2 each way | **7 embeddings-only, 0 BM25-only** |

A tie became a rout. Nothing about either retriever changed. Only the keys did.

The replaced keys are the ones that broke it — `dedicated to promoting the growth
of competitive youth soccer`, `MPSC does have a payment plan`, the age-group
line. These are what a person decided was the answer after reading the document.
BM25 finds none of them. Embeddings find all of them.

**Lesson, stated generally: when the thing that generates your test data and the
thing you are testing share a mechanism, the test measures the mechanism rather
than the system.** It will not fail loudly. It will produce a believable number.

---

## Embeddings hit the ceiling, and the ceiling is the chunker

| | |
| --- | --- |
| answerable | 12/14 |
| embeddings hit@5 | **12/14** |
| **ranking failures** | **0** |
| corpus failures | 2 |

Embeddings retrieved **every answer that exists in a single record**. There is no
ranking work left to do on this question set.

The two losses are `GONE` rows — the key is in the PDF but no single record
contains it:

- `$560 SPRING SEASON FEE` — club-03's cost section, split across records
- `dedicated to promoting the growth of competitive youth soccer` — club-04's
  mission statement, split across records

> **Corrected 2026-10-04.** Only the first of those was a chunking failure. The
> second row's stored key turned out to be 2,201 characters of pasted terminal
> output — the whole screen went in when `e` was pressed, instead of the one
> sentence. The intended key was in `club-04-s4` the entire time. So the split
> was 1 chunking failure, not 2, and the eval was carrying a corrupt row that no
> amount of chunking work would have fixed. **An eval can be wrong in the same
> way a corpus can, and a `GONE` row means "look at the key" at least as loudly
> as it means "look at the chunker."**

**That changes what Week 6 is.** Before the audit the split was 2 corpus / 7
ranking, and a re-ranker looked like the obvious next build. After the audit it
is 2 corpus / 0 ranking. The re-ranker would improve nothing. The remaining work
is entirely in the splitter.

---

## Which one ships — revised

**Embeddings alone.** This reverses `week-05.md`, which said hybrid.

Hybrid ties embeddings at 12/14 with **zero BM25-only wins**, so the lexical half
contributes nothing the semantic half had not already found. Adding BM25 adds a
second index to maintain in exchange for no questions.

The 274 MB is no longer a one-question luxury argued over on a club's laptop. It
is +7 of 14 — the difference between a system that answers a third of what
parents ask and one that answers everything the documents actually contain.

Keep the BM25 path in the repo as the no-model fallback for a client who cannot
install anything, and quote its real number when offering it: **35%**, not 72%.

---

## The refusal result holds, on all three

| ranker | worst leak | weakest genuine hit | separates? |
| --- | --- | --- | --- |
| BM25 | 18.020 | 6.287 | **no** |
| embeddings | 0.743 | 0.540 | **no** |
| hybrid | 0.033 | 0.030 | **no** |

Eleven must-refuse questions, three ranking functions, and in every case the
worst leak **exceeds** the weakest genuine hit. A question with no answer in the
corpus outscores a question answered correctly.

This survived the audit unchanged, which makes it the most robust result in the
project. Retrieval score measures similarity between a query and a passage.
Whether the passage *answers* the question is a different property, and no
ranking function is looking at it.

---

## What the audit itself found

Started at 19 rows. Kept 13, fixed 4, deleted 6. Re-asked the dropped questions
with six candidates instead of three. Finished at 25 — 14 answerable, 11
must-refuse.

Deleted, with reasons:

| question | why |
| --- | --- |
| How much does it cost to play? | duplicate of q01, already answerable with $525 |
| What age groups does the club have? | key was a heading rule, not the age groups |
| How many players are on a team? | corpus answers it; the search didn't surface it |
| Do I have to sign a photo release? | corpus answers it; the search didn't surface it |
| When is practice and how often? | key located the volunteer roles section |
| How are the teams created? | search matched the acknowledgements page |

Four distinct retrieval failure modes turned up while auditing, all from
documents I did not write:

1. **wrong word sense** — "created" matching *"Guide created by Marcos Estebez"*
2. **shared vocabulary** — "photo" matching Photo Day volunteer duties
3. **precision losing to repetition** — the short Age Group Structure section
   outranked by longer sections that merely say "age group" more often
4. **right topic, wrong entity** — US Youth Soccer's mission statement offered as
   the answer to *"what is the club's mission?"*

The fourth is the dangerous one. It reads perfectly, it is about the right
subject, and it is wrong. A model answering from it would sound authoritative.

---

## A rule worth keeping: a key is a locator, not an answer

The audit kept clarifying the same test. An answer key is not meant to read as a
good answer. It is an exact string whose presence proves a retrieved record
contains the answer. So:

> *Does a record containing this exact string contain the answer to the question?*

By that test a truncated fragment can be a perfectly good key, and a grammatical
sentence can be a terrible one — a page footer appearing on every page of
club-02 locates nothing at all.

And the sharper corollary, which only showed up on the payment-plan row: **pick
the key that IS the answer, not one sitting next to it.** `to pay their first
payment before August 31st` and `MPSC does have a payment plan` live in the same
paragraph today, so either passes. The moment the splitter cuts between them —
which is exactly what Week 7 will do — the first one silently starts pointing at
a record that does not answer the question, and the eval goes wrong without
failing.

---

## Also found

- **Invalid input was being filed as data.** `draft_answers.py` let any
  unrecognised keypress fall through to the refuse branch, so a line of text
  pasted at the wrong prompt became "the handbooks do not answer this." Fixed to
  re-prompt. A prompt that turns a mistake into a measurement is worse than one
  that rejects it.
- **Two clubs give opposite answers to the same question.** club-02 provides
  uniforms free; club-03 charges ~$100. Retrieval has no idea which club a parent
  belongs to, so it will confidently hand them the wrong club's policy — and it
  will not refuse, because it found a good answer. Just not theirs. Metadata
  filtering, not better ranking, is the fix.
- **No handbook tells a parent what to do about a concussion.** All four name a
  form or point at a state association. Four real clubs, zero procedures.
- **No handbook addresses a family who cannot afford the fees.** Fee amounts yes,
  payment plans yes, hardship provision nowhere.

Those last two are findings about the documents rather than the software, and
they are worth more to a club than the retrieval scores are.

---

## Resolved 2026-10-04

`SPRING SEASON FEE: $240` was being promoted to a heading. It is a row of a fee
table, and it collects every formatting signal a heading has — ALL CAPS, Title
Case, short, no full stop, and genuinely set in bold — so it scored 7 on text
evidence plus 4 from the font pass. club-03's cost table was four such lines, each
starting a new record with an unrelated body attached, which is why
`$560 SPRING SEASON FEE` existed in the PDF and nowhere in the corpus.

Fixed with a `DATA_ROW` rule in `headings.py`: a short `LABEL: value` line whose
value is a number or an amount scores **-10**. The magnitude is the arithmetic —
anything weaker leaves it at or above the threshold once the font boost lands,
which is exactly what -6 did on the first attempt.

What the number encodes: every signal pushing a fee line toward "heading" is
about **formatting**; the one pushing back is about **content**. For retrieval,
content wins. A number being bold does not make it a section. Fee tables, price
lists and spec sheets all have this shape, so this is not a club-03 quirk.

| | before | after |
| --- | --- | --- |
| records | 142 | 142 |
| **answerable** | **12/14 (85%)** | **14/14 (100%)** |
| BM25 hit@5 | 5/14 (35%) | **7/14 (50%)** |
| corpus failures | 2 | **0** |

**The corpus now contains every answer in a single record.** Every remaining loss
is ranking, and embeddings had already solved ranking.

---

## Carried into Week 7

1. **club-02's slabs** — 8 records over 2,000 characters. Not currently blocking
   any question, which is why it drops below metadata filtering
2. Metadata filtering by club, so a parent cannot be handed another club's policy
3. Numbered list items still read as headings
4. The swallowed rejection count in `read_real_handbook`
5. The re-ranker — **demoted**, there are no ranking failures left to fix
6. From Week 3: `POST /infer` with a typed schema, and the Gradio tab
7. `pipelines_bench.py` — written, committed, still never run

---

## What I would do differently

I would have built the key-proposer and the scorer on deliberately different
mechanisms, and written down which mechanism each one used. The circularity was
not subtle once it was visible — a BM25 search chose the keys and a BM25 search
graded them — but nothing in either script said out loud what it was doing, so
for two weeks there was no place to notice it. A one-line comment naming the
retrieval method in each file would have been enough.

The general rule I would carry anywhere: **write down what generated your test
data, next to the score it produced.** Not to be rigorous for its own sake, but
because circular test data does not fail loudly. It produces a believable
number, slightly flattering, in exactly the direction you were hoping for. 72%
looked like progress for twelve days.

I would also have audited the question set before running a comparison on it
rather than after. The audit cost an afternoon and invalidated three weeks of
figures; doing it first would have cost the same afternoon and invalidated
nothing.

---

> **Follow-up, 2026-10-23.** Both chunking losses are fixed — `answerable` is now
> **25/25** on a larger question set, so no question is lost to the splitter at
> all. Item 1 above is closed. Item 2, metadata filtering by club, turned out to
> be more serious than written here: it blocks the *measurement*, not just the
> product. See `week-07.md`.
