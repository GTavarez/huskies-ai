# Retrieval — BM25 vs embeddings

141 records · 30 answerable questions · k=5 · `nomic-embed-text`

| ranker | hit@5 | worst refusal leak |
|---|---|---|
| bm25 | 19/30 (63%) | 17.92 |
| embed | 25/30 (83%) | 0.71 |
| hybrid | 24/30 (80%) | 0.03 |

## Disagreements

- **embeddings only** — What do I need to buy for my child to play?
- **embeddings only** — Do I have to volunteer?
- **embeddings only** — Where are the games played?
- **embeddings only** — Can I coach from the sideline?
- **BM25 only** — Is there a code of conduct I have to sign?
- **embeddings only** — What happens if my child misses practice?
- **embeddings only** — What do I do if my child is sick on game day?
- **embeddings only** — How do I sign up to be a coach?

## What fusing actually changed

- **RRF rescued** — Is there a code of conduct I have to sign?
- **RRF dropped** — What happens if I yell at the referee?
- **RRF dropped** — How do I sign up to be a coach?

Net -1: 1 rescued, 2 dropped. Equal totals, different questions — a wash in the metric is not a wash for a parent.

## Which one ships, and why

_Name the cost as well as the score. An embedding model that wins by one question is not obviously worth 274 MB on a club's laptop._
