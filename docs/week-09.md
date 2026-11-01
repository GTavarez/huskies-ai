# Week 9 — Proving absence, and why a parent's question cannot localise anything

## The job

The must-refuse set has gone 15 → 10 → 8 across three audits, every flip
justified by the source text and every one in the same direction. At eight rows
each is worth 12.5 points, which is coarser than any effect being measured, and
`8/8` reads as a perfect score on a set that has lost nearly half its rows.

So: more must-refuse questions. The problem is that a `refuse` label is a claim
that four handbooks **do not** answer something, and absence is the one thing a
ranked retriever cannot establish. It returns its best five records whether or
not an answer exists anywhere in the corpus.

Reading a failed top-5 as proof of absence is the mistake this repo has made
most often. It produced five mislabelled rows — q04, q21, q29 and two others —
and two false findings that reached the week notes:

| claimed | actually |
| --- | --- |
| no handbook addresses injuries | club-02 rule 14 says what to do |
| no concussion procedure anywhere | club-04 has a titled section, page 10 |

---

## The tool

`refuse_candidates.py` counts exact strings over the **full text** of all four
PDFs and prints every passage, with the verdict line left blank. It does not
rank. Table-of-contents lines are dropped: a contents entry proves a topic is
listed, not that a passage answers anything.

```
python refuse_candidates.py
python refuse_candidates.py --all-snippets --pad 400
```

Input is `docs/refuse-candidates.txt`, one question per line, with any word the
handbooks might use instead after a pipe. Output is `docs/refuse-sweep.md`,
gitignored because it quotes the handbooks.

### Two bugs in the sweep, both found by reading its own output

**`ein` matched ten times inside `being`.** Substring counting is not safe for
proving absence in either direction: it manufactures hits that send a reader to
check ten passages that say nothing. Fixed with word boundaries, asserted only
where the term's own edge is a word character, so `a.m.` and `501(c)` still
match as written.

**The boundary fix then turned `sister` into zero hits** in a handbook that says
"brothers and sisters". A plural the term list did not anticipate is still the
passage you need to read, so single alphabetic terms now match an optional
`(?:e?s)?`. Recall beats precision here — every hit gets read anyway, and a
false absence is the expensive error.

The second bug is the more instructive one. The fix for a false positive
created a false negative of exactly the kind the script exists to prevent, in
one line, and it was invisible until the counts were read side by side.

---

## What the sweep says before anything has been read

Twenty candidates: the eight rows already labelled `refuse`, then twelve new
ones. The existing eight come first because a wrong label already in the set
costs more than a missing row.

**Read these first — a specific term lands in one club:**

| candidate | what the sweep found |
| --- | --- |
| **q06** what do I do about a concussion | club-04: `concussion` ×14, `return to play` ×4, `cdc` ×2, `head injury` ×1 |
| **q25** what if I cannot afford the fees | club-04 `payment plan` ×1; club-01 and club-02 `scholarship` ×2 each |
| **q26** what time do games start | club-02 `game time` ×3 |
| play up an older age group | club-04 `play up` ×2, `playing up` ×2, `age group` ×4, `older` ×8 |
| athletic trainer at games | club-04 `athletic trainer` ×2, `trainer` ×3 |
| equal playing time | club-01 `playing time` ×4, `equal` ×3; club-04 `playing time` ×2, `fair play` ×1 |
| total cost for a full season | club-03 `additional costs` ×1 |
| referee pay | club-03 `stipend` ×2 |

**Thin — read to confirm, not to find:**

| candidate | |
| --- | --- |
| q10 refund if my child quits | `refund` 0, `withdraw` 0, `non-refundable` 0 anywhere; only `quit` ×3 in club-01 |
| q15 how many players on a team | `roster` ×1 in club-02 and club-04, nothing else |
| sibling discount | `sibling` 0, `discount` 0, `family rate` 0; `brother` ×1 and `sister` ×1 in club-01 |
| insurance carrier | `insurance` 0, `carrier` 0, `coverage` 0; `policy` ×3 in two clubs |
| 501(c)(3) | `non-profit` ×1 per club, `501` 0, `tax-exempt` 0 |
| how many games in a season | `number of games` 0, `game count` 0, `regular season` 0 |

A count is not a verdict and **zero is not a verdict either** — zero is only as
good as the term list, which is why the terms searched are printed above every
result. The sibling-discount row is the one to distrust: six words came back
clean, and the question is whether a seventh was missing.

### q06 is the live problem

q06 is labelled `refuse` with the note *"no passage in the four handbooks
answers this"*. `claim_audit.py` already found a titled concussion section in
club-04 with a CDC-derived form, and this sweep finds `concussion` ×14 in the
same handbook. The note has been false in the repo for two weeks while q06 sat
inside the eight rows the **8/8** is scored against.

That is the second time a `claim_audit.py` finding failed to propagate into the
question set. The audit scripts are not wired to each other, and nothing
notices when one contradicts a label the other depends on.

---

## The finding: a parent's question is made of the handbook's most common words

The sweep prints, per candidate, the terms too common to localise anything.
Across the twenty candidates that list is the same handful every time —
`game` ×258, `player` ×248, `parent` ×246, `coach` ×240, `child` ×206,
`players` ×174, `club` ×110.

Those are not incidental. They are the words the questions are made of. Terms
derived mechanically from the question text were compared against terms added
by hand as domain synonyms:

| | question's own words | hand-added synonyms |
| --- | --- | --- |
| terms | 50 | 114 |
| **median frequency across the corpus** | **54** | **0** |
| too common to localise (>40 hits) | 26 (52%) | 4 (3%) |
| absent from all four handbooks | 2 (4%) | 65 (57%) |

**The median word in a parent's question appears 54 times across the corpus.
The median hand-added synonym appears zero times.**

This is a mechanism for the result the whole project rests on. BM25 scores a
passage by overlap with the query. If the query's vocabulary has median
frequency 54 in a four-handbook corpus, then *every* passage overlaps it, the
score is computed almost entirely on words that are uniformly present, and it
cannot distinguish a passage that answers from a passage that merely discusses
the same subject. The words that would distinguish — `concussion`, `stipend`,
`payment plan`, `sibling`, `non-refundable` — are exactly the ones a parent does
not use, because a parent asking about money says "much" and "fees", not
"non-refundable".

That is why the worst unanswerable question outscores the weakest genuine hit by
four times, on every ranker, in both question sets. Not noise, and not a
threshold waiting to be tuned: the query and the corpus share their common
vocabulary and differ only in their rare one.

**Caveat, and it matters.** The hand-added terms were written *in order to be*
rare and specific, so the 57%-absent figure is partly selection — it measures
how I chose synonyms as much as the corpus. The left column is not: those fifty
terms come out of the question text by a stop-list and nothing else, and their
median frequency of 54 stands on its own.

**What it implies for the demo**, where the same guards run on practice
websites: a patient asking "do you take my insurance" is using that site's most
common words too. Lexical relevance was already measured as a paraphrase
penalty on coherent chunks in Week 8. This says why — the filter is applied to
the half of the vocabulary that carries no information.

---

## Making the sweep readable, and a bug in how it quoted

The first full sweep was 2,265 lines for twenty candidates, and the worst
single candidate ran to 329. That is not a volume problem, it is a duplication
bug.

`snippets()` took one window per *term*: 260 characters either side of the hit,
deduplicated on the first 60 characters of the window. `brother` and `sister`
occur in the same sentence of club-01, so the window started at a different
offset each time, the dedup key differed, and that one sentence printed twice
with 260 characters of unrelated referee advice on each side.

It now takes **the sentence containing the hit, once, with the terms that
matched it** — one line in the worksheet where there were two long ones:

```
> <the one sentence in club-01 that mentions siblings, which turns out to be
>  about referees being related to players>
>
> — matched `brother`, `sister`
```

That example is paraphrased rather than quoted, and not by choice: the first
draft of this section pasted the real sentence in, and `tools/leak_check.py`
blocked it. The checker caught its own author adding a leak to the week note
describing the leak audit — which is the argument for having it run on every
commit rather than at the end of a cleanup.

| | before | after |
| --- | --- | --- |
| whole sweep | 2,265 lines | **2,004** |
| worst candidate | 329 lines | **155** |

A sentence with no sentence-ending punctuation in it — a glued run — falls back
to a window centred on the hit, so the glued records do not swallow a screen.

The reason this matters beyond tidiness: a worksheet nobody can read does not
get read, and the verdicts are the whole point of the exercise.

---

## The anonymisation audit, done the right way round

`club-01` … `club-04` are the labels used everywhere. Checking they actually
anonymise anything was done twice, and only the second attempt was a test.

**First attempt: search for the names I had seen.** Whatcom County Select,
North Puget Sound League, Phillips 66 Fields — names that had appeared in
output I happened to look at. That is the same error as concluding a question
is unanswerable because a ranked search missed it: it can only find what
already surfaced.

It would have missed club-02 completely. Its page footer carries its own name
on every page, and that name only came to light because the readability fix
printed a sentence that happened to include a footer.

**Second attempt: derive the names from the source.** A pattern for
capitalised sequences ending in `Soccer Club`, `Youth Soccer`, `League`,
`Association`, `Select`, `Sportsplex`, `FC` or `SC`, run over all four PDFs,
then every result checked against every tracked file and every commit.

| | |
| --- | --- |
| organisation names found in the four handbooks | **39** |
| of those appearing anywhere in the repo | **1** |
| that one | `US Youth Soccer` — a national governing body, in `week-06.md` |
| club or place names in tracked files | **0** |
| club or place names anywhere in history | **0** |

**The rule: to test whether something has leaked, enumerate from the source,
not from what you have noticed.** A deny-list built from memory tests your
memory. `docs/data-handling.md` has the rest of that story, including the three
checkers in this cleanup that reported success while failing.

---

## Predictions

The Week 8 scorecard was 2 of 6, every miss in the same direction: every change
was predicted to do more than it did. Correcting for that, these are
deliberately smaller than instinct says.

| | predicted |
| --- | --- |
| q06 drops | yes |
| further drops among the other seven | 1 |
| new candidates that survive, of 12 | 7 |
| must-refuse set after this round | 13 |
| refusal floor separates on any ranker | still no |
| **judge correct refusals** | **down from 8/8 — 10 to 12 of 13** |

The last one is the point of the exercise. `8/8` is a score on rows that were
inherited and are mostly easy; the new candidates are chosen for the shape that
breaks retrieval, which is the shape that should break a judge too. **A refusal
metric that stays perfect after the set doubles has not been tested, it has
been diluted.** If it holds at 13/13 the questions were not hard enough.

---

## Verdicts

_One line per candidate: KEEP (the handbooks genuinely do not answer it) or
DROP (they do), the club, and the sentence that decided it. Written after
reading the passages in `docs/refuse-sweep.md`, not from the counts above._

| candidate | verdict | club | the sentence that decided it |
| --- | --- | --- | --- |
| q06 concussion | | | |
| q10 refund on quitting | | | |
| q15 players on a team | | | |
| q17 practice frequency | | | |
| q25 cannot afford fees | | | |
| q26 game start times | | | |
| q35 watch practice | | | |
| q37 parent meeting | | | |
| insurance carrier | | | |
| referee pay | | | |
| 501(c)(3) | | | |
| sibling discount | | | |
| play up an age group | | | |
| transportation to away games | | | |
| lost or damaged uniform | | | |
| equal playing time | | | |
| complaint about a coach | | | |
| athletic trainer at games | | | |
| total cost for a season | | | |
| games in a season | | | |

---

## Carried forward

1. **Fill in the verdict table above**, then write the KEEPs into
   `data/questions-real.jsonl` as `expect: refuse` rows and re-run every eval.
   Restate `8/8` in `week-08.md` and the README against the new set
2. **Wire the audits together.** q06 shows a `claim_audit.py` finding can
   contradict a label for two weeks with nothing noticing. A check that every
   `refuse` row's note survives a sweep would have caught it the day it broke
3. **A completeness measure** — still open from Week 8. An answer can be 100%
   grounded and not answer the question
4. **Weight the question set** — embeddings 27/32 against hybrid 26/32 is one
   row, and every row is worth the same 1/32
5. From Week 3: `POST /infer` with a typed schema, the Gradio tab,
   `pipelines_bench.py` still never run
