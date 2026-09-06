# Corpus manifest

**Status:** 🟡 **NOT FROZEN** — dry run on the placeholder corpus.
Freezes when a real club's documents replace these.

---

## The rule this document exists to enforce

Every document listed here has to pass one test:

> **Can I verify the correct answer myself, without asking anyone?**

If the answer is no, the document comes out. Not because it is bad, but because
an unverifiable document cannot appear in an evaluation set — and a document that
cannot appear in the eval set cannot support any claim made in Week 6. It can
only quietly make the scores wrong.

Deleting is the point of this exercise. A manifest where nothing was removed
usually means the question was not asked seriously.

---

## Contents

Regenerate this table with `python corpus_stats.py`, then fill the last two
columns by hand.

| source file          | type         | pages | records | tokens   | verifiable? | owner |
| -------------------- | ------------ | ----- | ------- | -------- | ----------- | ----- |
| `announcements.json` | announcement | — | 3 | 160 | yes — invented, source in `data/raw/` | me |
| `faq_export.csv` | faq | — | 7 | 233 | yes — invented, source in `data/raw/` | me |
| `handbook_2026.pdf` | handbook | 3 | 11 | 730 | yes — invented, source in `data/raw/` | me |
| **total** | | **3** | **21** | **1,123** | | |

Counted with tiktoken `cl100k_base`, not estimated. For the record, the Week 1
ratio of 1.17 tokens per word predicted 1,083 against an actual 1,123 — low by
3.7%. Close enough for back-of-envelope work, not close enough to freeze a
corpus on.

**Rejected at ingestion:** 2 records — `faq-F006` (blank answer) and
`ann-A-2026-016` (body repeated the title). Both correctly rejected; neither is
retrievable content.

---

## Shape of the corpus

|                            |                                |
| -------------------------- | ------------------------------ |
| Records                    | 21                             |
| Mean record | 53 tokens |
| Longest record | `handbook-s4`, Code of Conduct — 137 tokens |
| Whole corpus in one prompt | 1,123 tokens |
| Retrieving 4 records | 214 tokens |
| Ratio | 5.2x |

That ratio is unimpressive because this corpus is a toy. A real 40-page club
handbook runs to roughly 26,000 tokens, and the same comparison stops being a
rounding error and becomes the reason retrieval exists at all. Re-run
`corpus_stats.py` after the swap and record the new number here — it is the
sentence that will settle the "why not just use a bigger context window"
question, with your figures rather than someone else's.

---

## The seven-section skeleton

The handbook parsed into seven sections, and they are not arbitrary. They are
what every youth club writes down, because they are what parents ask about:

1. Registration and eligibility
2. Subscriptions and fees
3. Kit and equipment
4. Code of conduct
5. Away travel
6. Adverse weather
7. Injury and return to play

This is a template, not just a corpus. A second club swaps the contents and keeps
the shape, the eval questions, the chunking decisions and the refusal guard.
Track how long the second one takes — if it is more than four hours, the template
did not hold.

---

## Structural decisions already made

Recorded here because Week 5 depends on them and they are easy to forget.

- **The fee table is not prose.** Each age band became its own self-contained
  record (`handbook-s2-u10-u12` and so on), naming its own band inside its own
  text. Left flattened, two of four models pulled the wrong row and quoted the
  wrong price.
- **Page furniture is stripped** — running headers and footers never reach the
  records.
- **Sections are split on numbered headings, not pages**, because section 4
  crosses a page break.
- **A record whose text only repeats its title is rejected**, not stored.

---

## When real documents arrive

1. Put them in `data/raw/`. Do not delete the Northside files — they stay as the
   regression fixture, so a change to `ingest.py` can be checked against a known
   result.
2. Run `ingest.py`, then `corpus_stats.py`, and replace the table above.
3. Ask the verification question for each document, and delete what fails.
4. Re-run `bench_models.py`. The model recommendation was made on invented
   documents and does not automatically survive the swap.
5. Change the status line at the top to **FROZEN**, with the date.
6. After that, adding or removing a document is a deliberate act that gets a line
   in the changelog below — not a quiet edit.

---

## Changelog

| date   | change                                            | why                                                                   |
| ------ | ------------------------------------------------- | --------------------------------------------------------------------- |
| Week 3 | Fee table split into 4 per-band records (17 → 21) | Flattened table caused two models to quote the wrong age band's price |
| Week 3 | Manifest created, dry run on placeholder corpus   | Format ready to receive real documents                                |

---

**Frozen by:** _(name and date, when it is real)_
