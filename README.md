# huskies-ai

A retrieval system over four real youth soccer club handbooks, built to answer
the questions parents actually ask — and an evaluation harness that spent eight
weeks catching the ways it, and I, were wrong.

The retrieval is ordinary. The eval is the work.

---

## Where it stands

141 records from four real club handbooks · 40 questions written before any
retriever was run · 30 answerable, 10 the documents genuinely do not answer.

| | |
| --- | --- |
| **answerable** — the answer sits intact in one record | **30/30** |
| BM25 hit@5 | 15/30 (50%) |
| embeddings hit@5 (`nomic-embed-text`) | 24/30 (80%) |
| hybrid, reciprocal rank fusion | 24/30 (80%) |
| **refusal: any score threshold that separates answerable from unanswerable** | **0/10, on all three rankers** |
| model judge reading the retrieved context | **8/10 correct refusals** |
| answers it invented | **0** |

`answerable` at 30/30 means no question is lost to chunking — every remaining
miss is ranking. It took six weeks of extraction bugs to get there: page
rotation, word spacing, empty-body merges, fee tables promoted to headings.

---

## The finding

**No retrieval score tells you whether a passage answers a question.**

Across three ranking functions, two question sets and a purge of five bad
labels, the worst scoring unanswerable question always outscored the weakest
genuine hit. BM25's worst leak scores 17.9 against a weakest real hit of 4.2.
There is no cutoff. Not a tuning problem — a ranking score measures similarity
between a query and a passage, and whether the passage *answers* it is a
different property that nothing in the ranking function looks at.

A second model reading the question, the context and the answer gets 8 of 10.

The same shape showed up again in Week 8, one layer up: a **gate** predicting
whether an answer could be produced tied a constant (24/40 against 24/40),
while the **judge** verifying an answer that already existed worked.
Verification beats prediction, twice, at two different levels of the stack.

_The judge's own error rate is being hand-audited; `judge_audit.py` samples the
rows where its mistakes concentrate. Until that count exists, 8/10 is quoted
without an error bar and says so._

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

---

## What is still open

- Hand-audit count for the judge — the error bar on every figure here
- More must-refuse questions; ten rows at ten points each is coarser than the
  effects being measured
- Metadata filtering by club. Four handbooks contradict each other on uniforms,
  conduct, coaching and tournament fees, and retrieval has no idea which club a
  parent belongs to — it will hand them the wrong one confidently
- Weighting the question set. Hybrid and embeddings tie at 24/30 and hit a
  *different* 24, so the choice between them cannot be settled while every
  question is worth 1/30
