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

## Prompt v1 vs v2 — a trade, and a metric that hid half of it

V1 refused four questions whose answer was in the context it was handed. The fix
looked obvious: the prompt's two prohibitions, `Do not use general knowledge`
and `Do not guess`, read to a 3B model as *decline unless certain*. V2 keeps the
same constraint but changes the shape — search instruction first and positive,
the prohibition narrowed to importing outside facts, and refusal gated behind a
test the model can apply (*nothing in the documents touches the question*)
rather than a confidence level it cannot calibrate.

Run both, keep both files, compare the sets:

| | v1 | v2 |
| --- | --- | --- |
| correct refusals | **9/15** | 4/15 |
| answered, grounded | 20/25 | **23/25** |
| over-refused | 4 | **1** |
| mangled refusals | 0 | 0 |
| **fabricated on an unanswerable question** | **0** | **2** |

| | |
| --- | --- |
| FIXED | q09 yell at the referee · q11 play up an age group · q28 is there a tryout |
| BROKE | q04 injured during a game · q06 concussion · q17 practice schedule · q25 cannot afford fees · q26 what time do games start |

Fixed 3, broke 5, net −2. All three fixes are over-refusals the change was aimed
at, so the mechanism worked exactly as intended. It just cost five.

### The row that decides it

> **What happens if my child is injured during a game?**
> *"If your child is injured during a game, you should ask the referee if you
> may enter the field to assist your child."*

> **RETRACTED, 2026-10-25.** The paragraph below was wrong, and it is left here
> rather than deleted because the mistake is more instructive than the
> conclusion was. club-02's parent rules, item 14, say verbatim: *"If during a
> game your child is injured, **ask the referee if you may enter the field and
> assist your child**."* The model did not invent an injury procedure. It
> quoted one, almost word for word. The row was labelled `refuse`, the judge
> called a near-quote UNSUPPORTED, and I built a conclusion on top of both
> without checking the source — two messages after flagging those very labels
> as unreliable. The "Ship v1" verdict below rested entirely on this row and
> does not survive it.

~~No handbook says that. The model invented an injury procedure and addressed it
to a parent. Week 6 already recorded that **no handbook tells a parent what to
do about a concussion** — four clubs, zero procedures — so this is the one
subject area where the corpus is known to be empty and a confident answer is
guaranteed to be fabricated.~~

~~That single row settles the prompt question regardless of the other numbers.
Three extra grounded answers do not buy a fabricated injury instruction.~~

~~**Ship v1.** The over-refusals stay in, as a known defect with a named cost.~~

**No verdict on v1 vs v2.** Both runs were scored against a must-refuse set
containing five wrong labels, so the comparison measured the labels as much as
the prompts. It has to be re-run against the audited set before it means
anything.

The lesson that does survive: **the corpus was not empty where I assumed it was
empty.** Week 6 found no concussion procedure in any handbook and I generalised
that to injuries, which is a different question with a different answer. One
exact-string search over the PDFs would have settled it in seconds, and that
search is now built into `audit_questions.py` as the `t` option, because the
same mistake had already set five labels wrong.

### The metric could not see it

```python
made_up = [r for r in ans if r["verdict"] == "UNSUPPORTED"]
```

`ans` is answerable rows only. An `UNSUPPORTED` verdict on a **must-refuse** row
— the model fabricating an answer to a question the documents cannot answer, the
worst cell in the matrix — was filtered out before being counted. So the run
that invented the injury procedure printed:

```
INVENTED           0
```

The prediction written down before the run said *invented 0 → 1 or 2*. It landed
on 2. The instrument reported it as 0.

This is the same defect as the denominator error earlier in this file, wearing
different clothes: **a metric that silently excludes its own worst outcome, and
keeps printing a clean number.** Not a crash, not a warning — a quotable zero.
Fixed in `judge.py` and `judge_diff.py`; fabrications are now counted on every
row and the unanswerable ones are broken out separately, because they are a
different severity and averaging them away is how the zero happened.

### Prediction scorecard — 3 of 4

| predicted | actual | |
| --- | --- | --- |
| over-refused 4 → 0 or 1 | 1 | right |
| correct refusals 9 → 6 or 7 | **4** | wrong — the cost was 5, not 2–3 |
| invented 0 → 1 or 2 | 2 | right, and the metric said 0 |
| net a wash or worse | −2 | right |

The miss is the informative one. The refusal half of the question set is far more
sensitive to prompt wording than the answering half — five refusals lost against
three answers gained, from one rewritten paragraph.

### What this actually proves: one prompt cannot serve both halves

V2 is not a worse prompt. It is better on everything the answering half measures
and worse on everything the refusing half measures, and both directions moved
from a single edit. That is not a wording problem to be tuned away; a prompt has
one setting and the question set has two populations.

The build it points at is **routing**: decide first whether the corpus plausibly
covers the question, then answer with the permissive prompt when it does and the
strict one when it does not. The expensive part already exists — the model judge
reads the retrieved context and gets 9/15 on precisely that call, where every
score threshold got 0/15. It is currently wired after the answer, grading it.
Wiring it before the answer, as a gate, uses the one thing in this project that
demonstrably works for the one decision that keeps going wrong.

---

## Routing, tried and killed in one run

Prompt v1 and v2 are better than each other on opposite halves of the question
set, so the next idea was to stop choosing: gate each question first — does the
retrieved context contain the answer? — then send COVERED questions to the
permissive prompt and emit the refusal sentence directly for MISSING, with no
generation step at all and therefore no path to a fabricated answer.

`llama3.2:1b` as the gate, scored against whether the answer was actually in the
retrieved context:

| | correct |
| --- | --- |
| the gate | **13/40** |
| constant "MISSING" | **21/40** |
| constant "COVERED" | 19/40 |
| the gate, counting only the 27 rows it answered in the required format | 13/27 |

**A constant beats it.** Not by a little — by eight questions. And the
conditional rates say why:

| | |
| --- | --- |
| says COVERED when the answer IS in context | 3/19 (16%) |
| says COVERED when the answer is NOT in context | 4/21 (19%) |

It says COVERED marginally *more often* when the answer is absent. The output is
statistically independent of the property it exists to detect. This is not a
weak signal to be strengthened with a better prompt; there is no signal. On top
of that, 13 of 40 responses contained neither COVERED nor MISSING — a 1B model
asked for one word, given five records of context, returned prose a third of the
time.

### The trap this run walked into, with the numbers to prove it

| | v1 | v1 + gate |
| --- | --- | --- |
| **correct refusals** | 9/15 | **13/15** |
| answered, grounded | 20/25 | **9/25** |
| over-refused | 4 | **11** |
| invented | 0 | 1 |

**13/15 is the best refusal number this project has produced, and it came from
the worst system in it.** The gate found the degenerate solution: refuse almost
everything. The refusal metric cannot tell that apart from competence, because
refusing is scored as correct on every must-refuse row and the cost lands in a
different row of the table.

Week 5 wrote the warning for the opposite case — *"a system that answers
everything scores perfectly on answer rate and is unshippable"* — and this is
its mirror image, arriving with a headline figure good enough to ship on if
nobody read the second line. The guard against it is not a better metric. It is
the rule that **no single number from this eval is allowed to decide anything**,
which is also why `judge_diff.py` prints FIXED and BROKE above the totals.

### Why this result is trustworthy when most of this week's are not

Gate accuracy is scored against `retrieved` — computed from the verbatim answer
keys and the retrieval run, with no model's opinion anywhere in it. It does not
depend on the must-refuse labels (four of which are known wrong) and it does not
depend on the 1.5B judge (which has never been hand-audited).

Of everything measured this week, **this is the only number independent of both
soft foundations**, which is why routing can be called dead on one run while the
prompt comparison cannot be called settled on two.

### The diff tool is scoring against labels we know are wrong

`judge_diff.py` reported FIXED (6) for v1 -> v2+gate, and two of those six are
q18 *How are the teams created?* and q19 *How big is the time commitment?* —
both of which the handbooks **do** answer (club-03 has `HOW ARE TEAMS ORGANIZED
AND FORMED?` and `WHAT IS THE TIME COMMITMENT?`). They are labelled `refuse`
from the audit's over-correction phase. So the tool recorded "fixed" for a
system that started wrongly refusing answerable questions.

Nothing is wrong with the tool. The labels are wrong, and a comparison is only
as good as the labels under it. **That makes the four label fixes a prerequisite
for every comparison in this file, not an item on a list.**

### Prediction scorecard — 1 of 4

| predicted | actual | |
| --- | --- | --- |
| gate accuracy 60–75% | **32.5%** | wrong, badly — and I named 65% as the viability floor |
| correct refusals 9 -> 10–13 | 13 | right, for the wrong reason: it refuses nearly everything |
| 0 fabrications on unanswerable questions | 0 with v1, **1 with v2** | wrong — UNPARSED routes to the answerer, so the short-circuit leaks |
| grounded 20 -> 19–22 | **9** | wrong by ten questions |

The one hit is the one that matters least, and it is right by accident. A gate
that outputs MISSING for everything would also have landed in that range.

### Routing is not dead; a 1B gate is

The idea survives the run. What died is this implementation, and the next test
needs something this machine does not currently have: **three capable models.**
The gate cannot be the judge (the grader would be grading its own routing call)
and the answerer cannot be the judge (self-grading). Of the five models
installed, only `llama3.2:latest` and `qwen2.5:1.5b` are strong enough to do any
of the three jobs — `qwen2.5:0.5b` copied its own prompt into its answer back in
Week 2.

So testing routing honestly means pulling a third model, and it goes behind the
label fixes and the judge audit, because without those there is nothing to
measure the result against.

---

## After the audit — every number in this file, recomputed

Five labels were wrong, not four. q04 *injured during a game*, q16 *photo
release*, q18 *how teams are created*, q19 *time commitment*, q20 *coach from
the sideline* — all marked `refuse`, all answered by a handbook. The question
set is now **30 answerable · 10 must-refuse**.

| | before (five bad labels) | after |
| --- | --- | --- |
| answerable | 25/25 (100%) | **30/30 (100%)** |
| BM25 hit@5 | 11/25 (44%) | **14/30 (46%)** |
| embeddings hit@5 | 19/25 (76%) | **24/30 (80%)** |
| hybrid (RRF) hit@5 | 19/25 (76%) | **24/30 (80%)** |
| refusal floor separates? | no | **no** |
| **judge correct refusals** | 9/15 (60%) | **8/10 (80%)** |
| judge answered, grounded | 19/25 (76%) | **24/30 (80%)** |
| invented | 0 | **0** |
| over-refused | 4 | **4** |

`answerable` holding at 100% across 30 questions is the strongest structural
result the project has: **five new verbatim keys were added and the chunker kept
every one of them inside a single record.** Zero questions lost to the splitter
on a set 20% larger than the one it was tuned against.

Embeddings found **all five** of the new questions (19 → 24). BM25 found three
(11 → 14). The two questions BM25 missed are q19, whose answer is under the
heading `WHAT IS THE TIME COMMITMENT?` and whose key is a date range, and q20,
whose answer begins *"Parents cheer; coaches coach"* — both of which the
embedding model reached and no amount of lexical tuning would.

### The audit raised the score, and that deserves suspicion

`audit_questions.py` prints a warning on exactly this: *"an audit that only
improves your score was probably not an audit."* Embeddings went 76% → 80%.

Two things make it defensible, and one does not:

- **The expect-flips were forced by the source text**, not by preference. Each
  of the five has a handbook passage that answers the question; three of them
  sit under a literal section heading asking the question.
- **The keys were found by exact-string search over the PDFs**, not by ranked
  retrieval, so there is none of the Week 6 circularity where a BM25 search
  chose the keys a BM25 search would then grade.
- **But I chose the five key strings, not Gisell.** Five of thirty questions —
  one sixth of the answerable set — now carry keys selected by the assistant,
  and the score moved up on precisely those five. Week 4's 20% baseline was
  thrown out for less: labels supplied rather than produced. This is weaker than
  that, because a key is a verbatim quote and the flip decision was made from
  the source text, but it is not nothing, and **the 80% should be quoted with it
  attached** until the five keys have been checked independently.

### The refusal finding, on a cleaner set

| | |
| --- | --- |
| worst leak (q06, concussion) | 17.914 |
| weakest genuine hit (q28, tryout) | 4.209 |
| separates? | **no** |

Still 0/10 on every ranker. Five of the fifteen must-refuse rows turned out to
be mislabelled and **the finding did not move**, which is the best evidence yet
that it is real rather than an artifact of a sloppy question set. The two
remaining leaks are q21 *do boys and girls play on the same teams* and q29
*when are tryouts held* — both cases where the handbooks discuss the topic and
never state the answer, which is the hardest class for any scorer.

### The cost of honest labels: a smaller denominator

Ten must-refuse rows means each is worth 10 percentage points, up from 6.7. With
the ±1 generation noise measured earlier in this file, **8/10 and 9/10 are the
same result.** The labels got more honest and the metric got noisier at the same
time, and the only fix for the second half is more must-refuse questions — which
is now a Week 8 item rather than a footnote.

### Prediction scorecard — 5 of 7

| predicted | actual | |
| --- | --- | --- |
| answerable 29–30/30 | **30/30** | right — and the q19 split I flagged as the likely failure held together |
| BM25 13–14/30 | **14/30** | right |
| embeddings 22–23/30 | **24/30** | wrong, better than predicted |
| refused 0/10 | **0/10** | right |
| judge correct refusals 8/10 | **8/10** | right, exactly |
| grounded 22–24/30 | **24/30** | right |
| over-refused 5 | **4** | wrong, better than predicted |

Both misses are in the favourable direction, which is its own mild warning
sign — but these were arithmetic from a known run plus a known label change,
which is a much easier thing to predict than the behaviour of a new component.
The two genuinely new things predicted this week, prompt v2 and the gate, came
in at 3/4 and 1/4.

---

## Carried into Week 8

1. ~~Fix the known-wrong refuse labels~~ — **done**: five of them, not four.
   q04 was found only because a claim built on it turned out to be false
2. **Hand-audit the judge** — ten rows, counted, quoted beside every judge
   figure. Still never done, and with a 10-row refuse set it is now the only
   way to tell a real one-question move from noise
3. **More must-refuse questions.** Ten rows at 10 points each is below the
   resolution of the effects being measured. Write five more, from questions a
   parent would ask that four handbooks genuinely do not answer
4. **Re-run the v1 vs v2 comparison** on the audited set. The earlier verdict
   was retracted, not replaced
5. **Have the five new keys checked independently** — they were chosen by the
   assistant, and the score rose on exactly those five rows
6. **Routing, properly** — needs a third capable model pulled, since gate,
   answerer and judge must all differ. A 1B gate scored 13/40 against a
   constant's 21/40. v1 ships meanwhile
7. ~~Make the refusal check corruption-tolerant~~ — **done**:
   `refusal_kind()` matches the core phrase with a length guard, has unit
   cases including the q36 string, and counts mangled refusals separately
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
