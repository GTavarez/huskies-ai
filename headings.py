"""Finding section headings in a document somebody else wrote.

    python headings.py data/raw/real/club-01.pdf        # see what it detects
    python headings.py data/raw/real/club-01.pdf --all  # see every line's score

Your Week 2 reader split on `^(\\d+)\\.\\s+(.+)$` because Northside numbered its
headings. I wrote Northside, so of course it did. A handbook written by a club
secretary in Word will use bold text, or ALL CAPS, or Title Case with no
punctuation, or a mix of all three in the same document — and bold is invisible
to text extraction.

So heading detection stops being a regex and becomes a judgement with evidence.
This module scores each line and lets you pick the threshold after looking at
real output, rather than guessing it in advance.

HOW TO USE IT
  1. Run it on each PDF with --all and read the scores.
  2. Pick a threshold where the real headings sit above and the body sits below.
  3. Pass that threshold to split_sections() from ingest.py.

If no threshold separates them cleanly on some document, that is a finding, not
a failure — write down which document and why, because it tells you what a real
ingestion pipeline has to handle before you promise anyone it works.
"""
import re
import sys

# Lines that are page furniture rather than content. Extend per document.
FURNITURE = re.compile(
    r"^(page\s+\d+|\d+\s*\|\s*page|\d+$|revised?\s|updated?\s|©|copyright|"
    r"www\.|http|.*\bconfidential\b)", re.I)

NUMBERED = re.compile(r"^(\d+(?:\.\d+)*)[.)]?\s+(\S.*)$")
LETTERED = re.compile(r"^([A-Z])[.)]\s+(\S.*)$")
LABELLED = re.compile(r"^(section|article|appendix|part|chapter)\s+[\dIVXA-Z]+\b[.:\s]*(.*)$", re.I)

# Words that almost never start a heading but very often start a sentence.
SENTENCE_STARTERS = {
    "the", "a", "an", "this", "these", "those", "it", "if", "when", "any",
    "all", "each", "players", "parents", "we", "you", "our", "in", "for",
    "please", "no", "there", "he", "she", "they",
}


def score_line(line, next_line=""):
    """Score a single line as a heading candidate. Returns (score, reasons).

    Positive evidence stacks; negative evidence subtracts. Nothing here is
    certain — that is the point. A score is something you can threshold and
    argue with, a boolean is something you have to trust."""
    s = line.strip()
    reasons = []
    score = 0

    if not s:
        return 0, ["blank"]
    if FURNITURE.match(s):
        return -99, ["furniture"]

    words = s.split()
    letters = [c for c in s if c.isalpha()]

    if NUMBERED.match(s):
        score += 4
        reasons.append("numbered")
    elif LETTERED.match(s):
        score += 3
        reasons.append("lettered")
    if LABELLED.match(s):
        score += 4
        reasons.append("labelled")

    if letters and all(c.isupper() for c in letters) and len(words) >= 2:
        score += 3
        reasons.append("ALL CAPS")

    # Title Case: most words capitalised, and not a sentence.
    caps = sum(1 for w in words if w[:1].isupper())
    if len(words) >= 2 and caps >= max(2, int(0.7 * len(words))):
        score += 2
        reasons.append("Title Case")

    if len(s) <= 60:
        score += 1
        reasons.append("short")
    if len(s) > 90:
        score -= 3
        reasons.append("long line")

    if not s.endswith((".", ",", ";", "?", "!")):
        score += 1
        reasons.append("no terminal punctuation")
    elif not NUMBERED.match(s):
        score -= 2
        reasons.append("ends like a sentence")

    if s.endswith(":") and len(s) <= 60:
        score += 1
        reasons.append("ends with colon")

    if words and words[0].lower() in SENTENCE_STARTERS and not NUMBERED.match(s):
        score -= 3
        reasons.append("sentence opener")

    # A heading is usually followed by prose, not by another short line.
    if next_line and len(next_line.strip()) > 80:
        score += 1
        reasons.append("followed by prose")

    return score, reasons


def find_headings(lines, threshold=5):
    """Indices of lines that score at or above the threshold."""
    out = []
    for i, line in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        sc, _ = score_line(line, nxt)
        if sc >= threshold:
            out.append(i)
    return out


def split_sections(text, threshold=5, min_body_chars=40):
    """Split extracted text into (title, body) pairs on detected headings.

    Anything before the first heading is dropped — on a real handbook that is
    the cover page and the contents, and neither is retrievable content.

    A section whose body is shorter than min_body_chars is merged into the one
    before it. That catches a contents page whose entries all score as headings:
    without this, a 20-line contents page becomes 20 empty sections."""
    lines = [l.strip() for l in text.split("\n")]
    idx = find_headings(lines, threshold)
    if not idx:
        return []

    sections = []
    for n, start in enumerate(idx):
        end = idx[n + 1] if n + 1 < len(idx) else len(lines)
        title = lines[start]
        body = " ".join(l for l in lines[start + 1:end] if l and not FURNITURE.match(l))
        body = " ".join(body.split())

        m = NUMBERED.match(title) or LETTERED.match(title) or LABELLED.match(title)
        if m and m.lastindex and m.group(m.lastindex).strip():
            title = m.group(m.lastindex).strip()

        if body and len(body) < min_body_chars and sections:
            sections[-1] = (sections[-1][0],
                            (sections[-1][1] + " " + title + " " + body).strip())
            continue
        sections.append((title, body))
    return sections



# ---------------------------------------------------------------------------
# The signal the text throws away
# ---------------------------------------------------------------------------
# Everything above works on plain extracted text, which is all `extract_text()`
# gives you — and it is why the Title Case case is hard. In the PDF itself the
# heading is 12pt Helvetica-Bold and the body is 10pt Helvetica. That difference
# is sitting right there in the file and plain extraction discards it.
#
# pypdf will hand it over if you ask. This is the technique to reach for on any
# document where the visual layout carries meaning the words do not.

def lines_with_font(path):
    """[(text, font_size, font_name)] for every non-empty run in the PDF."""
    from pypdf import PdfReader
    out = []

    def visitor(text, cm, tm, font_dict, font_size):
        t = (text or "").strip()
        if t:
            name = str((font_dict or {}).get("/BaseFont", ""))
            out.append((t, float(font_size or 0), name))

    for page in PdfReader(path).pages:
        page.extract_text(visitor_text=visitor)
    return out


def body_size(runs):
    """The most common font size — the body text, by definition."""
    from collections import Counter
    sizes = Counter(round(fs, 1) for _, fs, _ in runs if fs)
    return sizes.most_common(1)[0][0] if sizes else 0


def split_sections_by_font(path, min_body_chars=40):
    """Split on font evidence: a run that is larger than the body, or bold at
    body size, starts a new section.

    Far more reliable than text heuristics when it works, and it does not work
    at all on a scanned handbook, where every page is an image and there are no
    font runs to read. Check which kind you have before promising anything."""
    runs = lines_with_font(path)
    if not runs:
        return []
    base = body_size(runs)

    sections, cur_title, cur_body = [], None, []
    for text, size, font in runs:
        if FURNITURE.match(text):
            continue
        bold = "bold" in font.lower() or "black" in font.lower()
        is_head = (size > base + 0.5) or (bold and size >= base)
        if is_head and len(text) <= 80:
            if cur_title is not None:
                sections.append((cur_title, " ".join(" ".join(cur_body).split())))
            cur_title, cur_body = text, []
        elif cur_title is not None:
            cur_body.append(text)
    if cur_title is not None:
        sections.append((cur_title, " ".join(" ".join(cur_body).split())))

    merged = []
    for t, b in sections:
        if b and len(b) < min_body_chars and merged:
            merged[-1] = (merged[-1][0], (merged[-1][1] + " " + t + " " + b).strip())
        else:
            merged.append((t, b))
    return merged


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__.strip().split("\n\n")[0])
    path = sys.argv[1]
    show_all = "--all" in sys.argv

    from pypdf import PdfReader
    text = "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
    lines = [l.strip() for l in text.split("\n")]

    print(f"{path}\n{len(lines)} lines extracted\n")
    shown = 0
    for i, line in enumerate(lines):
        if not line:
            continue
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        sc, why = score_line(line, nxt)
        if show_all or sc >= 3:
            flag = "HEAD" if sc >= 5 else "    "
            print(f"{flag} {sc:>3}  {line[:70]:<70} {','.join(why)}")
            shown += 1
    if not shown:
        print("nothing scored above 3 — this document's headings do not look like "
              "headings to the extractor. Open the PDF and see whether they are "
              "images, or bold-only with no other signal.")

    secs = split_sections(text)
    print(f"\nTEXT heuristics at threshold 5 -> {len(secs)} sections:")
    for t, b in secs:
        print(f"  {len(b):>5} chars  {t[:60]}")

    try:
        fsecs = split_sections_by_font(path)
        runs = lines_with_font(path)
        print(f"\nFONT evidence (body text is {body_size(runs)}pt) -> {len(fsecs)} sections:")
        for t, b in fsecs:
            print(f"  {len(b):>5} chars  {t[:60]}")
        print("\nIf the two disagree, trust the font pass and say so in the week")
        print("note. If the font pass returns nothing, the PDF is probably scanned")
        print("images and needs OCR before any of this applies.")
    except Exception as e:
        print(f"\nfont pass unavailable: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
