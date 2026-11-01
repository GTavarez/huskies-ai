# huskies-ai

A retrieval system over four real youth soccer club handbooks, built to answer
the questions parents actually ask — and an evaluation harness that spent eight
weeks catching the ways it, and I, were wrong.

The retrieval is ordinary. The eval is the work.

---

## Where it stands

141 records from four real club handbooks · 40 questions written before any
retriever was run · 32 answerable, 8 the documents genuinely do not answer.

Retrieval figures are club-scoped, which is how the system ships: every
answerable question names the handbook it is about, so the search is restricted
to that club's records.

| | |
| --- | --- |
| **answerable** — the answer sits intact in one record | **32/32** |
| BM25 hit@5 | 21/32 (65%) |
| embeddings hit@5 (`nomic-embed-text`) | 27/32 (84%) |
| hybrid, reciprocal rank fusion | 26/32 (81%) |
| **refusal: any score threshold that separates answerable from unanswerable** | **0/8, on all three rankers** |
| model judge reading the retrieved context | **8/8 correct refusals** |
| answers it invented | **0** |
| answered and grounded | 26/32 |

`answerable` at 32/32 means no question is lost to chunking — every remaining
miss is ranking. It took six weeks of extraction bugs to get there: page
rotation, word spacing, empty-body merges, fee tables promoted to headings.

Two caveats the numbers do not carry on their own. **8/8 is eight rows**, and
the must-refuse set has gone 15 → 10 → 8 as hand audits found questions the
handbooks do answer after all — each flip justified by the source text, the
trend a problem; more must-refuse questions is the top of the Week 8 list.
And **grounded is not complete**: an answer can quote its source exactly and
still not be what was asked. Nothing here measures that yet.

---

## The finding

**No retrieval score tells you whether a passage answers a question.**

Across three ranking functions, two question sets and a purge of five bad
labels, the worst scoring unanswerable question always outscored the weakest
genuine hit. BM25's worst leak scores 17.9 against a weakest real hit of 4.2.
There is no cutoff. Not a tuning problem — a ranking score measures similarity
between a query and a passage, and whether the passage *answers* it is a
different property that nothing in the ranking function looks at.

A second model reading the question, the context and the answer gets 8 of 8 —
and got the same eight right when the set was ten and two of its "errors"
turned out to be mislabelled questions.

The same shape showed up again in Week 8, one layer up: a **gate** predicting
whether an answer could be produced tied a constant (24/40 against 24/40),
while the **judge** verifying an answer that already existed worked.
Verification beats prediction, twice, at two different levels of the stack.

_The judge has been hand-audited: ten rows read against the source handbooks,
sampled by `judge_audit.py` from where its mistakes concentrate rather than
from the front of the file. **Ten of ten verdicts correct.** Two of the ten
were rows the judge had been scored wrong on — and the labels were wrong, not
the judge. Every judge figure above can be quoted with that attached._

---

## What went wrong, and what it cost

The week notes in `docs/` are the real content. Each one is a measurement that
turned out to be wrong and what fixed it.

| | |
| --- | --- |
| [week-04](docs/week-04.md) | Five hand reviews of one corpus gave 20%, 10%, 15%, 25%, 15%. Three of the five were measuring my own tooling — a viewer truncating records at 600 characters, labels I had supplied, a prompt offering one option and asking yes or no. |
| [week-05](docs/week-05.md) | Replaced human judgement with answer keys and `hit@k`. BM25 and embeddings tied at 8/11 while disagreeing on four questions — reading only the totals would have concluded "embeddings add nothing". |
| [week-06](docs/week-06.md) | The key proposer and the scorer were both BM25. The eval had been measuring itself. A cold audit dropped hit@5 from 72% to 35%, and the rigged comparison had been quoted for twelve days. |
| [week-07](docs/week-07.md) | A conclusion built on a label I had already flagged as unreliable. The model had quoted its source almost word for word and I called it a fabrication. Retracted in place rather than deleted. |
| [week-08](docs/week-08.md) | Four guards that worked on website content broke 14 of 30 answers here. A lexical relevance check only earns its place where chunks are topically incoherent — on heading-delimited sections it is a paraphrase tax. |
| [week-09](docs/week-09.md) | Proving a question is unanswerable needs reading, not a failed search. Measured why: the median word in a parent's question appears 54 times across the corpus, the median specific synonym zero — the query and the documents share their common vocabulary and differ only in their rare one. |

Two rules came out of it that transfer past this project:

- **When the thing generating your test data and the thing being tested share a
  mechanism, the test measures the mechanism.** It does not fail loudly. It
  produces a believable number, slightly flattering.
- **Never conclude a document does not say something from a search that failed
  to find it.** Absence is a claim about the whole document; ranking only
  reports what rose to the top. That error set five labels wrong and five
  findings about the source documents wrong, independently.

---

## Running it

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # model config; see config.py
python verify.py                                      # must print "All checks passed"
```

```bash
python ingest.py                     # PDFs -> records
python retrieval_eval.py             # answerable, hit@5, the refusal floor
python embed_eval.py --hybrid        # BM25 vs embeddings vs RRF, with set differences
python judge.py                      # the model judge
python judge_audit.py                # sample its verdicts for a hand audit
```

Everything runs locally against Ollama or any OpenAI-compatible endpoint. The
model configuration lives in one file and is stamped into every result, because
a baseline recorded under an unknown configuration cannot be compared with
anything later.

---

## The corpus is not in this repo

`data/raw/real/` and `data/records-real.jsonl` are gitignored. They are four
other clubs' documents, shared for this work, and this repository is public.
`data/docs/` holds small synthetic fixtures so the pipeline runs without them.

The numbers above are therefore not reproducible from a clone, and saying so is
better than quietly shipping someone else's handbooks.

Ignoring the PDFs turned out not to be enough. The scripts that read them
wrote reports that quoted them — 42 verbatim passages across eight tracked
files, three of which also printed a real club's name, its league and its home
field. **Ignoring an input does not protect it; the leak is in the outputs.**

`tools/leak_check.py` now compares every tracked file against the full
handbook text and runs on staged content from a pre-commit hook, so the rule
is enforced rather than remembered. The question set is published as
`data/questions-public.jsonl` — the questions and their labels, without the
answer strings.

[docs/data-handling.md](docs/data-handling.md) is the whole account, including
the three ways the fix was wrong before it was right.

---

## What is still open

- More must-refuse questions. Eight rows at 12.5 points each is coarser than
  any effect being measured, and the set has only ever shrunk: 15 → 10 → 8
- A completeness measure. An answer can be 100% grounded and still not answer
  the question — q31 tells a parent turf shoes are comfortable instead of what
  a child should wear. The judge asks whether an answer is supported; nothing
  asks whether it is whole
- Weighting the question set. Embeddings 27/32 and hybrid 26/32 differ by one
  row, and the choice between them cannot be settled while every question is
  worth 1/32
