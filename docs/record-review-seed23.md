# Record review

Corpus: `data/records-real.jsonl` — 142 records, 4 source documents.

## Shape

| source | records | median_chars | shortest | longest | under_100 | over_2000 |
|---|---|---|---|---|---|---|
| club-01.pdf | 48 | 325 | 44 | 1938 | 9 | 0 |
| club-02.pdf | 36 | 822 | 32 | 5562 | 2 | 7 |
| club-03.pdf | 24 | 400 | 44 | 1869 | 1 | 0 |
| club-04.pdf | 34 | 374 | 85 | 2674 | 1 | 1 |

## Verdicts — 20 records reviewed by hand

- **self-contained:** 3 (15%)
- **partial:** 9
- **not usable:** 8

| doc_id | source | chars | verdict | what is missing |
|---|---|---|---|---|
| `club-02-s27` | club-02.pdf | 925 | p | text starts with number |
| `club-01-s23` | club-01.pdf | 123 | p | no pnctuation |
| `club-01-s6` | club-01.pdf | 519 | n | contents dot leaders and ends mid sentence |
| `club-02-s31` | club-02.pdf | 3166 | p | 2066 characters ommited visuble |
| `club-04-s1` | club-04.pdf | 189 | n | no punctuation and ends mid sentence |
| `club-03-s15` | club-03.pdf | 180 | p | numberred sentences |
| `club-04-s28` | club-04.pdf | 454 | y |  |
| `club-03-s9` | club-03.pdf | 104 | y |  |
| `club-01-s35` | club-01.pdf | 542 | n | contents dot leaders |
| `club-02-s2` | club-02.pdf | 510 | p | ends mid sentence |
| `club-02-s21` | club-02.pdf | 1478 | p | 378 chartaecs omitted visible |
| `club-04-s6` | club-04.pdf | 113 | p | contents dot leaders |
| `club-01-s5` | club-01.pdf | 415 | p | contents dot leaders |
| `club-02-s9` | club-02.pdf | 167 | n | ends mid sentence |
| `club-04-s9` | club-04.pdf | 124 | y |  |
| `club-01-s8` | club-01.pdf | 225 | n | ennds mid sentence and umber on title |
| `club-01-s29` | club-01.pdf | 895 | n | contenst dot leaders |
| `club-04-s20` | club-04.pdf | 1723 | n | 623 charates omitted |
| `club-03-s25` | club-03.pdf | 336 | p | enumeredred sentences |
| `club-01-s7` | club-01.pdf | 746 | n | contents dot leaders |

### By document

| source | reviewed | self-contained |
|---|---|---|
| club-01.pdf | 7 | 0 (0%) |
| club-02.pdf | 5 | 0 (0%) |
| club-03.pdf | 3 | 1 (33%) |
| club-04.pdf | 5 | 2 (40%) |

## The worst document

_Which of the four, and why._

## What I would change in the splitter

_One or two concrete fixes._
