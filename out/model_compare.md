# Model comparison

- **A** — `llama3.2:latest`
- **B** — `qwen2.5:0.5b`
- temperature 0.0, seed 7, max_tokens 400
- system prompt was sent to both

## a direct question

> What time does practice start?

**A — llama3.2:latest**

```
I'm not sure what the practice schedule is for this club. Can you please check the team's website or contact the coach for the most up-to-date information?
```

**B — qwen2.5:0.5b**

```
Practice starts at 8:00 AM.
```

## an instruction with a format rule

> List exactly three items a player must bring to practice. Number them 1 to 3 and write nothing else.

**A — llama3.2:latest**

```
1. Water bottle
2. Extra set of clothes
3. Athletic shoes
```

**B — qwen2.5:0.5b**

```
1. Warm-up equipment
2. Practice shoes
3. Practice clothing
```

## a half-finished sentence

> The registration deadline for the spring season is

**A — llama3.2:latest**

```
I don't have that information. Can you please check the club's website or contact the club directly for the registration deadline?
```

**B — qwen2.5:0.5b**

```
The registration deadline for the spring season is typically around the end of March or early April.
```

## What differed

_Three sentences. Write them yourself._

1. 
2. 
3. 
