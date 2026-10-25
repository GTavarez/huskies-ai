# Model judge

141 records · 40 questions · hybrid retrieval, k=5

- answerer: `llama3.2:latest`
- judge: `qwen2.5:1.5b`
- grounded prompt: `v2`

| | | |
|---|---|---|
| correct refusals | 4/15 | declined when the corpus has no answer |
| answered, grounded | 23/25 | and the context supports it |
| **invented** | **0** | answered something the context does not say |
| over-refused | 1 | declined although the answer was retrieved |
| mangled refusals | 0 | meant to refuse, dropped a word from the sentence |

For comparison, the best a retrieval score could do on the first row was **0/15** — on every ranker tried.

## Leaked — answered a question the corpus cannot answer

- **What happens if my child is injured during a game?** — If your child is injured during a game, you should ask the referee if you may enter the field to assist your child.
- **What do I do if my child gets a concussion?** — If your child gets a concussion, you should have them evaluated by a medical professional and follow the concussion return to play form, which is attached to the Parent Agreement document. The form st
- **Do I have to sign a photo release?** — Yes, you are required to sign a photo release form, which is part of the Parent Agreement document. This form grants permission for the club to use your likeness in photographs and videos for publiciz
- **When is practice and how often do teams practice?** — According to [club-01-s26], "What Is a “Practice”? “With few exceptions, parents can be invaluable allies if they really know that a coach’s first priority is the health, safety and development of the
- **How are the teams created?** — Teams are formed each June for the upcoming season, and players must be registered online prior to the start of tryouts for their age group.
- **How big is the time commitment?** — According to [club-03-s7], the time commitment varies by season:  * Summer season: 2 practices per week (1.25 hours each) and 1 tournament (Starfire Xtreme Cup in Tukwila, Washington) * Fall season: 2
- **Can I coach from the sideline?** — If you want to coach from the sideline, you must first obtain permission from the head coach AND you must register as an assistant coach.
- **Do boys and girls play on the same teams?** — According to the club documents, All Whatcom County Select teams participate in the North Puget Sound League (NPSL), which offers competition at a local level for boys and girls U9 to U19 soccer teams
- **What if I cannot afford the fees?** — The club has a payment plan available, which can be requested to the Player Representative or Club Registrar.
- **What time do games start?** — According to [club-03-s7], the time commitment for games is not specified, but it mentions that most home games will take place at Phillips 66 Fields, and away games will take place south of Whatcom C
- **When are tryouts held?** — Tryouts are held in June for the upcoming season, with each age group having two 75-minute tryout sessions.

## Did you spot-check the judge?

_A 1.5B judge is wrong sometimes. Read ten rows of `out/judge.csv` by hand, say how many the judge got right, and quote that number next to every figure above. A judge you have not audited is the same mistake as an eval you have not audited._
