"""Week 4 step 4 — is what came out of those handbooks actually usable?

    python inspect_records.py                          # the real corpus
    python inspect_records.py --file data/records.jsonl # Northside, for comparison
    python inspect_records.py --n 15                    # review more of them

Two halves. The first is arithmetic and runs on its own: how many records each
club produced, how long they are, how many are suspiciously short. The second is
a judgement only you can make, one record at a time:

    Would this record, on its own, answer a parent's question?

That question is the whole of retrieval quality. A chunk that needs the section
before it to make sense will be retrieved alone, shown alone, and answered from
alone — and it will be wrong alone.

WHAT THE VERDICTS MEAN
  y  yes, self-contained. Someone could act on this.
  p  partial — the fact is in here but it needs context that is not.
  n  no. A fragment, a heading with no body, a contents entry, a page of names.

Fifteen minutes of this is worth more than any metric you can compute, because
in Week 6 you will be scoring retrieval against these records and a corpus full
of 'n' makes every score downstream meaningless.

OUTPUT
  docs/record-review.md
"""
import argparse
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def load(path):
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"{p} not found — run ingest.py first.")
    return [json.loads(line) for line in open(p, encoding="utf-8")]


def by_club(records):
    """Group by source file. Each real handbook is one club."""
    groups = defaultdict(list)
    for r in records:
        groups[r.get("source_file", "?")].append(r)
    return groups


def summarise(groups):
    rows = []
    for name, recs in sorted(groups.items()):
        lengths = [len(r["text"]) for r in recs]
        rows.append({
            "source": name,
            "records": len(recs),
            "median_chars": int(statistics.median(lengths)) if lengths else 0,
            "shortest": min(lengths) if lengths else 0,
            "longest": max(lengths) if lengths else 0,
            "under_100": sum(1 for n in lengths if n < 100),
            "over_2000": sum(1 for n in lengths if n > 2000),
        })
    return rows


def print_table(rows):
    cols = ["source", "records", "median_chars", "shortest", "longest", "under_100", "over_2000"]
    w = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in cols}
    print("  ".join(c.ljust(w[c]) for c in cols))
    print("  ".join("-" * w[c] for c in cols))
    for r in rows:
        print("  ".join(str(r[c]).ljust(w[c]) for c in cols))


def display(text, head=700, tail=400):
    # Third revision. Truncating at 600 made every long record look like it
    # ended mid-sentence; marking the omission made three reviewers' verdicts
    # be about the marker. The longest record in this corpus is 5,562
    # characters, which fits on a screen. So: print all of it, always, and let
    # the viewer contribute nothing to the judgement.
    return text


def _display_elided(text, head=700, tail=400):
    """Show the record in a form you can actually judge.

    The first version of this printed `text[:600]` and appended an ellipsis. On
    a corpus whose median record is 529 characters that quietly truncated a
    third of every sample — and because the cut always lands mid-sentence, the
    verdict it invites is "ends mid-sentence". Seven of twenty reviewed records
    were rejected for a defect introduced by the viewer rather than found in the
    corpus.

    A measurement instrument that manufactures the thing it is measuring is
    worse than no instrument. So: short records print whole, and long ones print
    their beginning AND their end, with the omission stated in characters. You
    can always see how a record actually finishes, which is the one thing the
    question depends on."""
    if len(text) <= head + tail:
        return text
    omitted = len(text) - head - tail
    return (f"{text[:head]}\n"
            f"           [… {omitted} characters omitted — the END of the record follows …]\n"
            f"           {text[-tail:]}")


def ask(prompt, lower=True):
    """Prompt and read one line.

    input(prompt) does not reliably flush its prompt under Git Bash / MINGW64,
    so prompts arrive after the answer and keystrokes land in the wrong place.
    Writing the prompt separately with flush=True fixes it in every shell."""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    line = sys.stdin.readline()
    if not line:                       # Ctrl-D / closed stdin
        return "q"
    line = line.strip()
    return line.lower() if lower else line


def review(records, n, seed=7):
    """Sample and ask. Deterministic, so you can stop and resume the same set."""
    rng = random.Random(seed)
    sample = rng.sample(records, min(n, len(records)))
    verdicts = []

    print(f"\n{'=' * 74}")
    print(f"Reviewing {len(sample)} records. For each one:")
    print("  y = self-contained    p = partial    n = not usable    q = stop here")
    print(f"{'=' * 74}")

    for i, r in enumerate(sample, 1):
        print(f"\n[{i}/{len(sample)}]  {r['doc_id']}   ({len(r['text'])} chars)")
        print(f"  source : {r['source_file']}")
        print(f"  title  : {r['title'][:90]}")
        print(f"  text   : {display(r['text'])}")
        print("\n  Would this answer a parent's question ON ITS OWN?", flush=True)

        while True:
            v = ask("  [y/p/n/q] ")
            if v in ("y", "p", "n", "q"):
                break
            print("  y, p, n or q.", flush=True)
        if v == "q":
            print("  stopped early — the records you did review still count.")
            break

        why = ""
        if v in ("p", "n"):
            why = ask("  what is missing or wrong? ", lower=False)
        verdicts.append({"doc_id": r["doc_id"], "source": r["source_file"],
                         "chars": len(r["text"]), "verdict": v, "why": why,
                         "title": r["title"]})
    return verdicts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="data/records-real.jsonl")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=7,
                    help="which records get sampled. Change it for a second, "
                         "independent sample — re-reviewing records you have "
                         "already seen measures your memory, not the corpus.")
    ap.add_argument("--no-review", action="store_true", help="stats only, skip the questions")
    args = ap.parse_args()

    records = load(args.file)
    groups = by_club(records)

    print(f"{args.file}: {len(records)} records from {len(groups)} source files\n")
    rows = summarise(groups)
    print_table(rows)

    print("\nWhat to look for in that table before you read a single record:")
    print("  under_100  a pile of these means headings are being detected where")
    print("             there are none — a contents page, or a list of names.")
    print("  over_2000  means headings are being MISSED, and two or three sections")
    print("             have merged into one unretrievable slab.")
    print("  records    wildly different counts across clubs of similar length is")
    print("             the signal that one document defeated the splitter.")

    verdicts = [] if args.no_review else review(records, args.n, args.seed)

    out = Path(f"docs/record-review-seed{args.seed}.md" if args.seed != 7
               else "docs/record-review.md")
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("# Record review\n\n")
        f.write(f"Corpus: `{args.file}` — {len(records)} records, "
                f"{len(groups)} source documents.\n\n## Shape\n\n")
        cols = ["source", "records", "median_chars", "shortest", "longest", "under_100", "over_2000"]
        f.write("| " + " | ".join(cols) + " |\n|" + "|".join("---" for _ in cols) + "|\n")
        for r in rows:
            f.write("| " + " | ".join(str(r[c]) for c in cols) + " |\n")

        if verdicts:
            counts = {v: sum(1 for x in verdicts if x["verdict"] == v) for v in "ypn"}
            total = len(verdicts)
            f.write(f"\n## Verdicts — {total} records reviewed by hand\n\n")
            f.write(f"- **self-contained:** {counts['y']} ({counts['y']*100//total}%)\n")
            f.write(f"- **partial:** {counts['p']}\n")
            f.write(f"- **not usable:** {counts['n']}\n\n")
            f.write("| doc_id | source | chars | verdict | what is missing |\n")
            f.write("|---|---|---|---|---|\n")
            for v in verdicts:
                f.write(f"| `{v['doc_id']}` | {v['source']} | {v['chars']} | "
                        f"{v['verdict']} | {v['why']} |\n")
            # One rate across four documents hides the case where three are
            # fine and one is unusable — which is a completely different problem
            # with a completely different fix.
            per = defaultdict(lambda: [0, 0])
            for v in verdicts:
                per[v["source"]][0] += 1
                per[v["source"]][1] += 1 if v["verdict"] == "y" else 0
            f.write("\n### By document\n\n| source | reviewed | self-contained |\n|---|---|---|\n")
            print("\nby document:")
            for src in sorted(per):
                n, good = per[src]
                f.write(f"| {src} | {n} | {good} ({good*100//n}%) |\n")
                print(f"  {src:<14} {good}/{n}")

            f.write("\n## The worst document\n\n_Which of the four, and why._\n")
            f.write("\n## What I would change in the splitter\n\n_One or two concrete fixes._\n")

            print(f"\n{counts['y']} of {total} were self-contained "
                  f"({counts['y']*100//total}%).")
            if counts["y"] * 100 // total < 60:
                print("Under 60% means the chunking is the problem, not the model.")
                print("Fix that before Week 5 or every retrieval score you take")
                print("afterwards will be measuring the wrong thing.")

    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
