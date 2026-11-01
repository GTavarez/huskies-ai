"""Does any file in this repo contain verbatim text from the four handbooks?

    python tools/leak_check.py                 # every tracked file
    python tools/leak_check.py --staged        # only what is staged (hook mode)
    python tools/leak_check.py --min-words 6   # stricter

WHY THIS EXISTS
  The four real handbooks are gitignored, and so are the records, the full text
  and the judge CSVs. That was treated as sufficient for three months. It was
  not: generated reports under docs/ quoted whole sentences out of club-03's
  handbook and named the club, its league and its home field, and the question
  set carried forty verbatim answer strings. Every one of those files was
  written by a script that read the gitignored corpus and wrote somewhere that
  was not gitignored.

  A deny-list of paths cannot catch that, because the leak is in content that
  arrives in a new file nobody thought to list. This checks the content.

HOW
  Every run of >= --min-words words in a candidate file is looked up in the
  full handbook text. A hit means that exact wording came out of a real club's
  document. Short runs are ignored, since ordinary English collides.

  Both sides are reduced to letters and digits only, with all spacing and
  punctuation removed, because the reference text is stored that way - one
  unbroken string. The first version of this script compared word streams
  against it and reported "clean" while a whole quoted sentence naming a real
  club sat in docs/. A checker that cannot fail loudly is worse than none.

  Needs data/.handbook-text.txt, which is gitignored and built by ingest. If it
  is absent the check cannot run, and says so rather than passing quietly.

EXIT
  0  nothing found
  1  verbatim handbook text found, or the reference text is missing
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

REFERENCE = Path("data/.handbook-text.txt")

# Never checked: the corpus itself and anything deliberately kept private.
SKIP = re.compile(r"""
    ^data/raw/
  | ^data/\.handbook-text\.txt$
  | ^data/records-real\.jsonl$
  | ^out/judge.*\.csv$
  | ^docs/(findings-audit|refuse-sweep|judge-report-gated|judge-report-v2-gated)\.md$
  | ^tools/leak_check\.py$
  | \.(pdf|png|jpg|jpeg|zip|xlsx)$
""", re.X)

WORD = re.compile(r"[A-Za-z0-9$][A-Za-z0-9$'/.-]*")
NOT_ALNUM = re.compile(r"[^a-z0-9]+")

# A window has to clear both bars: enough words to be a quotation rather than a
# phrase, and enough characters that ordinary English will not collide.
MIN_CHARS = 40


def squash(text):
    """Letters and digits only. The reference text is stored with every space
    removed, so anything compared against it must be reduced the same way."""
    return NOT_ALNUM.sub("", text.lower())


def tracked(staged_only):
    cmd = (["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
           if staged_only else ["git", "ls-files"])
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    return [p for p in out.splitlines() if p and not SKIP.search(p)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--min-words", type=int, default=8)
    ap.add_argument("--max-report", type=int, default=4,
                    help="distinct hits printed per file")
    args = ap.parse_args()

    if not REFERENCE.exists():
        print(f"leak_check: {REFERENCE} not found, so nothing can be compared.")
        print("            Build it from the corpus, or pass over this check")
        print("            deliberately. It is not safe to treat as clean.")
        return 1

    ref = squash(REFERENCE.read_text(encoding="utf-8", errors="ignore"))
    if len(ref) < 10000:
        print(f"leak_check: {REFERENCE} squashed to only {len(ref)} characters, "
              f"which is too small to be the four handbooks. Refusing to "
              f"report clean on a reference that looks wrong.")
        return 1
    files = tracked(args.staged)
    if not files:
        return 0

    total = 0
    for path in files:
        p = Path(path)
        if not p.exists():
            continue
        try:
            raw = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        words = WORD.findall(raw)
        if len(words) < args.min_words:
            continue

        hits, i = [], 0
        n = args.min_words
        while i <= len(words) - n:
            window = squash(" ".join(words[i:i + n]))
            if len(window) >= MIN_CHARS and window in ref:
                # Extend so the report shows the whole quoted stretch rather
                # than the window that happened to find it.
                end = i + n
                while (end < len(words)
                       and squash(" ".join(words[i:end + 1])) in ref):
                    end += 1
                hits.append(" ".join(words[i:end]))
                i = end
            else:
                i += 1

        if hits:
            total += len(hits)
            print(f"\n{path}  —  {len(hits)} verbatim run(s)")
            for h in hits[:args.max_report]:
                show = h if len(h) < 150 else h[:147] + "..."
                print(f"    \"{show}\"")
            if len(hits) > args.max_report:
                print(f"    ... and {len(hits) - args.max_report} more")

    if total:
        print(f"\nFOUND {total} run(s) of verbatim handbook text in "
              f"{'staged' if args.staged else 'tracked'} files.")
        print("These are four other clubs' documents in a public repo.")
        return 1
    print(f"clean — no verbatim handbook text in "
          f"{len(files)} {'staged' if args.staged else 'tracked'} files "
          f"(runs of {args.min_words}+ words)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
