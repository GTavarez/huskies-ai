# Week 1 — Foundations

## Setup

- Python 3.10.9, python.org build, venv at `.venv`
- Model path: **local (Ollama)** — `llama3.2:latest` via `http://localhost:11434/v1`
- Chosen once, fixed for all ten weeks. Do not change without recording why.

## Measured

| What | Value |
|---|---|
| Determinism at temperature 0, seed 7 | **deterministic** |
| Unique answers across 5 identical runs | 1 of 5 |
| Mean pairwise similarity | 1.000 |
| Tokens per word (subword tokenizer) | _fill in after tokenizers_compare.py_ |
| Corpus size, sample docs | 20 documents |

Consequence: a small score difference in Week 6 is a real difference, not noise.
No need to average across repeated runs.

## What broke

- Microsoft Store Python could not create a venv — hung at `ensurepip`. Fixed by
  installing python.org 3.10.
- Git Bash needs `source .venv/Scripts/activate`, not `bin`, and backslash paths
  collapse silently.
- Ollama server was running while the `ollama` CLI was missing from PATH.
- `config.py` defined a seed that `smoke_test.py` never sent — that alone accounted
  for the apparent non-determinism.

## What I would do differently

_your turn — two or three sentences_

## Next

_what you are watching for in Week 2_
