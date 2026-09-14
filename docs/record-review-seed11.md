# Record review

Corpus: `data/records-real.jsonl` — 128 records, 4 source documents.

## Shape

| source | records | median_chars | shortest | longest | under_100 | over_2000 |
|---|---|---|---|---|---|---|
| club-01.pdf | 34 | 529 | 65 | 1487 | 2 | 0 |
| club-02.pdf | 36 | 822 | 32 | 5562 | 2 | 7 |
| club-03.pdf | 24 | 400 | 44 | 1869 | 1 | 0 |
| club-04.pdf | 34 | 374 | 85 | 2674 | 1 | 1 |

## Verdicts — 20 records reviewed by hand

- **self-contained:** 5 (25%)
- **partial:** 1
- **not usable:** 14

| doc_id | source | chars | verdict | what is missing |
|---|---|---|---|---|
| `club-04-s22` | club-04.pdf | 622 | n | bad title and text spacing |
| `club-04-s26` | club-04.pdf | 379 | y |  |
| `club-02-s15` | club-02.pdf | 1558 | n | bad staryire |
| `club-02-s14` | club-02.pdf | 483 | n | bad title and enda mid sentence |
| `club-04-s28` | club-04.pdf | 454 | y |  |
| `club-01-s26` | club-01.pdf | 527 | n | bad punctuation and starts with dash |
| `club-04-s21` | club-04.pdf | 1527 | n | text that says 427 characters omitted |
| `club-03-s9` | club-03.pdf | 104 | y |  |
| `club-02-s3` | club-02.pdf | 774 | y |  |
| `club-01-s25` | club-01.pdf | 312 | n | starts with dash |
| `club-01-s12` | club-01.pdf | 632 | n | contents dot leader |
| `club-04-s8` | club-04.pdf | 85 | n | ends mid sentence |
| `club-02-s7` | club-02.pdf | 267 | n | all caps |
| `club-01-s5` | club-01.pdf | 918 | n | contents dot leaders |
| `club-01-s18` | club-01.pdf | 672 | n | ends mid sentence |
| `club-01-s17` | club-01.pdf | 162 | n | ends mid sentence |
| `club-01-s11` | club-01.pdf | 220 | n | ends mid sentence |
| `club-02-s28` | club-02.pdf | 735 | p | bad title |
| `club-01-s9` | club-01.pdf | 546 | n | extra unnecesarry charatercs noted |
| `club-04-s25` | club-04.pdf | 1069 | y |  |

### By document

| source | reviewed | self-contained |
|---|---|---|
| club-01.pdf | 8 | 0 (0%) |
| club-02.pdf | 5 | 1 (20%) |
| club-03.pdf | 1 | 1 (100%) |
| club-04.pdf | 6 | 3 (50%) |

## The worst document

_Which of the four, and why._

## What I would change in the splitter

_One or two concrete fixes._
