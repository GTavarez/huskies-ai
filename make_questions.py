"""Week 5 step 1 — write the questions BEFORE you run any retriever.

    python make_questions.py              # author, resumable
    python make_questions.py --review     # read back what you have written
    python make_questions.py --coverage   # which categories are still thin

WHY THIS EXISTS
  Four hand reviews produced four different numbers on the same corpus, because
  "would this answer a parent's question on its own" is a judgement, and a
  judgement drifts between sittings. This replaces it with something a machine
  can score the same way every time:

      a question, the verified answer, and the exact strings that must appear
      in any record that honestly answers it.

  Once those exist, "self-contained" stops being an opinion. A record is
  self-contained for a question if it contains all the answer keys. That number
  is the same on Tuesday and on Friday.

THE RULE THAT MAKES IT WORTH ANYTHING
  Write the question first, from what a parent would ask. Do NOT go looking
  through the records for something that would make a nice question. In Week 3
  the eval hardcoded which document to retrieve, so when the chunking changed
  the eval could not see it. An eval written FROM the chunks has the same
  disease in a subtler form: it can only ever ask what the chunker already
  happens to answer well.

  Ask what a parent asks. Let the corpus fail.

ANSWER KEYS
  The short, exact strings that must be present. Prefer numbers, names and
  amounts over phrases — they survive rewording.

      question   : How much are league fees?
      answer     : MMYSL is $525 and MSPSP is $675
      keys       : $525, $675
      document   : club-04

  Two keys means BOTH must appear. If either alone would answer it, write two
  separate questions instead.

MUST-REFUSE CASES
  Five of the twenty-five should be questions a parent might reasonably ask that
  these documents DO NOT answer. A system that never refuses is not safe to put
  in front of a parent, and a metric with no refusal cases cannot tell the
  difference between a good retriever and one that always returns something.

OUTPUT
  data/questions-real.jsonl   (append-only; safe to stop and resume)
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

OUT = Path("data/questions-real.jsonl")

# Not a checklist to complete in order — a spread to check yourself against, so
# twenty-five questions do not all turn out to be about fees.
CATEGORIES = [
    ("money",        "fees, payment plans, refunds, what is and is not included"),
    ("registration", "joining, trials, age groups, deadlines, paperwork"),
    ("kit",          "uniforms, equipment, what to bring, where to buy"),
    ("schedule",     "season dates, practice and game format, field locations"),
    ("conduct",      "sideline behaviour, discipline, what gets you asked to leave"),
    ("safety",       "injuries, concussion, heading rules, medical forms"),
    ("volunteering", "required hours, roles, coaching, how to sign up"),
    ("conflict",     "complaints, who to contact first, escalation"),
]


def ask(prompt, lower=False):
    """Prompt and read one line. Explicit flush — Git Bash does not flush
    input()'s prompt, so it arrives after the answer."""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    line = sys.stdin.readline()
    if not line:
        return ""
    line = line.strip()
    return line.lower() if lower else line


RAW = Path("data/raw/real")
CACHE = Path("data/.handbook-text.txt")


def handbook_text():
    """Every word of the four PDFs, squashed, cached.

    Checked against the SOURCE DOCUMENTS, not against data/records-real.jsonl.
    That distinction is the whole design. Verifying keys against the records
    would let you adjust a key until it matched a chunk, and the `answerable`
    metric — which exists to catch answers that no single chunk contains — would
    read 100% forever. Verifying against the PDF only confirms you copied the
    words correctly. Whether the chunker kept them together is precisely what
    the eval is for, and it stays unknown until you run it."""
    if CACHE.exists():
        return CACHE.read_text(encoding="utf-8")
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    parts = []
    for pdf in sorted(RAW.glob("*.pdf")):
        try:
            parts += [p.extract_text() or "" for p in PdfReader(pdf).pages]
        except Exception as e:
            print(f"  (could not read {pdf.name}: {e})")
    blob = "".join("".join(" ".join(parts).split())).lower()
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(blob, encoding="utf-8")
    return blob


def key_report(keys, blob):
    """How many times each key appears across the four handbooks.

    Zero means you did not copy it from a document — you wrote what you assumed
    the answer was. A key that is not in the source cannot be found by any
    retriever, and a question scored against it measures nothing.

    A very high count means the key is not distinctive. `Yes` and `Website` both
    appear all over four handbooks about entirely different things; a record
    containing one of them has not answered anything."""
    out = []
    for k in keys:
        n = blob.count("".join(k.split()).lower()) if blob else -1
        # Rarity is not the only thing that makes a key good. `Yes` happens to
        # occur twice in these four handbooks, so it passes any frequency test —
        # and a record containing `Yes` has still answered nothing. A key has to
        # carry the answer, which in practice means a number, an amount, a name,
        # or a phrase long enough to be unambiguous.
        bare = "".join(k.split())
        vague = (len(k.split()) < 2 and len(bare) < 6
                 and not any(c.isdigit() or c in "$£€" for c in bare))
        verdict = ("MISSING" if n == 0 else
                   "too vague" if vague else
                   "too common" if n > 15 else
                   "ok")
        out.append((k, n, verdict))
    return out


def load():
    if not OUT.exists():
        return []
    return [json.loads(l) for l in open(OUT, encoding="utf-8") if l.strip()]


def append(row):
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def coverage(rows):
    have = Counter(r["category"] for r in rows)
    refusals = sum(1 for r in rows if r["expect"] == "refuse")
    print(f"\n{len(rows)} questions written — {refusals} of them must-refuse\n")
    for key, blurb in CATEGORIES:
        bar = "#" * have.get(key, 0)
        print(f"  {key:<13} {have.get(key, 0):>2}  {bar:<8}  {blurb}")
    if len(rows) >= 25:
        print("\nTwenty-five is the target. More is fine; fewer makes every "
              "percentage move by four points at a time.")
    if refusals < 5:
        print(f"\nOnly {refusals} must-refuse cases. Aim for 5 — a retriever "
              "that always returns something scores well without them.")


def review(rows):
    for i, r in enumerate(rows, 1):
        tag = "REFUSE" if r["expect"] == "refuse" else r.get("document", "?")
        print(f"\n[{i}] ({r['category']} · {tag})  {r['question']}")
        print(f"     answer : {r['answer'] or '—'}")
        print(f"     keys   : {', '.join(r['keys']) if r['keys'] else '—'}")


def collect_keys(blob):
    """Ask for answer keys until they are keys you could actually score.

    Returns a list of keys, or None if the question turned out to be one the
    handbooks do not answer — which is not a failure. A question you believed was
    answerable and then could not find is the most honest must-refuse case there
    is, because you did not invent it to pad the count."""
    while True:
        raw = ask("  answer keys — exact strings that must appear, "
                  "comma separated\n  > ")
        keys = [k.strip() for k in raw.split(",") if k.strip()]
        if not keys:
            print("    at least one key, or this question cannot be scored.")
            continue

        report = key_report(keys, blob)
        for k, n, verdict in report:
            flag = {"ok": "     ", "MISSING": "  !! ",
                    "too common": "  ?  ", "too vague": "  ?  "}[verdict]
            count = n if n >= 0 else "?"
            print(f"{flag}{k!r:<26} appears {count} times across the four "
                  f"handbooks   {verdict}")

        if any(v == "MISSING" for _, _, v in report):
            print("    A key that appears nowhere in the four handbooks means the\n"
                  "    answer came from you, not from the documents. Open the PDF,\n"
                  "    find the sentence, copy the words exactly.")
            if ask("    [Enter] retype  ·  [r] no answer exists, make it a "
                   "refuse case: ", lower=True).startswith("r"):
                return None
            continue

        if any(v in ("too common", "too vague") for _, _, v in report):
            print("    Those keys are not distinctive — a record containing them\n"
                  "    has not necessarily answered anything. Prefer a number, an\n"
                  "    amount, a name, or a longer exact phrase.")
            if ask("    keep them anyway? [y/N] ", lower=True) != "y":
                continue

        return keys


def author(rows):
    print(__doc__.split("ANSWER KEYS")[0].rstrip())
    blob = handbook_text()
    if not blob:
        print("\n  (could not read data/raw/real/*.pdf — keys will not be checked)")
    print("=" * 74)
    print("Enter on an empty question to stop. Everything is saved as you go.")
    print("=" * 74)

    while True:
        coverage(rows)
        print("\n" + "-" * 74)
        q = ask("\nquestion a parent would ask (empty to stop)\n  > ")
        if not q:
            break

        names = [k for k, _ in CATEGORIES]
        cat = ""
        while cat not in names:
            cat = ask(f"  category [{'/'.join(names)}]: ", lower=True)
            if cat and cat not in names:
                print("    one of those words, exactly.")

        expect = ""
        while expect not in ("a", "r"):
            expect = ask("  do the handbooks answer it?  [a]nswerable / [r]efuse: ",
                         lower=True)

        qid = f"q{len(rows)+1:02d}"
        keys = None
        answer = ""
        if expect == "a":
            answer = ask("  the answer, COPIED from the handbook\n  > ")
            keys = collect_keys(blob)

        if keys:
            doc = ask("  which document holds it (club-01..04, or ? if unsure): ")
            row = {"qid": qid, "category": cat, "question": q,
                   "expect": "answerable", "answer": answer, "keys": keys,
                   "document": doc, "note": ""}
        else:
            if expect == "a":
                note = "believed answerable; no supporting text found in the handbooks"
                print("    Recorded as a refuse case — and a good one.")
            else:
                note = ""
                while len(note) < 10:
                    note = ask("  why should it refuse? (a sentence, not a letter) ")
                    if len(note) < 10:
                        print("    What would a parent want here that these four\n"
                              "    handbooks genuinely do not contain? In six months\n"
                              "    this note is the only thing explaining the case.")
            row = {"qid": qid, "category": cat, "question": q, "expect": "refuse",
                   "answer": "", "keys": [], "document": "", "note": note}

        append(row)
        rows.append(row)
        print(f"  saved {row['qid']}.")

    print(f"\n{len(rows)} questions in {OUT}.")
    if len(rows) >= 25:
        print("Now run:  python retrieval_eval.py")


def drop(rows, n):
    """Remove the last n questions. The file is append-only by design, so this
    is the only way to take something back — and taking a bad question back is
    better than leaving it in to quietly move a percentage."""
    keep = rows[:-n] if n < len(rows) else []
    with open(OUT, "w", encoding="utf-8") as f:
        for r in keep:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"dropped {len(rows) - len(keep)}; {len(keep)} remain.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", action="store_true")
    ap.add_argument("--coverage", action="store_true")
    ap.add_argument("--drop", type=int, metavar="N",
                    help="remove the last N questions")
    args = ap.parse_args()

    rows = load()
    if args.drop:
        drop(rows, args.drop)
    elif args.review:
        review(rows)
    elif args.coverage:
        coverage(rows)
    else:
        author(rows)


if __name__ == "__main__":
    main()
