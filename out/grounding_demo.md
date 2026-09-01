# Grounding demo — qwen2.5:0.5b

Retrieval is hand-written here. Weeks 4-5 replace that.

## What should my child bring to practice?

retrieved: `faq-F005`

**Ungrounded** (22 prompt tokens)

```
For a youth sports club, your child should bring their own equipment, such as a ball, a mat, and a water bottle.
```

**Grounded** (112 prompt tokens)

```
To practice, your child should bring:
- Shin pads
- Boots appropriate to the surface
- A filled water bottle
- Jewellery, including earrings and fitness trackers, must be removed before play.
```

## How is my child's age group decided?

retrieved: `handbook-s1`

**Ungrounded** (23 prompt tokens)

```
Age groups are determined by age and gender.
```

**Grounded** (185 prompt tokens)

```
A player's age group is determined by the player's age on 31 August of the current season year.
```

## After lightning is seen, how long before play can resume?

retrieved: `handbook-s6`

**Ungrounded** (26 prompt tokens)

```
After lightning is seen, play can resume 10-15 minutes before the next scheduled game.
```

**Grounded** (147 prompt tokens)

```
Play is suspended immediately on the sighting of lightning and may not resume for at least 30 minutes after the last strike.
```

## What time is training tomorrow?

retrieved: `nothing`

**Ungrounded** (20 prompt tokens)

```
I'm sorry, but I don't have real-time information about the specific training schedule for tomorrow. I can't provide you with the exact time.
```

**Grounded** (70 prompt tokens)

```
That is not covered in the club documents. Do not add general knowledge about how clubs usually work.
```

