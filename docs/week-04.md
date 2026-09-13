# Week 4 — Real documents

## The finding

Four weeks of ingestion work looked finished. It was finished against a corpus I
did not write and could not fail.

Thirty minutes against four real club handbooks, downloaded from four club
websites, produced a **20% self-contained rate**. Northside scores near 100% on
the identical test, because it was built clean on purpose.

That gap — 100% on the fixture, 20% on reality — is the result of the week.

---

## Measured — what came out

Four handbooks: 609 KB, 279 KB, 99 KB, 386 KB. All four were parsed by the font
pass; none needed the text-heuristic fallback. **239 records.**

| source | records | median chars | shortest | longest | under 100 | over 2000 |
| --- | --- | --- | --- | --- | --- | --- |
| club-01.pdf | 67 | 210 | 8 | 1,454 | 15 | 0 |
| club-02.pdf | 117 | 242 | 12 | 5,906 | 31 | 3 |
| club-03.pdf | 31 | 381 | 44 | 1,478 | 9 | 0 |
| club-04.pdf | 24 | 682 | 112 | 3,982 | 0 | 3 |
| **Northside** | **21** | ~300 | 121 | ~800 | **0** | **0** |

**55 of 239 records — 23% — are under 100 characters.** Six are over 2,000.
Northside has none of either.

Counting fragments and rating them disagree about which document is worst:

| | under 100 | rate |
| --- | --- | --- |
| club-01 | 15 of 67 | 22% |
| club-02 | 31 of 117 | 26% |
| club-03 | 9 of 31 | **29%** |
| club-04 | 0 of 24 | 0% |

By count club-02 is worst; by rate club-03 is. The rate is the one that
describes the document rather than its length.

**club-02 is the genuinely hard case** — 31 records under 100 chars *and* 3 over
2,000, median 242, longest 5,906. It fragments and merges inside the same
document. A splitter that is consistently wrong can be tuned; one that is wrong
in both directions cannot, because no single threshold satisfies both.

**club-04 is the easy case** — zero fragments, consistent under-segmentation,
three slabs. A secondary split on paragraph boundaries would largely fix it.

---

## Measured — the record review

Ten records sampled at a fixed seed and judged by hand against one question:
*would this answer a parent's question on its own?*

| verdict | count |
| --- | --- |
| self-contained | 2 |
| partial | 2 |
| not usable | 6 |

**20% self-contained.** This is the Week 5 baseline: measured before any fix, on
documents I did not write, with the sample seeded so it can be repeated exactly.

A first pass at this review marked 10 of 10 as self-contained. That was wrong —
the records include a table-of-contents dot-leader line, a publisher credit, and
three sentences cut in half. The correction matters more than the original
number: labelling drifts under fatigue, which is exactly why the Week 5 rule is
to label before seeing results and audit cold 48 hours later.

---

## Three bugs, diagnosed from the review

| what the record looked like | records | cause |
| --- | --- | --- |
| sentence cut in half · starts and ends mid-sentence · text starts with a comma | 3 | **bold is not a heading** |
| contents dot-leader · publisher credit and page number | 2 | furniture filter too narrow |
| one rule, the rest elsewhere · promises rules, does not include them | 2 | numbered list items read as headings |

**1. Bold is used for emphasis, not only for structure.** `split_sections_by_font`
starts a new section at any bold run. Real handbooks bold phrases inside running
text — *"**Encourage your child**, regardless of..."* — so an emphasis becomes a
section boundary, the sentence is sawn in half, and the bolded fragment is
promoted to a title. Fix: a bold run only starts a section if it is on its own
line and the previous run ended with sentence-final punctuation.

**2. The furniture filter is too specific.** It catches `Page 3` but not
`The Maine Center for Sport and Coaching ... Page 7`, and not a row of dot
leaders. Fix: match a page marker anywhere in the line, and reject lines that are
mostly punctuation.

**3. Numbered list items match the numbered-heading pattern.** `1.` `2.` `9.`
`12.` inside a list of ground rules each start a new section, orphaning the
sentence that introduced them. Fix: require a numbered heading to be followed by
a capitalised phrase rather than a sentence continuation.

Three fixes account for roughly eight of the ten reviewed records. That is the
Week 5 chunking backlog, written from evidence rather than guesswork.

---

## What broke

- **Text runs joined with spaces.** `lines_with_font` treats every text-showing
  operator as a separate run and joins with a space. PDFs split single words
  across operators for kerning and pack several words into one, so the output
  contains both `an d body` and `thereferees`. Present in more than half the
  sampled records, including both that passed. Fix: use the font pass only to
  identify heading strings, then split the plain `extract_text()` output on them.
- **Rejections were being swallowed.** `read_real_handbook` skipped sections with
  empty bodies before `validate()` saw them, so four real handbooks reported
  `0 rejected` while Northside reports 2. The drop count is a direct measure of
  fragmentation and it was being thrown away.
- **One malformed PDF.** club-01 produced three `Ignoring wrong pointing object`
  warnings — pypdf repairing a broken cross-reference table. It recovered, but
  real PDFs are not well-formed and the loop now catches per-file failures so one
  bad document cannot stop the other three.
- **Git Bash does not flush `input()` prompts.** Prompts arrived after the answer
  and keystrokes landed in the wrong place. Fixed by writing the prompt and
  flushing before reading.

---

## Still open

- The three splitter fixes — deliberately left for Week 5, which is the chunking week
- The text-run joining bug
- `POST /infer` with a typed schema, and the Gradio tab, from Week 3
- Weekday B: `pipelines_bench.py` is written and has not been run
- The tracker is now out of step with what actually happened this week

---

## On the plan

Week 4 as written asks for a 30-item labelled eval set. Building it on Northside
would have meant throwing it away the moment real documents arrived — the same
coupling that made the Week 3 fee fix invisible to its own eval. The corpus went
first instead.

---

## What I would do differently

_your turn — two or three sentences_

## Next

_what you are watching for in Week 5_
