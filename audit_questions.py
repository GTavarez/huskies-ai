"""Week 6, Weekday A — audit the eval set cold, and delete what you cannot confirm.

    python audit_questions.py            # walk every row
    python audit_questions.py --report   # what the last audit decided

WHY COLD MATTERS, AND WHY TWELVE DAYS IS BETTER THAN TWO
  The plan asks for this 48 hours after building the set. The point is that you
  cannot remember what you were thinking, so you have to judge the row on what it
  actually says rather than on what you meant.

  The set being audited was built in two passes that contradicted each other. The
  first accepted 21 machine-proposed keys in a row. The second rejected so much
  that 8 of 19 came out as must-refuse — and at least four of those are wrong,
  because the handbooks do answer them. Neither pass was careless; both were
  made at the end of a long day by one person with no second opinion. This is the
  second opinion, and it is you, later.

WHAT GETS CHECKED
  answerable rows   does the key actually answer the question? Not "is it about
                    the right topic" — would a parent reading only that text have
                    their question answered?

  refuse rows       the tool searches the four PDFs and shows you the best
                    passages. If one of them answers the question, the row is
                    mislabelled and you knew it was suspicious.

DELETING IS THE POINT
  A row you cannot confirm is worse than a missing row, because it still moves
  the percentage. Expect to delete some. An audit that keeps everything did not
  happen.

OUTPUT
  data/questions-real.jsonl   rewritten
  data/questions-rejected.jsonl   what you removed, and why
  docs/eval-audit.md
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

from draft_answers import Index, passages, propose_key

QUESTIONS = Path("data/questions-real.jsonl")
REJECTED = Path("data/questions-rejected.jsonl")


def ask(prompt, lower=True):
    sys.stdout.write(prompt)
    sys.stdout.flush()
    line = sys.stdin.readline()
    if not line:
        return "q"
    line = line.strip()
    return line.lower() if lower else line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--show", type=int, default=3)
    args = ap.parse_args()

    out = Path("docs/eval-audit.md")
    if args.report:
        print(out.read_text(encoding="utf-8") if out.exists() else "no audit yet.")
        return

    rows = [json.loads(l) for l in open(QUESTIONS, encoding="utf-8") if l.strip()]
    print(f"{len(rows)} rows to audit.")
    print("Building the index over the four handbooks ...", flush=True)
    idx = Index(passages())
    print(f"{len(idx.docs)} passages.\n")
    print("=" * 74)
    print("  k  keep it as it is")
    print("  f  fix it — pick a better key, or flip answerable <-> refuse")
    print("  d  delete it — you cannot confirm it, so it should not count")
    print("  q  stop (everything decided so far is saved)")
    print("=" * 74)
    print("A row you cannot confirm still moves the percentage. Delete it.")

    kept, fixed, dropped = [], [], []

    for i, r in enumerate(rows, 1):
        print(f"\n{'-' * 74}")
        print(f"[{i}/{len(rows)}]  {r['qid']}  ({r['category']})  — currently "
              f"{r['expect'].upper()}")
        print(f"  Q: {r['question']}")

        if r["expect"] == "answerable":
            print(f"  key: {r['keys'][0]!r}" if r["keys"] else "  key: (none)")
            print("\n  Would someone reading ONLY that text have their question"
                  " answered?")
        else:
            hits = idx.top(r["question"], args.show)
            if r.get("note"):
                print(f"  reason given: {r['note']}")
            print("\n  What the handbooks actually contain for this question:")
            for n, (src, passage, score) in enumerate(hits, 1):
                print(f"\n  [{n}] {src}")
                print(f"      {passage[:240]}{'...' if len(passage) > 240 else ''}")
            if not hits:
                print("  nothing matched — the refusal looks right.")
            print("\n  Does any of that answer the question? If yes this row is"
                  " mislabelled.")

        v = ""
        while v not in ("k", "f", "d", "q"):
            v = ask("  [k/f/d/q] ")
            if v not in ("k", "f", "d", "q"):
                print("    k = keep · f = fix · d = delete · q = stop")
        if v == "q":
            rows_left = rows[i - 1:]
            kept += rows_left
            print(f"  stopped — {len(rows_left)} rows left untouched.")
            break

        if v == "k":
            kept.append(r)
            print("  kept.")
            continue

        if v == "d":
            why = ""
            while len(why) < 8:
                why = ask("  why are you deleting it? ", lower=False)
                if len(why) < 8:
                    print("    Write the reason — a deletion without one looks "
                          "like a mistake in six weeks.")
            dropped.append({**r, "dropped_because": why})
            print("  deleted.")
            continue

        # fix
        flip = ask("  flip answerable <-> refuse? [y/N] ")
        if flip == "y":
            if r["expect"] == "answerable":
                r.update(expect="refuse", keys=[], answer="", document="",
                         note="flipped at cold audit — key did not answer the "
                              "question and nothing in the handbooks does")
            else:
                hits = idx.top(r["question"], args.show)
                print("  pick the passage that answers it:")
                for n, (src, passage, _) in enumerate(hits, 1):
                    k = propose_key(r["question"], passage)
                    print(f"    [{n}] {src}  key: {k!r}")
                pick = ask("  [number]: ")
                if pick.isdigit() and 1 <= int(pick) <= len(hits):
                    src, passage, _ = hits[int(pick) - 1]
                    k = propose_key(r["question"], passage) or ask(
                        "  type the key: ", lower=False)
                    r.update(expect="answerable", keys=[k], answer=k,
                             document=src,
                             note="flipped at cold audit — the handbooks do "
                                  "answer this")
                else:
                    print("  no pick — leaving it as refuse.")
        else:
            newkey = ask("  new key (copy it exactly from the handbook): ",
                         lower=False)
            if newkey:
                r.update(keys=[newkey], answer=newkey,
                         note="key replaced at cold audit")
        fixed.append(r)
        kept.append(r)
        print(f"  fixed -> {r['expect']}.")

    # Renumber so ids are unique and sequential — the --keep flag in
    # draft_answers.py left duplicates behind.
    for n, r in enumerate(kept, 1):
        r["qid"] = f"q{n:02d}"

    with open(QUESTIONS, "w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    if dropped:
        with open(REJECTED, "a", encoding="utf-8") as f:
            for r in dropped:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    ans = sum(1 for r in kept if r["expect"] == "answerable")
    ref = sum(1 for r in kept if r["expect"] == "refuse")

    print(f"\n{'=' * 58}")
    print(f"  kept     {len(kept)}   ({ans} answerable · {ref} must-refuse)")
    print(f"  fixed    {len(fixed)}")
    print(f"  deleted  {len(dropped)}")
    print(f"{'=' * 58}")
    if not dropped and not fixed:
        print("  Nothing changed. That is possible but unlikely on a set built")
        print("  in two contradictory passes — worth asking whether you audited")
        print("  the rows or recognised them.")

    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        # Do not hardcode how cold the audit was — this file gets reread
        # months later and a wrong interval is worse than no interval.
        built = min((r.get("built") for r in kept if r.get("built")), default=None)
        gap = (f", {(date.today() - date.fromisoformat(built)).days} days after "
               f"the set was built" if built else "")
        f.write(f"# Eval set — cold audit\n\n"
                f"Audited {date.today().isoformat()}{gap}.\n\n")
        f.write(f"| | |\n|---|---|\n| kept | {len(kept)} |\n"
                f"| of those, fixed | {len(fixed)} |\n| deleted | {len(dropped)} |\n"
                f"| answerable | {ans} |\n| must-refuse | {ref} |\n")
        if dropped:
            f.write("\n## Deleted\n\n| question | why |\n|---|---|\n")
            for r in dropped:
                f.write(f"| {r['question']} | {r['dropped_because']} |\n")
        if fixed:
            f.write("\n## Fixed\n\n| question | now |\n|---|---|\n")
            for r in fixed:
                f.write(f"| {r['question']} | {r['expect']} — "
                        f"{r['keys'][0] if r['keys'] else '—'} |\n")
        f.write("\n## What the audit changed about the numbers\n\n"
                "_Rerun `retrieval_eval.py` and `embed_eval.py`, then write what "
                "moved and whether the earlier figures were worth quoting._\n")

    print(f"\nwrote {out}")
    print("\nNow rerun both evals on the cleaned set:")
    print("  python retrieval_eval.py")
    print("  python embed_eval.py --hybrid")
    print("The numbers will move. Whether they move UP is the interesting part —")
    print("an audit that only improves your score was probably not an audit.")


if __name__ == "__main__":
    main()
