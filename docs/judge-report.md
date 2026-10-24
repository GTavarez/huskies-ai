# Model judge

141 records · 40 questions · hybrid retrieval, k=5

- answerer: `llama3.2:latest`
- judge: `qwen2.5:1.5b`

| | | |
|---|---|---|
| correct refusals | 9/15 | declined when the corpus has no answer |
| answered, grounded | 20/25 | and the context supports it |
| **invented** | **0** | answered something the context does not say |
| over-refused | 4 | declined although the answer was retrieved |

For comparison, the best a retrieval score could do on the first row was **0/15** — on every ranker tried.

## Leaked — answered a question the corpus cannot answer

- **Do I have to sign a photo release?** — Yes, you are required to sign a photo release form, which is part of the Parent Agreement document [club-02-s34].
- **How are the teams created?** — Teams are formed each June for the upcoming season.
- **How big is the time commitment?** — According to [club-03-s7], the time commitment varies by season:  * Summer Season: 2 practices per week (1.25 hours each) and 1 tournament (Starfire Xtreme Cup in Tukwila, Washington) * Fall Season: 2
- **Can I coach from the sideline?** — Parents cheer; coaches coach. If you want to coach from the sideline, sign up to be an assistant coach or head coach. If you are not prepared to come to every practice and help out as a coach, you sho
- **Do boys and girls play on the same teams?** — All Whatcom County Select teams participate in the North Puget Sound League (NPSL), which offers competition at a local level for boys and girls U9 to U19 soccer teams.
- **When are tryouts held?** — Each age group will have two 75-minute tryout sessions.

## Did you spot-check the judge?

_A 1.5B judge is wrong sometimes. Read ten rows of `out/judge.csv` by hand, say how many the judge got right, and quote that number next to every figure above. A judge you have not audited is the same mistake as an eval you have not audited._
