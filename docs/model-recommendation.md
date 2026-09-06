# Model recommendation — Huskies AI club assistant

**Date:** Week 3 · **Author:** Gisell Tavarez · **Status:** decided

---

## Decision

Use **`llama3.2:latest`** for the club document assistant through Week 10.

Revisit after the corpus is replaced with a real club's documents, or if median
latency above 2.5 s turns out to matter to a user — neither is settled yet.

---

## The problem this model has to solve

A parent asks a youth sports club a question that is already answered in the
club's handbook, FAQ or announcements. A coordinator answers it by hand, in
August, for the twentieth time.

The assistant has to answer from those documents, cite where it got the answer,
and — the part that decides whether a club can use it at all — **say plainly when
the documents do not cover the question** instead of inventing something
plausible.

The answers most often concern money, dates and safety, so a confident wrong
answer is worse than no answer.

---

## What was measured

Nine cases against a 21-record corpus (7 FAQ, 11 handbook, 3 announcement), run
on this laptop through Ollama at temperature 0, seed 7.

- **6 grounded cases** — the answer is in the corpus, and a short list of
  documents is supplied, most of which are near misses. Correct means the
  required fact appears in the answer.
- **3 refusal cases** — the corpus does not answer the question. Correct means
  refusing. One of the three is a trap: it asks for a U19 fee and supplies every
  neighbouring age band, none of which is U19.
- **Latency** — median wall-clock seconds per call, after a warm-up.

Published benchmarks were not used. None of them measures this task.

---

## Results

| model | size GB | grounded | refusal | median s | tok/s |
|---|---|---|---|---|---|
| llama3.2:1b | 1.32 | 0/6 | 3/3 | ~1.5 | 6.1 |
| **llama3.2:latest** | **2.02** | **5/6** | **3/3** | **~3.0** | **4.4** |
| qwen2.5:0.5b | 0.40 | 6/6 | 0/3 | ~1.0 | 23.2 |
| qwen2.5:1.5b | 0.99 | 5/6 | 3/3 | ~1.85 | 12.5 |

Latency is written as a range because it is not reproducible: across three runs
the same model varied by 10-20%, while every accuracy score was identical. Treat
the timings as approximate and the scores as exact.

`llama3.2:latest` and `qwen2.5:1.5b` both score **8 of 9**. The table does not
separate them. What they got wrong does.

---

## The tiebreaker

Both models missed exactly one case: *"What is the season fee for a U11 player?"*

- **`llama3.2:latest`** answered *"That is not covered in the club documents."*
- **`qwen2.5:1.5b`** answered *"The season fee for a U11 player is £120."*

£120 is the **U7–U9** fee. The correct band is U10–U12 at £150.

Neither model got it right, and I am choosing the one that got it wrong *safely*.
A parent who is told the price is not in the documents asks a human. A parent who
is told £120 pays £120 and finds out in September. In this domain a refusal is a
recoverable failure and a confident wrong number is not.

`qwen2.5:1.5b` is half the size and roughly 1.6x faster. That is a real
advantage — comfortably larger than the run-to-run variance — and it does not
outweigh the above.

---

## What was rejected, and why

**`llama3.2:1b` — rejected.** Scored 3/3 on refusal by refusing all nine
questions, including the six it was handed the answers to. A perfect score on one
metric, achieved by being useless. Kept in the table deliberately as a reminder
that a single number can be gamed.

**`qwen2.5:0.5b` — rejected.** The only model to score 6/6 on grounded answers,
and the only one that invents facts when handed nothing: it produced a training
time of *"9:00 AM to 11:00 AM"* and a U19 fee of *£195* out of documents
containing neither. Fastest of the four by a wide margin. Not usable for anything
a parent reads.

**`qwen2.5:1.5b` — rejected, narrowly, and worth revisiting.** Tied on score,
faster, smaller. Rejected only on the direction of its single failure. If a
future eval shows it refusing rather than guessing on price questions, this
decision should be reopened.

---

## Known limits of this test

Stated so that nobody, including me, reads more into the numbers than they carry.

1. **The U11 case tests two things at once.** "U11" appears nowhere in the
   corpus; answering it requires inferring that 11 falls inside U10–U12. That is
   reasoning, not retrieval, and a case that mixes both cannot say which one
   broke. It should be split into a retrieval case ("What is the U10–U12 fee?")
   and a reasoning case ("What does it cost for an 11-year-old?").

2. **Retrieval is hardcoded.** Each case names the documents to supply. When the
   fee table was split into per-band records earlier today, every fee case
   silently began testing a document that no longer held the answer, and the
   scores did not move. An eval coupled to chunking decisions goes stale the
   moment chunking changes. Week 5 replaces this with real retrieval.

3. **Refusal is detected by substring matching**, which has now failed three
   separate times on honest paraphrases — most recently *"not explicitly
   mentioned in the provided documents"*, which the matcher missed because of the
   word *explicitly*. `qwen2.5:0.5b`'s true refusal score is 1/3, not 0/3. Adding
   more phrases is not the fix; Week 6 replaces the matcher with a model judge.

4. **Latency was measured once per model per run and moves.** Three runs of the
   identical benchmark gave `llama3.2:latest` 2.89 s, 3.19 s and a median around
   3.0 s, and `llama3.2:1b` moved 19% between two runs. Accuracy on this stack
   has no noise floor; timing has one of roughly 10-20%. Any latency claim
   smaller than that is not a finding. Take a median of several runs before
   quoting a number to anyone.

5. **Nine cases is a small sample** on a 21-record invented corpus. This is
   enough to reject two models confidently. It is not enough to claim a
   percentage.

---

## What this recommendation does not cover

- **License terms** — not yet checked for any of the four. Must be settled before
  anything is delivered to a paying client. _[TODO: fill in]_
- **Context window** — not measured; matters from Week 5, when retrieved chunks
  start competing for room. _[TODO: fill in]_
- **Hosted models** — the whole comparison is local. A hosted model would almost
  certainly beat all four on quality and would introduce a per-question cost and
  a dependency on somebody else's uptime.
- **Whether latency matters** — 2.89 s versus 1.91 s has not been tested on a
  real user. It may be irrelevant, or it may be the whole thing.

---

## Revisit this when

- The corpus is replaced with a real club's documents (Week 3 weekend / Week 5)
- The eval set reaches 25 verified questions (Week 6)
- Retrieval stops being hardcoded (Week 5)
- Any of the four models ships a new version

Each of those invalidates the numbers above. The decision is only as current as
the evidence under it.
