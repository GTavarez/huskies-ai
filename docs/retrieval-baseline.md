# Retrieval baseline

`data\records-real.jsonl` — 142 records · 19 questions · BM25 · k=5 · refusal floor 2.0

| metric | result | meaning |
|---|---|---|
| answerable | 10/11 (90%) | one record holds the whole answer |
| hit@5 | 8/11 (72%) | and it was retrieved |
| union@5 | 8/11 (72%) | the top 5 together hold it |
| refused | 0/8 | declined correctly |

## By document

| source | answerable | retrieved |
|---|---|---|
| club-02.pdf | 7 | 5 |
| club-04.pdf | 3 | 3 |

## Where the losses are

- **1** questions have no single record that answers them — corpus
- **2** questions have one and the ranking missed it — retriever

## What I change first, and why

_one paragraph, before you change anything._
