# Week 4 — Real documents

## The finding

Four weeks of ingestion work looked finished. It was finished against a corpus
I wrote myself, which could not fail.

Four real club handbooks, downloaded from four club websites, produced a **25%
self-contained rate**. Northside scores near 100% on the identical test, because
it was built clean on purpose.

But the corpus-level number is the less interesting half. Broken out by document:

| document | reviewed | self-contained |
| --- | --- | --- |
| club-01.pdf | 8 | **0 (0%)** |
| club-02.pdf | 5 | 1 (20%) |
| club-03.pdf | 1 | 1 (100%) |
| club-04.pdf | 6 | 3 (50%) |

**club-01 is zero for eight, and every summary metric says it is the healthiest
document in the corpus** — 34 records, 2 fragments, no slabs, median 529
characters, the tightest distribution of the four. Every number I had been
reporting was blind to the only document that is completely unusable.

That is the result of the week. Not the 25%.

---

## Measured — the corpus

Four handbooks: 609 KB, 279 KB, 99 KB, 386 KB. All four parsed by the font pass;
none needed the text-heuristic fallback. **128 records.**

| source | records | median chars | shortest | longest | under 100 | over 2000 |
| --- | --- | --- | --- | --- | --- | --- |
| club-01.pdf | 34 | 529 | 65 | 1,487 | 2 | 0 |
| club-02.pdf | 36 | 822 | 32 | 5,562 | 2 | 7 |
| club-03.pdf | 24 | 400 | 44 | 1,869 | 1 | 0 |
| club-04.pdf | 34 | 374 | 85 | 2,674 | 1 | 1 |
| **Northside** | **21** | ~300 | 121 | ~800 | **0** | **0** |

**6 of 128 records — 4.7% — are under 100 characters.** It was 23% before the
fixes below. Three of the four clubs now land within two records of each other
(34, 36, 34) on documents of very different lengths; four independent documents
agreeing on how many sections a club handbook contains is evidence the splitter
is reading structure rather than noise.

**club-02 is the remaining structural problem** — 7 records over 2,000
characters, longest 5,562, median 822 against 374–529 for the others. Every fix
this week attacked over-splitting. club-02 under-splits, and nothing here
touches it.

---

## Why club-01 fails, and why no metric saw it

club-01 is laid out in **multiple columns**, with pull-quotes and sidebar
citations. `lines_with_font` groups text runs by baseline across the full page
width, so a run in the left column and a run in the right column at the same
height become one line. The extractor reads straight across the gutter:

> "- Bigelow, Moroney, & Hall, 2001 too much attention to the game." "When
> watching a youth sports game, if you can't carry on a normal conversation
> with the person next to you then you're probably paying instructions."

A sidebar citation, a pull-quote and body text, interleaved. The sentences are
shuffled before chunking ever runs.

Every metric in the table above measures **record geometry** — how many, how
long, how evenly distributed. Interleaved columns produce records of perfectly
ordinary length in perfectly ordinary quantities. The defect lives in word
order, and nothing that counts characters can see word order.

The general form, which is the part worth keeping: **a metric can only find
defects in the dimension it measures.** Length metrics find length defects. Only
reading finds reading defects. Fifteen minutes of judging records by hand found
what four weeks of summary statistics could not.

---

## What broke — mine, not the corpus

Three of this week's four bugs were in my own code, and two of them were in the
measuring instrument rather than the thing being measured.

**1. Word spaces were being guessed.** A PDF does not store the space between
two words as a space character; it stores a jump in x. `lines_with_font`
estimated where each run ended (`len(text) * size * 0.5`) and inserted a space
if the next run started far enough past it. On real fonts that under-inserted
badly: `Respectand Responsibility`, `MPSC utilizesSoccerVillage`,
`Athletesshouldneverreturntoplay`. **Fourteen of twenty reviewed records were
rejected for spacing rather than for structure.**

Fixed by not guessing. pypdf's `extract_text()` already resolves spacing from the
real positional offsets, so the font pass now locates each line inside that plain
text — matching with whitespace stripped from both sides — and adopts the plain
text's spacing. The font pass keeps the job it is good at (grouping runs into
lines, reporting size and weight) and stops doing a job already done.

**2. Empty bodies never merged.** `if b and len(b) < min_body_chars` meant a
section with a zero-length body — a cover-page line, a contents entry, a heading
whose text starts on the next page — skipped the merge step entirely. The one
case that most needed it. A body of zero characters is shorter than the floor and
belongs on the same side of the test as a body of ten.

**3. The review tool truncated the records it was asking about.**
`inspect_records.py` printed `text[:600]` with an ellipsis. On a corpus whose
median record is 529 characters that silently cut a third of every sample — and
because the cut always lands mid-sentence, the verdict it invited was "ends
mid-sentence". **Seven of twenty verdicts were for a defect the viewer
introduced.**

This is the worst of the three. A measuring instrument that manufactures the
defect it is measuring is worse than no instrument, because it produces a number
that looks like evidence. Fixed: records under 1,100 characters print whole,
longer ones print their beginning *and* their end with the omission stated.

---

## The baseline, and what it is a baseline of

Four numbers were produced this week. Only one of them is real.

| | sample | instrument | result |
| --- | --- | --- | --- |
| 20% | labels supplied by the TA | — | **not a measurement** — my judgement, not mine to claim |
| 10% | my labels, pre-spacing corpus | truncating viewer | superseded |
| 15% | seed 11 | truncating viewer | superseded |
| **25%** | **seed 11, same 20 records** | **whole records** | **the baseline** |

The corpus was identical (128 records) for the last two. **Ten points of the
baseline were the viewer, not the documents.**

The first number is the one to remember. When the TA handed over a table of
verdicts and I typed them in, the result measured the TA's judgement of my
corpus, not my corpus — and it read as a real measurement for two days. A
labelled set is only worth what the labeller's independence is worth.

**Baseline: 25% self-contained, 128 records, seed 11, whole-record display.**
Frozen. Week 5 improves on it or it does not.

---

## Also broken

- **`0 rejected`, four handbooks running.** Northside reports 2.
  `read_real_handbook` still skips empty-bodied sections before `validate()` sees
  them, so the drop count — the most direct fragmentation gauge there is — is
  thrown away. Cosmetic now that fragments are at 4.7%; still disconnected.
- **Numbered list items read as headings.** `13. Parents cheer; coaches coach...`
  becomes a section title in club-02. Diagnosed in the first review, still open,
  deliberately held for Week 5.
- **One malformed PDF.** club-01 throws three `Ignoring wrong pointing object`
  warnings — pypdf repairing a broken cross-reference table. It recovers, and the
  loop now catches per-file failures so one bad document cannot stop the rest.
- **Git Bash does not flush `input()` prompts.** Prompts arrived after the
  answer. Fixed by writing the prompt and flushing before reading.

---

## Carried into Week 5

1. **Column detection** — cluster runs by x before grouping by y. 90 minutes.
   *Kill criterion, written before starting: if club-01 does not clear 40%
   self-contained afterwards, it comes out of the corpus and the reason gets
   documented.*
2. club-02's 7 slabs — merge below a floor, split above a ceiling
3. Numbered list items read as headings
4. The swallowed rejection count
5. From Week 3: `POST /infer` with a typed schema, and the Gradio tab
6. `pipelines_bench.py` is written, committed, and has never been run

---

## On the plan

Week 4 as written asks for a 30-item labelled eval set. Building it on Northside
would have meant discarding it the moment real documents arrived — the same
coupling that made the Week 3 fee fix invisible to its own eval. The corpus went
first instead. The eval set is worth building in Week 5, on documents that are
now known to be real and known to be flawed.

---

## What I would do differently

_your turn — two or three sentences_

## Next

_what you are watching for in Week 5_
