# Retrieval — BM25 vs embeddings

142 records · 14 answerable questions · k=5 · `nomic-embed-text`

| ranker | hit@5 | worst refusal leak |
|---|---|---|
| bm25 | 5/14 (35%) | 18.02 |
| embed | 12/14 (85%) | 0.74 |
| hybrid | 12/14 (85%) | 0.03 |

## Disagreements

- **embeddings only** — What do I need to buy for my child to play?
- **embeddings only** — Do I need to buy a uniform?
- **embeddings only** — Who do I talk to first if I have a problem with the coach?
- **embeddings only** — Do I have to volunteer?
- **embeddings only** — Where are the games played?
- **embeddings only** — What age groups does the club have?
- **embeddings only** — Is there a payment plan?

## Which one ships, and why

_Name the cost as well as the score. An embedding model that wins by one question is not obviously worth 274 MB on a club's laptop._
