"""Hand-audit the model judge: is its verdict right?

    python judge_audit.py                  # 10 rows the judge actually ruled on
    python judge_audit.py --n 20
    python judge_audit.py --file out/judge-guards.csv

WHY THE OBVIOUS SAMPLE IS WRONG
  Reading the first ten rows of judge.csv audits the wrong thing. On any row
  where the model emitted the refusal sentence, `refusal_kind()` sets the
  verdict and the judge's opinion is discarded. Four of the first ten rows are
  refusals, so four of them exercise nothing.

  This samples only rows where the judge actually decided — SUPPORTED or
  UNSUPPORTED — which is the population whose error rate you want.

WHAT IT WILL NOT DO
  Tell you whether each verdict is right. A TA handing over a label table is
  how the Week 4 self-contained baseline was invalidated; the number stopped
  being a measurement and became a transcription.

  So: the answer, and what the handbooks actually say near it, side by side.
  The call is yours.
"""
import argparse
import csv
import json
import re
import textwrap
from pathlib import Path

RAW = Path("data/raw/real")
STOP = set("the a an and or of to in on at for with from by is are was were be "
           "you your our we they it this that there as not no can will would "
           "should may must please according documents club".split())


def handbooks():
    from pypdf import PdfReader
    out = {}
    for pdf in sorted(RAW.glob("*.pdf")):
        out[pdf.stem] = " ".join(
            " ".join((p.extract_text() or "").split()) for p in PdfReader(pdf).pages)
    return out


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", text) if len(s.strip()) > 25]


def evidence(answer, books, n=3):
    """Sentences in the source PDFs that share the most rare words with the
    answer. Rare because a sentence matching on `the` and `club` is noise."""
    aw = {w for w in re.findall(r"[a-z0-9$]+", answer.lower())
          if w not in STOP and len(w) > 2}
    if not aw:
        return []
    scored = []
    for club, text in books.items():
        for s in sentences(text):
            sw = set(re.findall(r"[a-z0-9$]+", s.lower()))
            hit = aw & sw
            if len(hit) >= 2:
                scored.append((len(hit) / (len(sw) ** 0.4 or 1), club, s))
    scored.sort(key=lambda x: -x[0])
    seen, out = set(), []
    for _, club, s in scored:
        if s[:40] in seen:
            continue
        seen.add(s[:40])
        out.append((club, s))
        if len(out) >= n:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="out/judge.csv")
    ap.add_argument("--n", type=int, default=10)
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.file, encoding="utf-8")))
    ruled = [r for r in rows if r["verdict"] in ("SUPPORTED", "UNSUPPORTED")
             and not r.get("refusal")]
    skipped = len(rows) - len(ruled)

    # Sample where the errors are, not where the file starts.
    #
    # Taking ruled[:10] returns ten rows in qid order, and on this set that is
    # ten `answerable` + SUPPORTED rows — the easiest cases in the file. The
    # judge's mistakes concentrate in two places instead: a refuse row it
    # called SUPPORTED (it endorsed an answer to a question the corpus cannot
    # answer), and any UNSUPPORTED verdict (it rejected something, and the
    # rejection may be wrong — that is how two verbatim quotes were thrown out
    # in Week 8).
    #
    # So: those first, then the ordinary rows spread across the whole file
    # rather than taken from the front, because questions written on the same
    # afternoon resemble each other.
    def priority(r):
        if r["expect"] == "refuse" and r["verdict"] == "SUPPORTED":
            return 0, r["qid"]          # the judge endorsed an unanswerable answer
        if r["verdict"] == "UNSUPPORTED":
            return 1, r["qid"]          # the judge rejected something
        return 2, r["qid"]

    ruled.sort(key=priority)
    head = [r for r in ruled if priority(r)[0] < 2]
    rest = [r for r in ruled if priority(r)[0] == 2]
    want = max(0, args.n - len(head))
    step = max(1, len(rest) // want) if want else 1
    sample = head[:args.n] + rest[::step][:want]

    print(f"{len(rows)} rows · {len(ruled)} the judge actually ruled on "
          f"· {skipped} refusals where its opinion was discarded")
    print(f"showing {len(sample)}: {len(head[:args.n])} where the judge is most "
          f"likely wrong, then {len(sample) - len(head[:args.n])} spread across "
          f"the rest\n")

    books = handbooks()
    for r in sample:
        print("=" * 74)
        flag = ""
        if r["expect"] == "refuse" and r["verdict"] == "SUPPORTED":
            flag = "   << judge endorsed an answer the corpus should not have"
        elif r["verdict"] == "UNSUPPORTED":
            flag = "   << judge rejected this one"
        print(f"{r['qid']}   expected {r['expect']}   "
              f"JUDGE SAID: {r['verdict']}{flag}")
        print(f"\nQ: {r['question']}")
        print("A: " + textwrap.fill(r["answer"][:420], 70, subsequent_indent="   "))
        ev = evidence(r["answer"], books)
        print("\n   what the handbooks say near this:")
        if not ev:
            print("     nothing close — which is itself worth noticing")
        for club, s in ev:
            print(f"     [{club}] " + textwrap.fill(s[:240], 66,
                                                    subsequent_indent="              "))
        print()
    print("=" * 74)
    print(f"  Read {len(sample)} rows. For each: did the judge get it right?")
    print("  Count the yeses. That count is the error bar on every judge number")
    print("  in this repo, and nothing else can supply it.")
    print("\n  Write it into docs/week-08.md next to 8/10 and 24/30.")


if __name__ == "__main__":
    main()
