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
# Page furniture. Widened after four real handbooks: the first version anchored
# everything to the start of the line, so it caught `Page 3` and missed
# `The Maine Center for Sport and Coaching ... Page 7`. It also had nothing for
# a contents dot-leader, which is why `PARENT COPY ...............` survived.
FURNITURE = re.compile(
    r"(^\s*\d+\s*$"                      # a bare page number
    r"|\bpage\s+\d+\b"                   # a page marker anywhere in the line
    r"|\d+\s*\|\s*page"
    r"|^\s*(revised?|updated?|effective)\s"
    r"|©|copyright|www\.|https?://"
    r"|\.{6,}"                            # contents dot leaders
    r"|^[\W_]+$"                           # a line that is only punctuation
    r"|\bconfidential\b)", re.I)

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
    if FURNITURE.search(s):
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
        body = " ".join(l for l in lines[start + 1:end] if l and not FURNITURE.search(l))
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

def compose(cm, tm):
    """Where a text run actually lands on the page, and how big it actually is.

    A PDF positions text with the text matrix (tm), but content inside a form
    XObject is additionally transformed by the current transformation matrix
    (cm). Ignore cm and everything inside those XObjects reports the same few
    coordinates. Scaling lives in the matrices too, which is why club-02
    reported every font as size 1.0 — the real size was tm's scale factor."""
    import math
    cm = [float(v) for v in (cm or [1, 0, 0, 1, 0, 0])]
    tm = [float(v) for v in (tm or [1, 0, 0, 1, 0, 0])]
    x = cm[0] * tm[4] + cm[2] * tm[5] + cm[4]
    y = cm[1] * tm[4] + cm[3] * tm[5] + cm[5]
    # Area scale of each matrix; sqrt gives the linear factor.
    det = abs(tm[0] * tm[3] - tm[1] * tm[2]) * abs(cm[0] * cm[3] - cm[1] * cm[2])
    return x, y, math.sqrt(det) if det > 0 else 1.0


def squash(s):
    """Drop every space and lowercase. Used to compare two extractions of the
    same words that disagree only about where the spaces go."""
    return "".join(s.split()).lower()


def squash_index(s):
    """(squashed string, index back into the original for each character).

    Lets you find a run of characters ignoring whitespace, then recover the
    original slice — spaces and all — rather than the squashed one."""
    out, idx = [], []
    for i, ch in enumerate(s):
        if not ch.isspace():
            out.append(ch.lower())
            idx.append(i)
    return "".join(out), idx


def respace(line, sq, idx, plain, cursor):
    """Give a font-pass line the spacing pypdf's own extractor found.

    The font pass reconstructs a line from its text-showing operators, and a PDF
    does not store the space between two words as a space character — it stores a
    jump in x. Estimating the jump from character counts under-inserts on some
    fonts and over-inserts on others, which is where `Respectand Responsibility`
    and `MPSCutilizesSoccerVillage` came from: 14 of 20 reviewed records were
    rejected for spacing, not for structure.

    pypdf's extract_text already solves this properly, using the real positional
    offsets. So: find this line in the plain text with the spaces removed from
    BOTH sides, then return the plain text's own version of that span. The font
    pass keeps its job — grouping runs into lines, and reporting size and weight —
    and stops guessing at something already known.

    Returns (text, new_cursor). No match leaves the line untouched: a document
    whose two extraction paths disagree degrades to the old behaviour instead of
    losing the line."""
    key = squash(line)
    if not key:
        return line, cursor
    pos = sq.find(key, cursor)
    if pos < 0:                      # out of order, or only on an earlier page
        pos = sq.find(key)
    if pos < 0:
        return line, cursor
    start, end = idx[pos], idx[pos + len(key) - 1] + 1
    return " ".join(plain[start:end].split()), pos + len(key)


def lines_with_font(path):
    """One entry per LINE, not per run: (text, max_size, all_bold, page).

    The first version of this returned one entry per text-showing operator and
    joined them with spaces. That was wrong twice over. PDFs split single words
    across operators for kerning, so you get `an d body`; and they pack several
    words into one operator, so you get `thereferees`. Grouping by baseline
    (the y translation in the text matrix) reconstructs real lines.

    `all_bold` is the field that matters. A line where EVERY run is bold is a
    heading. A line with some bold runs and some not is a sentence with emphasis
    in it — which is what `**Encourage your child**, regardless of...` is, and
    what the previous version sawed in half."""
    from collections import defaultdict
    from pypdf import PdfReader

    pages = []
    for page in PdfReader(path).pages:
        runs = defaultdict(list)

        def visitor(text, cm, tm, font_dict, font_size, _runs=runs):
            t = text or ""
            if not t.strip():
                return
            # tm alone is the text-space position. Anything drawn inside a form
            # XObject is ALSO transformed by cm, and real handbooks are full of
            # form XObjects. Using tm[5] alone made every page of club-02
            # collapse onto seventeen shared y values — 279 KB of text reduced
            # to seventeen "lines", all of them the running header.
            x, y, scale = compose(cm, tm)
            name = str((font_dict or {}).get("/BaseFont", "")).lower()
            bold = "bold" in name or "black" in name or "heavy" in name
            _runs[round(y, 1)].append((x, t, float(font_size or 0) * scale, bold))

        plain = page.extract_text(visitor_text=visitor) or ""
        sq, idx = squash_index(plain)
        cursor = 0
        for y in sorted(runs, reverse=True):          # top of page downwards
            parts = sorted(runs[y], key=lambda r: r[0])
            raw = "".join(p[1] for p in parts)
            text, cursor = respace(raw, sq, idx, plain, cursor)
            if not text.strip():
                continue
            pages.append((text, max(p[2] for p in parts), all(p[3] for p in parts)))
    return pages


def body_size(lines):
    """The most common font size — the body text, by definition."""
    from collections import Counter
    sizes = Counter(round(size, 1) for _, size, _ in lines if size)
    return sizes.most_common(1)[0][0] if sizes else 0


def heading_keys(path, max_chars=80):
    """The set of lines that font evidence says are headings, normalised for
    matching against plainly-extracted text."""
    lines = lines_with_font(path)
    if not lines:
        return set(), 0
    base = body_size(lines)

    keys = set()
    for text, size, all_bold in lines:
        if not text or len(text) > max_chars or FURNITURE.search(text):
            continue
        bigger = size > base + 0.5
        if bigger or all_bold:
            keys.add(norm(text))
    return keys, base


def norm(s):
    """Spaces are where the two extraction paths disagree, so compare without
    them. `Kit and Equipment` and `Kitand Equipment` are the same heading."""
    return "".join(s.split()).lower()


def split_sections_by_font(path, min_body_chars=40, threshold=5):
    """One pass over the plainly-extracted text, scored with BOTH signals.

    An earlier version used font evidence as the sole splitter and matched the
    two extraction paths by exact string. That is a brittle join: any difference
    in how the paths break lines kills the match. On four real handbooks it took
    239 records down to 60 — better on two documents, catastrophic on the other
    two, one of which produced nothing at all.

    So font evidence is now a SIGNAL worth +4 on a line's heading score, not a
    verdict. When the font pass works the score clears the threshold easily.
    When the PDF defeats it — scanned pages, unreadable matrices, a document set
    entirely in one font — the text heuristics still carry the split, and the
    output degrades instead of vanishing.

    That is the actual lesson of this module: on documents you did not write,
    prefer several weak signals that fail independently over one strong signal
    that fails completely."""
    try:
        font_lines = lines_with_font(path)
    except Exception:
        font_lines = []

    if font_lines:
        base = body_size(font_lines)
        lines = [t for t, _, _ in font_lines]
        # Font evidence per line, computed once alongside the text.
        boost = [4 if ((size > base + 0.5) or all_bold) and len(t) <= 80 else 0
                 for t, size, all_bold in font_lines]
    else:
        # No readable font runs at all: scanned pages, or a producer pypdf
        # cannot follow. Fall back to plain text and text heuristics only.
        from pypdf import PdfReader
        text = "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
        lines = [l.strip() for l in text.split("\n")]
        boost = [0] * len(lines)

    sections, cur_title, cur_body = [], None, []
    for i, line in enumerate(lines):
        if not line or FURNITURE.search(line):
            continue
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        score, _why = score_line(line, nxt)
        score += boost[i]
        if score >= threshold and len(line) <= 90:
            if cur_title is not None:
                sections.append((cur_title, " ".join(" ".join(cur_body).split())))
            cur_title, cur_body = line, []
        elif cur_title is not None:
            cur_body.append(line)
    if cur_title is not None:
        sections.append((cur_title, " ".join(" ".join(cur_body).split())))

    merged = []
    for t, b in sections:
        # `if b and ...` here meant a section with an EMPTY body never merged —
        # the one case that most needed to. Cover-page lines, contents entries
        # and a heading whose text is on the next page all produce title-only
        # records, and those were the reviewed records marked `n` for "a heading
        # with no body". A body of zero characters is shorter than the floor, so
        # it belongs on the same side of the test as a body of ten.
        if len(b) < min_body_chars and merged:
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
