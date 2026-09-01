# Week 2 — Data and dialogue

## What this week was for

Week 1 proved the model behaves the same way twice. Week 2 was about the two
things that sit either side of it: the documents going in, and the conversation
wrapped around it.

## Measured — ingestion

| What                                | Value                                              |
| ----------------------------------- | -------------------------------------------------- |
| Source formats                      | 3 — CSV, nested JSON, PDF                          |
| Records produced                    | **17 valid**, 2 rejected                           |
| By source type                      | faq 7 · handbook 7 · announcement 3                |
| Mean text length                    | 323 characters                                     |
| Longest record                      | `handbook-s4` (783 chars)                          |
| Shortest record                     | `faq-F002` (121 chars)                             |
| Page furniture leaked into text     | **0 lines**                                        |
| Sections split across a page break  | 0 — section 4 survived intact                      |

The two rejections were both correct rejections: an FAQ row whose answer was
blank, and an announcement whose body was empty so its text repeated its title.
Neither is retrievable content. Both would have embedded into meaningless vector
space in Week 5 and quietly degraded every search after that.

## Measured — the chat loop

| What                          | Value                                             |
| ----------------------------- | ------------------------------------------------- |
| Token budget                  | 600                                               |
| History after one exchange    | 78 tokens across 3 messages                       |
| Turns before the budget bit   | _fill in — how many exchanges until trim fired?_  |
| What `trim()` dropped first   | _fill in — check `/history` right after a trim_   |

## Measured — temperature sweep

_Run `python temp_sweep.py`, then fill this in from `out/temp_sweep.csv`._

| Prompt | t=0.0 | t=0.3 | t=0.6 | t=0.9 | t=1.2 |
| ------ | --------- | --------- | --------- | --------- | --------- |
| open — unique / similarity   | 1 / 1.000 | 3 / 0.961 | 5 / 0.941 | 6 / 0.784 | 6 / 0.605 |
| closed — unique / similarity | 1 / 1.000 | 1 / 1.000 | 2 / 0.952 | 2 / 0.952 | 2 / 0.952 |

Temperature at which the closed prompt first returned a **wrong** answer:
**never — it held to 1.2.** The only variation across the entire sweep was a
trailing full stop: `7pm` vs `7pm.` The answer was in the prompt, so the
probability mass on the right token was too concentrated for sampling noise to
dislodge. A closed prompt is a grounded prompt in miniature, and this is the
mechanism grounding buys.

Two things this measurement corrected:

- The prediction was that the closed prompt would eventually break. It did not,
  at least not by 1.2. Measure, then conclude.
- `unique` counted 2 answers when the only difference was punctuation. The
  metric is more sensitive than the meaning — normalise before counting, or it
  will alarm on nothing.

Open-prompt lengths spread from 102 ±0 characters at t=0 to 109 ±14 at t=1.2,
and every sample at 1.2 was still a perfectly sendable message. Temperature
bought variety on the open task at no cost to quality. That is what it is for.

## Measured — two models compared

_Run `python compare_models.py`, then write three sentences on what differed._

- A: `llama3.2:latest`
- B: `qwen2.5:0.5b`

Both are instruction-tuned, so this measured **capability**, not base-vs-instruct
— both obeyed the "number them 1 to 3 and write nothing else" format rule.
Asked what time practice starts, A declined and B answered "8:00 AM", a fact
nobody had given it.

1.
2.
3.

## What broke

- PowerShell does not have `source`; the activation there is
  `.venv\Scripts\Activate.ps1`. Switched to the bash terminal inside VS Code.
- Python typed at a PowerShell prompt, and PowerShell typed at a `>>>` prompt.
  Both produce confusing errors that have nothing to do with the code.
- The raw PDF extraction put the running header and footer *first*, before the
  body text — extraction order is drawing order, not reading order.
- Splitting the handbook by page would have cut section 4 in half. Splitting on
  numbered headings was the fix.

## Grounding — a preview of Weeks 4-5

Ran `grounding_demo.py`: four questions, each asked bare and then with the
matching record pasted in. Retrieval was hand-written, which is the one piece
Weeks 4-5 exist to replace.

| What | Result |
| ---- | ------ |
| Extra prompt tokens for grounding | 423 across 4 questions (~106 each), on every call |
| Grounded answers | shorter, and carried specifics no model could guess (31 August; no fitness trackers) |
| Refusal guard on the uncovered question | held for both models |

Three findings worth keeping:

1. Ungrounded, `llama3.2` answered the lightning question with *"According to
   our club's safety policy, 30 minutes"* — the right number attached to a
   **fabricated citation**. It had never seen the policy. A right answer from a
   process that checks nothing will be wrong eventually, with no warning.
2. Asked what time training is tomorrow, `chat.py` said "I don't have that
   information" and `grounding_demo.py` said "5:30 PM" — same model, same
   temperature, same seed. The only difference is one sentence in the system
   prompt: *"If you do not know something specific to this club, say so rather
   than guessing."* That sentence looks like boilerplate and is not.
3. `qwen2.5:0.5b` refused correctly on the question `llama3.2` invented an
   answer for. Bigger is not reliably safer per question. Hence evals in Week 6.

Also found a prompt-leak bug: the small model emitted the refusal sentence and
then kept copying the system prompt behind it. Fixed by moving the literal
string it must output to the very end, with nothing behind it to leak.

## The gap this week opened

The chat loop answers "what time is training tomorrow?" with *I don't have that
information about this club* — while `data/records.jsonl` sits on disk holding
17 records that contain the answer. Nothing connects them yet.

That gap is the entire point of Weeks 4 and 5.

## What I would do differently

_your turn — two or three sentences_

## Next

_what you are watching for in Week 3_
