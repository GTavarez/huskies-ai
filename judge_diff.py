"""Compare two judge runs question by question.

    python judge_diff.py out/judge.csv out/judge-v2.csv

WHY THIS EXISTS
  Two prompts scored 19/25 and 19/25 in Week 7's retrieval comparison and did
  not hit the same nineteen. A total hides a trade, and a trade is the thing you
  need to see when deciding whether a change was an improvement. Same lesson
  here: a prompt that moves `over-refused` from 4 to 0 while moving `correct
  refusals` from 9 to 5 has not improved anything, and both files will show a
  headline that looks like progress.

  So print the set difference. Every question whose verdict changed, in which
  direction, and whether the answer was in the context at the time.

  The totals are printed last on purpose.
"""
import csv
import sys
from pathlib import Path

GOOD = {("answerable", "SUPPORTED"), ("refuse", "REFUSED")}


def load(path):
    with open(path, encoding="utf-8") as f:
        return {r["qid"]: r for r in csv.DictReader(f)}


def verdict_quality(row):
    """Was this verdict the one the label asked for?"""
    return (row["expect"], row["verdict"]) in GOOD


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    a_path, b_path = Path(sys.argv[1]), Path(sys.argv[2])
    for p in (a_path, b_path):
        if not p.exists():
            sys.exit(f"missing: {p}\nRun judge.py to produce it.")
    a, b = load(a_path), load(b_path)

    shared = [q for q in a if q in b]
    missing = sorted(set(a) ^ set(b))
    if missing:
        print(f"note: {len(missing)} question(s) in only one file "
              f"({', '.join(missing[:8])}) — comparing the {len(shared)} shared\n")

    better, worse, sideways = [], [], []
    for q in sorted(shared):
        ra, rb = a[q], b[q]
        if ra["verdict"] == rb["verdict"]:
            continue
        ga, gb = verdict_quality(ra), verdict_quality(rb)
        (better if (gb and not ga) else worse if (ga and not gb)
         else sideways).append((q, ra, rb))

    print(f"{a_path.name}  ->  {b_path.name}")
    print("=" * 70)
    for title, group in (("FIXED", better), ("BROKE", worse),
                         ("changed, neither clearly better", sideways)):
        if not group:
            continue
        print(f"\n{title}  ({len(group)})")
        print("-" * 70)
        for q, ra, rb in group:
            ctx = "answer WAS in context" if ra["retrieved"] == "1" else ""
            print(f"  {q}  {ra['expect']:<10} {ra['verdict']:<11} -> "
                  f"{rb['verdict']:<11} {ctx}")
            print(f"       {rb['question'][:64]}")
    if not (better or worse or sideways):
        print("\nNo verdict changed on any shared question.")

    print(f"\n{'=' * 70}")
    print(f"  fixed {len(better)}   broke {len(worse)}   "
          f"sideways {len(sideways)}   net {len(better) - len(worse):+d}")
    for name, d in ((a_path.name, a), (b_path.name, b)):
        rows = [d[q] for q in shared]
        ref = [r for r in rows if r["expect"] == "refuse"]
        ans = [r for r in rows if r["expect"] == "answerable"]
        cr = sum(1 for r in ref if r["verdict"] == "REFUSED")
        ok = sum(1 for r in ans if r["verdict"] == "SUPPORTED")
        # Count UNSUPPORTED on every row, not just answerable ones. judge.py
        # originally filtered this to answerable and so reported 0 invented on
        # a run that fabricated an injury procedure for a parent.
        inv = sum(1 for r in rows if r["verdict"] == "UNSUPPORTED")
        inv_bad = sum(1 for r in rows
                      if r["verdict"] == "UNSUPPORTED" and r["expect"] == "refuse")
        over = sum(1 for r in ans
                   if r["verdict"] == "REFUSED" and r["retrieved"] == "1")
        mang = sum(1 for r in rows if r.get("refusal") == "corrupt")
        print(f"  {name:<22} refusals {cr}/{len(ref)}   grounded {ok}/{len(ans)}"
              f"   invented {inv} (of those {inv_bad} unanswerable)"
              f"   over-refused {over}   mangled {mang}")
    print("\n  A net of 0 is not a tie. Read the lists above it.")


if __name__ == "__main__":
    main()
