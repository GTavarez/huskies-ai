# Retrieval — BM25 vs embeddings

141 records · 25 answerable questions · k=5 · `nomic-embed-text`

| ranker | hit@5 | worst refusal leak |
|---|---|---|
| bm25 | 11/25 (44%) | 17.91 |
| embed | 19/25 (76%) | 0.74 |
| hybrid | 19/25 (76%) | 0.03 |

## Disagreements

- **embeddings only** — What do I need to buy for my child to play?
- **embeddings only** — Who do I talk to first if I have a problem with the coach?
- **embeddings only** — Do I have to volunteer?
- **embeddings only** — Where are the games played?
- **embeddings only** — What age groups does the club have?
- **embeddings only** — Is there a payment plan?
- **embeddings only** — What happens if it rains?
- **BM25 only** — Is there a tryout?
- **BM25 only** — Is there a code of conduct I have to sign?
- **embeddings only** — What happens if my child misses practice?
- **embeddings only** — What do I do if my child is sick on game day?
- **embeddings only** — How do I sign up to be a coach?

## What fusing actually changed

- **RRF rescued** — Do I need to buy a uniform?
- **RRF rescued** — Is there a tryout?
- **RRF dropped** — What happens if my child misses practice?
- **RRF dropped** — How do I sign up to be a coach?

Net +0: 2 rescued, 2 dropped. Equal totals, different questions — a wash in the metric is not a wash for a parent.

## Which one ships, and why

_Name the cost as well as the score. An embedding model that wins by one question is not obviously worth 274 MB on a club's laptop._
