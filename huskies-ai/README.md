# huskies-ai

Capstone repo for a 10-week solo run of GAI 480 — Applied Generative AI Engineering.
By Week 10 this is a deployed, evaluated retrieval system over a youth sports club's
documents. Right now it is Week 1.

## Week 0 — setup (do this first, finish it, then stop)

```bash
git clone <your-repo-url> huskies-ai && cd huskies-ai
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # then put your key in .env
python verify.py                                        # must print "All checks passed"
```

`verify.py` is the Week 0 gate. Do not start Week 1 until it exits clean.

**Pick your model path now and keep it for all ten weeks.** Hosted API or a local
model — either works, and every exercise is designed for both. Switching mid-course
invalidates every baseline you have recorded. The choice lives in `.env`; the
configuration that gets stamped into result files lives in `config.py`.

## Week 1

```bash
python smoke_test.py                  # Weekday B  — proves the model answers, shows token counts
python src/tokenizers_compare.py      # Weekend    — three tokenizers, one chart
python src/cost_table.py --rate 3.00  # Weekend    — per-source cost, use YOUR provider's rate
```

## Layout

```
config.py                  model config + client. Everything imports from here.
verify.py                  the Week 0 gate
smoke_test.py              first model call, token accounting, temperature check
src/tokenizers_compare.py  word vs character vs subword across the corpus
src/cost_table.py          joins metadata, prices the corpus by source type
data/docs/                 the corpus — SAMPLE FIXTURES, replace in Week 3
data/metadata.csv          one row per document
out/                       generated results (gitignored except .gitkeep)
docs/expected-output/      what the scripts produced on a working setup
```

## The sample corpus is a placeholder

`data/docs/` ships with 20 short documents for an invented club, "Northside Youth FC".
They exist so the scripts run on day one. In Week 3 you replace them with real
Empire State Huskies documents and freeze the list — that is the Week 3 deliverable.

One rule when you swap them in: **keep only documents whose answers you can verify.**
A document you cannot check ground truth against is worse than no document, because
it produces evaluation rows you cannot score.

## Rules that survive the whole course

1. One variable at a time. A result from changing three things at once proves nothing.
2. Every result file records `config.stamp()`. Unrecorded configuration means an
   uncomparable baseline.
3. Commit what did not work. The negative results are the evidence you were measuring.
