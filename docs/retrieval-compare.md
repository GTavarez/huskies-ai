# Retrieval — BM25 vs embeddings

142 records · 11 answerable questions · k=5 · `nomic-embed-text`

| ranker | hit@5 | worst refusal leak |
|---|---|---|
| bm25 | 8/11 (72%) | 18.02 |
| embed | 8/11 (72%) | 0.77 |
| hybrid | 9/11 (81%) | 0.03 |

## Disagreements

- **embeddings only** — What do I need to buy for my child to play?
- **BM25 only** — What age groups does the club have?
- **BM25 only** — When is practice and how often do teams practice?
- **embeddings only** — Do I have to volunteer?

## Which one ships, and why

_Name the cost as well as the score. An embedding model that wins by one question is not obviously worth 274 MB on a club's laptop._
