"""Write a publishable copy of the question set, without the handbook text.

    python tools/export_public_questions.py

WHY
  data/questions-real.jsonl carries, per row, the `answer` and `keys` fields -
  verbatim strings lifted out of four other clubs' handbooks. Forty of them.
  The handbooks themselves are gitignored; the quotations were not, for three
  months, which made the gitignore decorative.

  The harness keeps reading the full file. Only the published copy is stripped,
  and nothing in the tooling changes.

  A clone cannot reproduce any number in this repo anyway - the corpus is not
  here - so the keys were never useful to a reader. The questions and their
  labels are the interesting part, and those stay.

OUT
  data/questions-public.jsonl            the live set, tracked
  data/questions-rejected-public.jsonl   what was dropped and why, tracked
"""
import json
import io
from pathlib import Path

KEEP = ["qid", "category", "question", "expect", "document", "note"]
# (source, destination, extra field kept). The two sets stay in separate files:
# merging them produced a headline count of 34 answerable / 12 must-refuse,
# which is the live set plus six rows that were deliberately thrown out.
JOBS = [
    (Path("data/questions-real.jsonl"), Path("data/questions-public.jsonl"), None),
    (Path("data/questions-rejected.jsonl"),
     Path("data/questions-rejected-public.jsonl"), "dropped_because"),
]


def main():
    wrote_any = False
    for src, out, extra in JOBS:
        if not src.exists():
            print(f"not found, skipped: {src}")
            continue
        rows = []
        for line in io.open(src, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            row = {k: r.get(k, "") for k in KEEP}
            if extra:
                row[extra] = r.get(extra, "")
            rows.append(row)
        if not rows:
            print(f"empty, skipped: {src}")
            continue
        with io.open(out, "w", encoding="utf-8", newline="\n") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        n_ref = sum(1 for r in rows if r["expect"] == "refuse")
        print(f"wrote {out}: {len(rows)} rows "
              f"({len(rows) - n_ref} answerable · {n_ref} must-refuse), "
              f"answer and keys fields dropped")
        wrote_any = True

    if not wrote_any:
        raise SystemExit("nothing to export")


if __name__ == "__main__":
    main()
