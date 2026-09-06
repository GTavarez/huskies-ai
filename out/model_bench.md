# Candidate model scorecard

Corpus: 21 records. Temperature 0.0, seed 7. Measured on this machine, not quoted.

| model | size GB | grounded | refusal | median s | tok/s |
|---|---|---|---|---|---|
| llama3.2:1b | 1.32 | 0/6 | 3/3 | 1.33 | 7.5 |
| llama3.2:latest | 2.02 | 5/6 | 3/3 | 3.19 | 4.9 |
| qwen2.5:0.5b | 0.4 | 6/6 | 0/3 | 0.98 | 24.4 |
| qwen2.5:1.5b | 0.99 | 5/6 | 3/3 | 1.77 | 13.4 |

## Every answer that was marked wrong

### llama3.2:1b

**How many sessions may a new player attend before registering?**  
retrieved `faq-F001, faq-F002`, expected `two`

```
That is not covered in the club documents.
```

**What is the season fee for a U11 player?**  
retrieved `handbook-s2-u10-u12, handbook-s2-u13-u15, handbook-s2`, expected `150`

```
That is not covered in the club documents.
```

**After lightning is seen, how long before play may resume?**  
retrieved `handbook-s6`, expected `30`

```
That is not covered in the club documents.
```

**Up to what point in the season is a subscription refundable?**  
retrieved `faq-F004, faq-F003`, expected `fourth week`

```
That is not covered in the club documents.
```

**Who must accompany an under-13 player to an away fixture?**  
retrieved `handbook-s5`, expected `parent`

```
That is not covered in the club documents.
```

**How quickly must an injury be recorded in the log?**  
retrieved `handbook-s7, ann-A-2026-017`, expected `24 hours`

```
That is not covered in the club documents.
```

### llama3.2:latest

**What is the season fee for a U11 player?**  
retrieved `handbook-s2-u10-u12, handbook-s2-u13-u15, handbook-s2`, expected `150`

```
That is not covered in the club documents.
```

### qwen2.5:0.5b

**What time is training tomorrow?**  
retrieved `-`, expected `That is not covered in the club documents.`

```
Training is scheduled for tomorrow from 9:00 AM to 11:00 AM.
```

**Who is the club's current top scorer?**  
retrieved `-`, expected `That is not covered in the club documents.`

```
The club's current top scorer is not explicitly mentioned in the provided documents.
```

**What is the season fee for a U19 player?**  
retrieved `handbook-s2-u16-u18, handbook-s2-u13-u15, handbook-s2`, expected `That is not covered in the club documents.`

```
The season fee for a U19 player is £195.
```

### qwen2.5:1.5b

**What is the season fee for a U11 player?**  
retrieved `handbook-s2-u10-u12, handbook-s2-u13-u15, handbook-s2`, expected `150`

```
The season fee for a U11 player is £120, or 4 instalments of £30. Kit included: Yes.
```

## Not measured here — fill in by hand

| model | license | context window | still maintained? |
|---|---|---|---|
| llama3.2:1b |  |  |  |
| llama3.2:latest |  |  |  |
| qwen2.5:0.5b |  |  |  |
| qwen2.5:1.5b |  |  |  |

## Recommendation

_One page. Name the model you chose, the two or three numbers above that decided it, and — the part people skip — what you rejected and why. A recommendation with no rejected options is not a decision, it is a description._
