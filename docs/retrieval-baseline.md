# Retrieval baseline

`data\records-real.jsonl` — 141 records · 40 questions · BM25 · k=5 · refusal floor 2.0

| metric | result | meaning |
|---|---|---|
| answerable | 30/30 (100%) | one record holds the whole answer |
| hit@5 | 19/30 (63%) | and it was retrieved |
| union@5 | 19/30 (63%) | the top 5 together hold it |
| refused | 0/10 | declined correctly |

## By document

| source | answerable | retrieved |
|---|---|---|
| club-02.pdf | 13 | 6 |
| club-03.pdf | 6 | 4 |
| club-04.pdf | 11 | 9 |

## Where the losses are

- **0** questions have no single record that answers them — corpus
- **11** questions have one and the ranking missed it — retriever

## What I change first, and why

_one paragraph, before you change anything._
