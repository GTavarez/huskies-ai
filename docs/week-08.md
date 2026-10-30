# Week 8 — Guards that worked on websites, and did not work here

## The experiment

Four deterministic checks were built for a patient-question demo running on
real medical practice websites, where each caught a failure a model judge
missed: an invented phone number, a citation to an unrelated page, cosmetic
aftercare offered as an after-hours policy, a booking claim about a site with
no booking.

They cost no model call. They can only turn an answer into a refusal. So
porting them into `judge.py` looked like free safety.

```
python judge.py --guards
python judge_diff.py out/judge.csv out/judge-guards.csv
```

| | baseline | with guards |
| --- | --- | --- |
| correct refusals | 8/10 | **9/10** |
| answered, grounded | 24/30 | **10/30** |
| invented | 0 | 0 |
| over-refused | 4 | **16** |

**Fixed 1, broke 14.** Twelve of the fourteen were answers that were correct
and whose source had been retrieved.

---

## Why they did not transfer

Not a tuning problem. The two corpora differ in a way that decides whether the
relevance check means anything.

**A practice website chunk is 700 characters of marketing copy** sliced at an
arbitrary boundary. It mentions everything — a Botox page says "hours" because
it discusses aftercare timing. So requiring the *cited sentence* to mention
what was asked is a real filter: it separates the sentence that answers from
the page that merely contains the vocabulary.

**A handbook chunk is a heading-delimited section** about one subject. It is
already topically coherent, so the filter has nothing to remove — and what it
does instead is penalise ordinary paraphrase:

| question | the sentence that answers it | held because |
| --- | --- | --- |
| What happens if it rains? | *"Practice and games will be suspended and will not resume until 30 minutes after the last sign of lightning/thunder."* | never mentions "rains" |
| How much are the fees? | the fee sentence | never mentions "much" |
| What do the fees actually pay for? | the sentence listing what fees cover | never mentions "actually", "pay" |

The handbook says lightning; the parent says rain. No lexical check bridges
that, and on this corpus almost every question has that shape.

**The rule: a lexical relevance check earns its place only where chunks are
topically incoherent.** Coherent chunks — anything split on headings — make it
a paraphrase penalty and nothing else.

---

## Two real bugs it found anyway

**1. The number guard flagged correctly quoted prices.** `$240.` at the end of
a sentence was compared against a source containing `$240` and reported as
invented. The pattern's trailing `[\d,.:]*` swallowed the full stop, so **any
figure ending a sentence** hit this.

That one was live in the demo being shown to prospects: a practice's real price
or opening time, quoted correctly, would have been blocked as a fabrication.
Fixed in both.

**2. Four records still have their words glued together.**

| record | text |
| --- | --- |
| `club-04-s22` (title `'st'`) | `ALLplayerswillbeexpectedtopaytheirfirstpaymentbeforeAugust31.MPSCdoeshaveapaymentplan` |
| `club-04-s11` | `FallSeasonAugusttoOctober SpringSeasonApriltoJune` |
| `club-03-s16`, `club-03-s18` | one glued run each |

Four of 141. The Week 4 spacing fix handles the rest of the corpus and misses
these, and the damage is not cosmetic: lexical retrieval cannot match a word
that has no spaces around it. `payment plan` is in that record and unfindable.

This had been sitting on the carried-forward list as "`club-04-s22` titled
`'st'`" — a cosmetic-sounding note. It is a retrieval defect, and the guards
are what turned it into a measurement.

---

## The glued records, fixed

Diagnosed properly, it was two records, not four — and pypdf was not the cause.

```
club-04: pypdf itself produces 0 glued runs
```

The spacing was correct coming out of the PDF. The font pass joins
text-showing operators with no separator (`raw = "".join(...)`), and `respace`
exists to give that line pypdf's own spacing back. When its lookup failed it
returned `line` untouched — which is the glued version. **A failed lookup did
not degrade to worse spacing, it degraded to none.**

The lookup fails because a whole line is a brittle key: the font pass groups
runs by rounded baseline, so two separately-drawn lines sharing a y arrive
concatenated in an order pypdf's text never used.

A single glued word is a much better key. `repair_glued()` re-spaces runs of
12+ letters one at a time, and leaves alone anything pypdf also renders without
spaces — an email address or a URL is found as itself and untouched. That is
why club-03's three "glued runs" were never defects: they are
`bellinghamsportsplex` and `northpugetsoundleague`, fragments of a real address
and a real URL.

### What it was worth

| | before | after |
| --- | --- | --- |
| BM25 hit@5 | 14/30 (46%) | **15/30 (50%)** |
| embeddings hit@5 | 24/30 (80%) | 24/30 (80%) |
| hybrid hit@5 | 24/30 (80%) | 24/30 (80%) |
| answerable | 30/30 | 30/30 |

The question that moved is q23, *"Is there a payment plan?"*, and it now
retrieves `club-04-s22` — the record that read `MPSCdoeshaveapaymentplan`. It
also now wins q01 and q40.

**Embeddings did not move at all.** They were finding that record semantically
the whole time, gluing and all.

That is a better argument for hybrid than any in the week notes so far. The
defect damaged one index and not the other, which is the case the comparison
has been circling since Week 5: two rankers that fail on different things are
worth more than two that fail together. It took a corpus bug to show it
cleanly.

---

## Prediction scorecard — 2 of 4

| predicted | actual | |
| --- | --- | --- |
| correct refusals 8 or 9 | 9/10 | right |
| invented 0 | 0 | right |
| grounded 20–23 | **10** | wrong by ten |
| over-refused 5–8 | **16** | wrong by eight |

The direction was right — I expected the guards to cost more than they gained —
and the magnitude was not close. Both misses are the same miss: I assumed
paraphrase would be rare and it is the norm here.

---

## What ships

**The guards stay out of the default path.** `--guards` remains, off, as a
documented experiment with its own output files.

That is not a wasted port. It produced a transferable rule about when a lexical
relevance check is worth anything, a live bug fix in the demo, and a corpus
defect that had been mis-filed as cosmetic for three weeks.

---

## Auditing the judge, and getting the sample wrong twice

Every judge figure in this repo — 8/10 correct refusals, 24/30 grounded, the
whole guards comparison — has been quoted since Week 7 with no error bar. The
fix is ten rows read by hand. Choosing *which* ten took two attempts.

**First attempt: the first ten rows of `judge.csv`.** Four of them are
refusals, and on a refusal `refusal_kind()` sets the verdict and the judge's
opinion is discarded. Those four audit a component that did not run. Across the
whole file it is 14 of 40 — **more than a third of the rows cannot tell you
anything about the judge.**

**Second attempt: the first ten rows the judge actually ruled on.** Taken in
qid order, which on this set returns ten `answerable` + SUPPORTED rows: the
easiest cases in the file, and all written in the same sitting, so they
resemble each other. A flattering number carrying no information.

**What it samples now.** The judge's errors concentrate in two places, so those
come first:

- a **refuse** row it called SUPPORTED — it endorsed an answer to a question
  the corpus is not supposed to answer (q21, q29)
- any **UNSUPPORTED** verdict — it rejected something, and in Week 8 it rejected
  two answers that quoted their source word for word

Then the ordinary rows, spread across the file rather than taken from the
front.

`judge_audit.py` prints each sampled row with the answer and the handbook
sentences nearest to it, and deliberately does not say whether the verdict is
right. A TA supplying a label table is how the Week 4 self-contained baseline
stopped being a measurement; the same mistake made twice would be harder to
explain.

### The number

_Pending: ten rows read, count of correct verdicts out of ten. Once recorded it
goes beside every judge figure in this file and in `week-07.md`. Until then,
8/10 and 24/30 are quoted without an error bar — and on a 10-row refuse set, a
one-question move and noise are the same size._

---

## Routing, closed

Week 7 killed a 1B gate and said the idea survived — what died was the
implementation, and a proper test needed three capable models for three jobs.
`gemma2:2b` arrived, so: gate `gemma2:2b`, answerer `llama3.2:latest`, judge
`qwen2.5:1.5b`. All different, no model grading its own work.

| | correct |
| --- | --- |
| `llama3.2:1b` gate (Week 7) | 13/40 |
| **`gemma2:2b` gate** | **24/40** |
| constant "COVERED" | **24/40** |
| constant "MISSING" | 16/40 |

The better model nearly doubled the raw score and **tied the trivial baseline
exactly.** It answered COVERED 30 times out of 40.

| | |
| --- | --- |
| says COVERED when the answer IS in context | 19/24 (79%) |
| says COVERED when it is NOT | 11/16 (69%) |

Ten points of separation, where the 1B gate had none at all (16% vs 19%,
slightly inverted). So gemma2 is genuinely better at the task and still not
good enough to beat saying one word every time.

It also cost: grounded 24/30 → **21/30**, over-refused 4 → **7**. Three
answerable questions whose answers had been retrieved were routed out before
anything generated. Correct refusals did not move.

**Routing is closed.** Two gate models, both at or below a constant.

### Why the gate fails where the judge works

Same models, same corpus, two jobs that look similar and are not:

| | sees | has to |
| --- | --- | --- |
| **gate** | question + context | predict whether an answer can be produced |
| **judge** | question + context + the answer | check one against the other |

The judge gets 8/10 on refusals where no retrieval score managed better than 0.
The gate ties a constant. The difference is that checking is a comparison and
predicting is a guess, and a 2B model can do the first.

**The rule: spend the extra model call after generation, not before.** A gate
saves the generation when it is right and is wrong often enough to cost more
than it saves. A verifier only ever runs on something that already exists, and
can be wrong without inventing anything.

That is the same shape as this project's oldest finding. A retrieval score
cannot tell whether a passage answers a question; a model reading the passage
and the answer together can. Prediction loses to verification both times.

---

## Metadata filtering by club — kept

A parent belongs to one club. The corpus holds four, and they contradict each
other on uniforms, conduct, coaching and tournament fees. An unfiltered search
can hand a family another club's policy, confidently, and never refuse — it did
find a good answer, just not theirs.

It also distorts the measurement: a correct answer from the wrong handbook
scores identically to finding nothing, which is how "right answer, wrong
entity" has been logged as a ranking failure since Week 6.

Every answerable question already carried a `document` field, so scoping cost
nothing but a filter.

| | whole corpus | per club |
| --- | --- | --- |
| BM25 hit@5 | 15/30 (50%) | **19/30 (63%)** |
| club-02 | 5/13 | 6/13 |
| **club-03** | **2/6** | **4/6** |
| club-04 | 8/11 | 9/11 |
| embeddings hit@5 | 24/30 | **25/30** |
| hybrid hit@5 | 24/30 | 24/30 |

Nothing got worse, which is also a check on the labels: the key is inside that
club's records by construction, so filtering can only remove competitors. A
question that dropped would have meant a wrong `document` field.

**club-03 was being drowned out.** 2/6 to 4/6 once it competes only against its
own 23 records. And 48 of the 141 records are club-01 — a generic introduction
to youth soccer, not a club handbook, the source of no answerable question, and
therefore pure interference in every search ever run against this corpus.

Must-refuse questions stay unfiltered. No club answers them, so scoping would
only make refusing easier, and `refused 0/10` is the one result that has
survived every change since Week 5. It does not need help.

### Scoping changes what the lexical half is for

| | whole corpus | per club |
| --- | --- | --- |
| embeddings | 24/30 | **25/30** |
| hybrid (RRF) | 24/30 | **24/30** |

Unscoped, hybrid ties embeddings. Scoped, it falls one behind — and the fusion
breakdown says why: RRF rescues *Is there a code of conduct I have to sign?*
and drops *What happens if I yell at the referee?* and *How do I sign up to be
a coach?*

The reading that fits: once the candidate pool is restricted to one club it is
already clean, so BM25's contribution is less about cutting through
interference and more about pulling the fused ranking toward literal wording.
The questions it costs are both paraphrase — *yell at the referee* against a
handbook discussing criticism of officials, *sign up to be a coach* against a
SAY Soccer volunteer form.

**This is not a verdict on which ranker ships.** One question out of thirty is
inside the noise this set can resolve — Week 5 wrote that rule down after a
one-question difference produced a confident conclusion that was wrong, and
"which one ships" has already been answered three times in this project and
revised twice. What can be said is narrower and holds: **the lexical half was
doing more work before scoping than after**, and its unique contribution is now
one question while costing two.

Settling it needs the weighted question set, not another run.

---

## The oversized-record split — built, measured, reverted

After scoping, nine of the eleven remaining BM25 misses were club-02's, and
club-02's records are three times everyone else's:

| club | records | mean | median | max | over 2,000 |
| --- | --- | --- | --- | --- | --- |
| club-01 | 48 | 426 | 333 | 1,938 | 0 |
| **club-02** | 36 | **1,370** | **866** | **5,562** | **7** |
| club-03 | 23 | 637 | 520 | 1,869 | 0 |
| club-04 | 34 | 616 | 375 | 2,674 | 1 |

A 5,562-character record is a chapter. The hypothesis — that BM25's length
normalisation was diluting the query's terms — was specific, long-standing
(carried since Week 5) and had an obvious fix: split oversized sections again
on sentence boundaries, with overlapping windows so no answer key is severed.

The split worked as designed. club-02 went 36 records to 79, mean 1,370 to 711,
nothing over 2,000. `answerable` held at 30/30, so the overlap did its job.

| | 141 records | 200 records |
| --- | --- | --- |
| BM25 by club | 19/30 | **19/30** |
| **club-02 specifically** | **6/13** | **6/13** |
| embeddings by club | 25/30 | **24/30** |
| hybrid by club | 24/30 | **23/30** |
| judge, correct refusals | 8/10 | **7/10** |

**The club it was built for did not move at all.** BM25 held at 19 by trading
two questions for two others. Everything else lost one. A 40% larger corpus for
a net negative.

### Correlation read as cause

Nine of eleven misses were club-02's, and club-02 had the biggest records. But
club-02 also holds **13 of the 30 questions**, more than any other club, so it
would have topped the miss list whatever the reason.

What those misses are:

| question | what the handbook says |
| --- | --- |
| What happens if it rains? | lightning/thunder |
| What should my child wear to practice? | turf shoes |
| How do I sign up to be a coach? | a SAY Soccer volunteer form |

Every one sits in the embeddings-only column. **They are paraphrase, and
re-chunking does not touch paraphrase.** BM25 is at its ceiling on that
handbook, which is why embeddings reach 25/30 against its 19/30 — no longer a
defect to fix, but the argument for the architecture already in place.

Reverted. `split_long` stays in `headings.py`, off, with these numbers in the
comment above it, so the next person to have the idea reads what happened
instead of repeating it.

---

## Predictions this week — 2 of 6

| | predicted | actual |
| --- | --- | --- |
| guards: grounded | 20–23 | **10** |
| guards: over-refused | 5–8 | **16** |
| glued records: BM25 | +1 or +2 | +1 ✓ |
| gemma2 gate | 20–28, level with a constant | 24/40, exactly level ✓ |
| club scoping: BM25 | 22–26 | **19** |
| split: BM25 | 21–24 | **19** |

Direction right almost every time, magnitude wrong almost every time, and
always in the same direction — every change was predicted to do more than it
did. The one structural prediction, that the gate would tie a constant, is the
only one that was not about size.

Worth recording because it is the bias to correct for, not a run of bad luck:
**a change that looks like it should fix nine failures fixes two.**

---

## Carried forward

1. ~~Fix the glued records~~ — **done**: two, not four, and the cause was
   `respace` falling back to the font pass's unspaced output. `repair_glued()`
   now re-spaces word by word. BM25 +1 question
2. **Hand-audit the judge** — tooling done (`judge_audit.py`, error-weighted
   sampling). The count itself is still outstanding
3. **Five more must-refuse questions** — ten rows at ten points each is coarser
   than the effects being measured
4. ~~Routing, properly~~ — **closed**. gemma2 gate scores 24/40 against a
   constant's 24/40, and costs three grounded answers. Verification after
   generation works; prediction before it does not
5. Re-run v1 vs v2 on the audited set — retracted in Week 7, never replaced
6. ~~Metadata filtering by club~~ — **done**, BM25 15/30 → 19/30. What remains
   after it is paraphrase, which is an embeddings job, not a chunking one
7. From Week 3: `POST /infer` with a typed schema, the Gradio tab,
   `pipelines_bench.py` still never run
