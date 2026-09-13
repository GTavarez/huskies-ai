# Record review

Corpus: `data/records-real.jsonl` — 239 records, 4 source documents.

## Shape

| source | records | median_chars | shortest | longest | under_100 | over_2000 |
|---|---|---|---|---|---|---|
| club-01.pdf | 67 | 210 | 8 | 1454 | 15 | 0 |
| club-02.pdf | 117 | 242 | 12 | 5906 | 31 | 3 |
| club-03.pdf | 31 | 381 | 44 | 1478 | 9 | 0 |
| club-04.pdf | 24 | 682 | 112 | 3982 | 0 | 3 |

## Verdicts — 10 records reviewed by hand

- **self-contained:** 2 (20%)
- **partial:** 2
- **not usable:** 6

| doc_id | source | chars | verdict | what is missing |
|---|---|---|---|---|
| `club-02-s29` | club-02.pdf | 44 | n | contents line, no content |
| `club-01-s56` | club-01.pdf | 349 | y |  |
| `club-02-s74` | club-02.pdf | 30 | n | sentence cut in half |
| `club-02-s184` | club-02.pdf | 238 | n | starts and ends mid-sentence |
| `club-01-s21` | club-01.pdf | 98 | n | publisher credit and page number |
| `club-01-s28` | club-01.pdf | 165 | y |  |
| `club-03-s58` | club-03.pdf | 80 | p | one rule, rest are elsewhere |
| `club-02-s129` | club-02.pdf | 231 | p | complete directions, no venue named |
| `club-01-s39` | club-01.pdf | 65 | n | text starts with a comma |
| `club-02-s61` | club-02.pdf | 188 | n | promises rules, doesn't include them |

## The worst document

_Which of the four, and why._

## What I would change in the splitter

_One or two concrete fixes._
