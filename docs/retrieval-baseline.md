# Retrieval baseline

`data\records-real.jsonl` — 141 records · 40 questions · BM25 · k=5 · refusal floor 2.0

| metric | result | meaning |
|---|---|---|
| answerable | 25/25 (100%) | one record holds the whole answer |
| hit@5 | 11/25 (44%) | and it was retrieved |
| union@5 | 11/25 (44%) | the top 5 together hold it |
| refused | 0/15 | declined correctly |

## By document

| source | answerable | retrieved |
|---|---|---|
| club-02.pdf | 11 | 4 |
| club-03.pdf | 4 | 1 |
| club-04.pdf | 10 | 6 |

## Where the losses are

- **0** questions have no single record that answers them — corpus
- **14** questions have one and the ranking missed it — retriever

## What I change first, and why

_one paragraph, before you change anything._
