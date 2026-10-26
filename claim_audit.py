"""Audit the claims the week notes make ABOUT the four handbooks.

    python claim_audit.py            # counts + one snippet per club per claim
    python claim_audit.py --wide     # longer snippets

WHY THIS EXISTS
  The week notes assert things about the source documents — "no handbook tells a
  parent what to do about a concussion", "handbooks never state game times" —
  and those assertions are the saleable output of the project. They go in front
  of a club director who owns the document and can check them in ten seconds.

  Every one of them was produced the same way the five mislabelled eval rows
  were: a ranked search did not surface the passage, and absence of a result was
  read as absence from the document. That reasoning was wrong five times on the
  labels. It was wrong twice more on the claims:

    "no handbook addresses injuries"  -> club-02 rule 14 says exactly what to do
    "no concussion procedure anywhere" -> club-04 has a titled section, page 10

  So: exact-string search over the PDFs, counts per club, and the surrounding
  text printed so a claim is judged by reading rather than by a hit count. Two
  `scholarship` hits looked like a hardship provision and were about college
  scholarships.

  Table-of-contents lines are filtered out. A contents entry proves a topic is
  listed, not that a passage answers anything — the same distinction that
  invalidated a key back in Week 6.

OUTPUT
  docs/findings-audit.md
"""
import argparse
import re
from pathlib import Path

RAW = Path("data/raw/real")

CLAIMS = {
    "concussion procedure": ["concussion", "head injury"],
    "what to do if injured": ["injured", "injury"],
    "family cannot afford the fees": ["scholarship", "financial assistance",
                                      "hardship", "fee waiver", "reduced fee",
                                      "afford", "unable to pay"],
    "game start times": ["game time", "kick off", "kickoff", "games start",
                         "games begin"],
    "practice schedule": ["practice schedule", "twice per week",
                          "practice times", "practices are"],
    "game locations": ["home games", "away games", "directions to"],
    "tryout dates": ["tryout"],
    "parent meeting": ["meeting"],
    "uniform cost": ["uniform"],
    "tournament fees": ["tournament"],
}

DOTS = re.compile(r"\.{6,}")


def load():
    from pypdf import PdfReader
    out = {}
    for pdf in sorted(RAW.glob("*.pdf")):
        out[pdf.stem] = " ".join(
            " ".join((p.extract_text() or "").split()) for p in PdfReader(pdf).pages)
    return out


def snippets(flat, term, pad):
    """Occurrences with context, table-of-contents lines dropped."""
    low = flat.lower()
    seen, out = set(), []
    for m in re.finditer(re.escape(term), low):
        a, b = max(0, m.start() - pad), min(len(flat), m.end() + pad)
        snip = flat[a:b].strip()
        if DOTS.search(snip):          # a contents entry locates nothing
            continue
        if snip[:50] in seen:
            continue
        seen.add(snip[:50])
        out.append(snip)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wide", action="store_true")
    args = ap.parse_args()
    pad = 420 if args.wide else 230

    texts = load()
    lines = ["# Findings audit — do the claims about the handbooks hold?\n",
             "Exact-string search over the four source PDFs. Table-of-contents",
             "lines are excluded. A count is not a verdict; read the text.\n"]

    for claim, terms in CLAIMS.items():
        print("=" * 72); print("CLAIM:", claim)
        lines.append(f"\n## {claim}\n")
        counts = {}
        for club, flat in texts.items():
            low = flat.lower()
            counts[club] = {t: low.count(t) for t in terms if low.count(t)}
        row = "  ".join(f"{c}:{sum(v.values())}" for c, v in counts.items())
        print("  totals ", row)
        lines.append(f"totals — {row}\n")
        for club, flat in texts.items():
            if not counts[club]:
                continue
            term = max(counts[club], key=counts[club].get)
            got = snippets(flat, term, pad)
            if not got:
                print(f"  {club}: only contents-page hits for {term!r}")
                lines.append(f"- **{club}** — only table-of-contents hits "
                             f"for `{term}`\n")
                continue
            print(f"\n  [{club} · {term!r} x{counts[club][term]}]\n  ...{got[0]}...")
            lines.append(f"- **{club}** (`{term}` ×{counts[club][term]}) — "
                         f"{got[0]}\n")
        print()

    doc = Path("docs/findings-audit.md")
    doc.parent.mkdir(exist_ok=True)
    doc.write_text("\n".join(lines) + "\n\n## Verdict per claim\n\n"
                   "_One line each: holds / false / needs rewording, and the "
                   "comparative version if the absolute one does not survive. A "
                   "claim that goes to a club director has to be checkable by "
                   "that director in ten seconds._\n", encoding="utf-8")
    print(f"wrote {doc}")


if __name__ == "__main__":
    main()
