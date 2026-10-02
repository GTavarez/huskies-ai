# Retrieval baseline

`data\records-real.jsonl` — 142 records · 25 questions · BM25 · k=5 · refusal floor 2.0

| metric | result | meaning |
|---|---|---|
| answerable | 12/14 (85%) | one record holds the whole answer |
| hit@5 | 5/14 (35%) | and it was retrieved |
| union@5 | 5/14 (35%) | the top 5 together hold it |
| refused | 0/11 | declined correctly |

## By document

| source | answerable | retrieved |
|---|---|---|
| club-02.pdf | 6 | 3 |
| club-03.pdf | 2 | 0 |
| club-04.pdf | 4 | 2 |

## Where the losses are

- **2** questions have no single record that answers them — corpus
- **7** questions have one and the ranking missed it — retriever

## What I change first, and why

_one paragraph, before you change anything._
