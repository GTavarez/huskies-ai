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

## Carried forward

1. ~~Fix the glued records~~ — **done**: two, not four, and the cause was
   `respace` falling back to the font pass's unspaced output. `repair_glued()`
   now re-spaces word by word. BM25 +1 question
2. **Hand-audit the judge** — ten rows, counted. Still never done
3. **Five more must-refuse questions** — ten rows at ten points each is coarser
   than the effects being measured
4. **Routing, properly** — gate `gemma2:2b`, answerer `llama3.2`, judge
   `qwen2.5:1.5b`. Three different models, finally available
5. Re-run v1 vs v2 on the audited set — retracted in Week 7, never replaced
6. Metadata filtering by club
7. From Week 3: `POST /infer` with a typed schema, the Gradio tab,
   `pipelines_bench.py` still never run
