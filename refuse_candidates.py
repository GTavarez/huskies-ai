"""Sweep candidate must-refuse questions against the full handbook text.

    python refuse_candidates.py                       # sweep docs/refuse-candidates.txt
    python refuse_candidates.py --all-snippets        # every hit, not the first six
    python refuse_candidates.py --pad 400             # wider context

WHY THIS EXISTS
  A `refuse` label is a claim that the four handbooks do not answer a question.
  That is a claim about ABSENCE, and a ranked retriever cannot establish one: it
  returns its best five records whether or not an answer exists anywhere.

  Reading a failed search as proof of absence is the single mistake this repo
  has made most. It produced five mislabelled eval rows (q04, q21, q29 and two
  others), and two false findings that went into the week notes:

    "no handbook addresses injuries"   -> club-02 rule 14 says what to do
    "no concussion procedure anywhere" -> club-04 has a titled section, page 10

  Both survived because nobody read the documents; a top-5 had come back empty
  and that was treated as an answer. So this script does not rank anything. It
  counts exact strings over the full text of all four PDFs and prints every
  passage, and the verdict column is left blank for a person to fill in.

  A count is not a verdict. Zero hits is not a verdict either — it is only as
  good as the term list, which is why the terms searched are printed above the
  result for every candidate. A candidate that comes back clean on three terms
  and was never searched for the word the handbook actually uses is a label
  waiting to be flipped in Week 9.

INPUT   docs/refuse-candidates.txt
          One candidate per line. Blank lines and #-comments ignored.
          Terms are derived from the question's content words; add any the
          handbooks might use instead after a pipe:

            What time do Saturday games start? | kick off, kickoff, 9:00, am
            Who is the club's insurance carrier? | insurance, liability, policy

OUTPUT  docs/refuse-sweep.md   (gitignored — it quotes the handbooks)
"""
import argparse
import re
from pathlib import Path

RAW = Path("data/raw/real")
OUT = Path("docs/refuse-sweep.md")
CANDIDATES = Path("docs/refuse-candidates.txt")

# Dropped before deriving terms. Deliberately short: a question's rare words are
# the point, and an over-eager stop list is how a term list ends up too thin to
# prove anything.
STOP = {
    "a", "about", "an", "and", "any", "anyone", "are", "as", "at", "be",
    "can", "do", "does", "for", "from", "get", "has", "have", "how", "i",
    "if", "in", "is", "it", "many", "me", "much", "my", "need", "of", "on",
    "or", "our", "should", "someone", "that", "the", "their", "there",
    "they", "this", "to", "we", "what", "when", "where", "which", "who",
    "whom", "why", "will", "with", "you", "your",
}

DOTS = re.compile(r"\.{6,}")          # a table-of-contents line
WORD = re.compile(r"[a-z0-9][a-z0-9'-]*")

_COMPILED = {}


def matcher(term):
    """Whole-word match for a term, cached.

    Substring counting is not safe here: 'ein' found ten hits in club-01 and
    every one of them was the middle of 'being'. A short term that silently
    matches inside longer words sends a reader off to check ten passages that
    say nothing, which is the opposite of what this script is for.

    A boundary is only asserted where the term's own edge is a word character,
    so 'a.m.' and '501(c)' still match as written.
    """
    if term not in _COMPILED:
        head = r"\b" if term[:1].isalnum() else ""
        tail = r"\b" if term[-1:].isalnum() else ""
        body = re.escape(term)
        # A plural the term list did not anticipate is still the passage you
        # need to read. Boundaries alone turned 'sister' into zero hits in a
        # handbook that says 'brothers and sisters', which is exactly the kind
        # of false absence this script exists to prevent. Recall matters more
        # than precision here: every hit gets read anyway.
        if tail and len(term) > 3 and term.isalpha():
            body += "(?:e?s)?"
        _COMPILED[term] = re.compile(head + body + tail)
    return _COMPILED[term]


def count(low, term):
    return len(matcher(term).findall(low))


def load():
    """Full text of each real handbook, one flat string per club."""
    from pypdf import PdfReader
    if not RAW.exists():
        raise SystemExit(f"{RAW} not found — the four real PDFs live there")
    out = {}
    for pdf in sorted(RAW.glob("*.pdf")):
        out[pdf.stem] = " ".join(
            " ".join((p.extract_text() or "").split()) for p in PdfReader(pdf).pages)
    if not out:
        raise SystemExit(f"no PDFs in {RAW}")
    return out


def parse_line(line):
    """'question | extra, terms' -> (question, [terms])."""
    question, _, extra = line.partition("|")
    question = question.strip()
    given = [t.strip().lower() for t in extra.split(",") if t.strip()]
    derived = [w for w in WORD.findall(question.lower())
               if w not in STOP and len(w) > 2]
    # A singular form so 'tryouts' also finds 'tryout'. Only ever shortens.
    stems = [w[:-1] for w in derived
             if w.endswith("s") and len(w) > 4 and w[-2:-1].isalnum()]
    terms, seen = [], set()
    for t in given + derived + stems:
        if t not in seen:
            seen.add(t)
            terms.append(t)
    return question, terms


def read_candidates():
    if not CANDIDATES.exists():
        raise SystemExit(
            f"{CANDIDATES} not found. One candidate question per line;\n"
            f"see the docstring at the top of this file for the format.")
    out = []
    for raw in CANDIDATES.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            out.append(parse_line(line))
    if not out:
        raise SystemExit(f"{CANDIDATES} has no candidates in it")
    return out


def snippets(flat, term, pad):
    """Every occurrence with context. Contents-page lines dropped."""
    low = flat.lower()
    seen, out = set(), []
    for m in matcher(term).finditer(low):
        a, b = max(0, m.start() - pad), min(len(flat), m.end() + pad)
        snip = flat[a:b].strip()
        if DOTS.search(snip):
            continue
        key = snip[:60]
        if key in seen:
            continue
        seen.add(key)
        out.append(snip)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pad", type=int, default=260,
                    help="characters of context either side of a hit")
    ap.add_argument("--all-snippets", action="store_true",
                    help="print every passage, not the first six per club")
    ap.add_argument("--cap", type=int, default=40,
                    help="a term appearing more than this many times across "
                         "the corpus cannot localise anything; its count is "
                         "reported but its passages are not printed")
    args = ap.parse_args()

    texts = load()
    cands = read_candidates()
    cap = None if args.all_snippets else 6

    doc = [
        "# Must-refuse sweep — candidates, every passage, no verdicts\n",
        "Exact-string counts over the **full text** of all four handbooks, not a",
        "ranked search. Table-of-contents lines are dropped: a contents entry",
        "proves a topic is listed, not that a passage answers anything.\n",
        "**A count is not a verdict and zero is not a verdict.** Zero hits is only",
        "as good as the term list printed under each candidate. Read the passages,",
        "then write KEEP (the handbooks genuinely do not answer this) or DROP (they",
        "do) on the verdict line, with the club and the sentence that decided it.\n",
    ]

    for question, terms in cands:
        print("=" * 74)
        print("CANDIDATE:", question)
        print("  terms:", ", ".join(terms))
        doc += [f"\n---\n\n## {question}\n",
                f"**terms searched** — `{'` · `'.join(terms)}`\n"]

        total = 0
        per_club = {}
        for club, flat in texts.items():
            low = flat.lower()
            hits = {t: n for t in terms if (n := count(low, t))}
            per_club[club] = hits
            total += sum(hits.values())

        # A term that appears everywhere localises nothing. "child" x169 in a
        # parent handbook is not evidence about any question; printing its
        # passages buries the rare term that actually decides the label.
        corpus = {t: sum(h.get(t, 0) for h in per_club.values()) for t in terms}
        common = {t for t, n in corpus.items() if n > args.cap}
        rare_total = total - sum(corpus[t] for t in common)
        if common:
            shown = ", ".join(f"{t}x{corpus[t]}" for t in
                              sorted(common, key=corpus.get, reverse=True))
            print(f"  too common to localise: {shown}")
            doc.append(f"_Too common to localise, passages not printed_ — "
                       f"{shown}\n")

        row = "  ".join(
            f"{c}:{sum(n for t, n in h.items() if t not in common)}"
            for c, h in per_club.items()) or "—"
        print("  totals:", row)
        doc.append(f"**mentions** — {row}\n")

        if rare_total == 0:
            print("  NO MENTION OF ANY LOCALISING TERM IN ANY HANDBOOK.")
            print("  -> strongest candidate shape. Check the term list is not "
                  "the reason.")
            doc += ["_No mention of any term in any handbook._ Strongest shape "
                    "there is — but check the term list above is not the reason. "
                    "What word would the handbook use that is not in it?\n",
                    "\n**verdict:** \n"]
            continue

        for club, hits in per_club.items():
            if not hits:
                doc.append(f"\n### {club} — no mention of any term\n")
                continue
            informative = {t: n for t, n in hits.items() if t not in common}
            if not informative:
                doc.append(f"\n### {club} — only terms too common to "
                           f"localise\n")
                continue
            doc.append(f"\n### {club}\n")
            for term in sorted(informative, key=informative.get, reverse=True):
                got = snippets(texts[club], term, args.pad)
                if not got:
                    doc.append(f"- `{term}` ×{hits[term]} — contents-page hits "
                               f"only\n")
                    continue
                shown = got if cap is None else got[:cap]
                doc.append(f"\n**`{term}` ×{hits[term]}**\n")
                for s in shown:
                    doc.append(f"\n> …{s}…\n")
                if len(got) > len(shown):
                    doc.append(f"\n_{len(got) - len(shown)} further passages "
                               f"not shown — `--all-snippets` for all of them._\n")
            print(f"  {club}: " + (", ".join(
                f"{t}x{n}" for t, n in sorted(informative.items(),
                                              key=lambda kv: -kv[1]))
                or "nothing that localises"))

        doc.append("\n**verdict:** \n")
        print()

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(doc), encoding="utf-8")
    print("=" * 74)
    print(f"wrote {OUT}  ({len(cands)} candidates)")
    print("\nRead it. A candidate becomes a question only after you have read "
          "every\npassage under it. Five that survive is the target; the ones "
          "that do not\nsurvive are worth as much, because they are the labels "
          "you did not ship.")


if __name__ == "__main__":
    main()
