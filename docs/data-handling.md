# Data handling — what is in this repo, what is not, and what checks it

The corpus this project evaluates is four real youth soccer club parent
handbooks, obtained from the clubs' own public pages. They are not mine to
republish, so they are not here, and neither is anything that reproduces their
wording.

That intention was in place from Week 1. It did not hold, and the reason it did
not hold is the useful part of this document.

---

## The rule

| | |
| --- | --- |
| **not in the repo** | the four PDFs, the records built from them, their full text, model answers quoting them, and every generated report that prints any of it |
| **in the repo** | the code, the week notes, and `data/questions-public.jsonl` — the 40 questions and their labels, with the answer strings removed |

A consequence worth stating plainly: **no number in this repo is reproducible
from a clone.** The corpus is absent, so `hit@5`, `answerable` and the judge
figures cannot be re-derived by a reader. The code is reviewable; the results
are reported. Anyone who wants to check the method can point it at their own
documents.

---

## What the audit found

`tools/leak_check.py` reduces every tracked file and the full handbook text to
letters and digits, then looks for runs of 8+ words from the file inside the
text. A hit means that exact wording came out of a real club's document.

Run against the whole repo for the first time on 2026-11-01:

| file | verbatim runs |
| --- | --- |
| `data/questions-real.jsonl` | 28 — the `answer` and `keys` fields |
| `docs/judge-report-v2.md` | 5 — model answers printed in full |
| `docs/judge-report-gated-g2.md` | 2 |
| `docs/judge-report-guards.md` | 1 |
| four week notes | 6 — illustrative quotations |
| **total** | **42 runs across 8 files** |

Three of those reports also printed a real club's name, its league and its home
field. The `club-01` … `club-04` labels used everywhere else were not
anonymising anything, because the generated reports printed the real names
beside them.

---

## Why the gitignore did not prevent it

**Ignoring an input does not protect it. The leak is in the outputs.**

Every one of those eight files was written by a script that read the gitignored
corpus and wrote somewhere that was not gitignored. The PDFs never moved. The
text walked out in the reports.

A path deny-list cannot catch this, and that is not a tuning problem. A
deny-list enumerates files someone already thought of; each of these arrived as
a *new* file, from a script written weeks after the ignore rules. Three such
reports were listed in `.gitignore` and ten were not, which is the shape of the
failure: the rule was maintained by memory.

So the check is on content, and it runs on every commit. `tools/leak_check.py
--staged` is called from the pre-commit guard, which also blocks the paths, and
blocks added lines containing an email address, a phone number, a private key
or an API token.

---

## Three things that went wrong in the fix itself

Worth recording, because all three are the same mistake in different clothes:
**a check that is wrong fails quietly, and a quiet failure reads as success.**

**1. The leak checker reported clean across all 91 tracked files** while a
quoted sentence naming a real club sat in `docs/`. The reference text is stored
with every space removed — one unbroken string — and the first version compared
word streams against it, so no match was possible. It now reduces both sides
identically, and refuses to report clean if the reference is too small to be
the four handbooks.

**2. The pre-commit guard passed everything** on its first write. Its rules
were a table separated by tab characters, and the tabs did not survive being
written to disk, so every rule's regex became the whole line and matched
nothing. Found by testing it against a throwaway repo with planted files rather
than by reading it.

**3. Two verification steps produced false failures.** One used `git log
--all`, which reads the backup refs `filter-branch` creates, so it found the
pre-rewrite history and reported the rewrite had failed. The other matched
removed paths by substring and flagged `data/questions-rejected-public.jsonl`
— the redacted replacement — as the private file it replaces.

A checker that cannot fail loudly is worse than no checker, because it converts
"nobody looked" into "we checked."

---

## Testing the anonymisation

The `club-01` … `club-04` labels were checked twice. The first check searched
for the organisation names that had appeared in output someone had looked at,
which tests what has been noticed rather than what is there — and would have
missed one club entirely, whose name sits in its page footer.

The second derived the names from the source: a pattern for capitalised
sequences ending in `Soccer Club`, `Youth Soccer`, `League`, `Association`,
`Select`, `Sportsplex`, `FC` or `SC`, run over all four PDFs, then every result
checked against every tracked file and every commit in history.

**39 organisation names appear in the handbooks. One appears in this repo** —
`US Youth Soccer`, a national governing body, in a week note. No club or place
name appears in any tracked file or any commit.

**To test whether something has leaked, enumerate from the source, not from
what you have noticed.** A list built from memory tests the memory.

---

## What a force-push does not undo

The exposed content was removed from the branch and from every commit. That is
not the same as it never having been published:

- anyone who cloned or forked in the window has it
- GitHub serves unreachable objects by SHA for a period after a force-push —
  tested directly here, and an old commit was still fetchable
- cached file views can persist until GitHub Support purges them

Anything that was public should be treated as having been seen. Removing it
stops the exposure continuing; it does not reach backwards.
