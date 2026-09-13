"""Week 2 — turn three file formats into one record shape.

    python ingest.py

Reads everything in data/raw/ and writes data/records.jsonl, where every record
looks identical regardless of which format it came from. That uniformity is what
makes Week 5's chunking and embedding possible: the retrieval pipeline should
never know or care that one document was a PDF and another was a spreadsheet row.

WHAT YOU WRITE
  read_announcements_json()   TODO — the JSON is nested; content is two levels down
  read_handbook_pdf()         TODO — the hard one; page furniture pollutes the text

WHAT IS GIVEN
  read_faq_csv()              a worked example — read it before starting
  validate()                  catches empty text, missing title, duplicate ids
  main()                      wiring and the summary

Run it as soon as you start. The CSV reader alone will work, and you will see
exactly what shape you are aiming for.
"""
import csv
import json
import re
from pathlib import Path
from pypdf import PdfReader
from headings import split_sections_by_font, split_sections

RAW = Path("data/raw")
OUT = Path("data/records.jsonl")

# The target shape. Every record from every format must have exactly these keys.
# Decide this ONCE, here, and the rest of the course depends on it holding.
FIELDS = ["doc_id", "source_file", "source_type", "title", "text", "updated"]


def record(doc_id, source_file, source_type, title, text, updated=""):
    """Build one record. Using this everywhere is what guarantees uniformity."""
    return {
        "doc_id": str(doc_id).strip(),
        "source_file": str(source_file),
        "source_type": source_type,
        "title": " ".join(str(title).split()),
        "text": " ".join(str(text).split()),   # collapse all whitespace runs
        "updated": str(updated).strip(),
    }


# --------------------------------------------------------------- GIVEN
def read_faq_csv(path):
    """One record per FAQ row. Question and answer are joined into the text,
    because at retrieval time you want both — a question alone answers nothing."""
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # A question with no answer is not retrievable content, so its text
            # is empty rather than the question echoed back. validate() then
            # rejects it loudly instead of it embedding as a useless vector.
            answer = row["answer"].strip()
            text = f"{row['question']} {answer}" if answer else ""
            out.append(record(
                doc_id=f"faq-{row['faq_id']}",
                source_file=path.name,
                source_type="faq",
                title=row["question"],
                text=text,
                updated=row["updated"],
            ))
    return out


# --------------------------------------------------------------- YOURS
def read_announcements_json(path):
    """One record per announcement.

    Open the file and look at it first. The structure is nested: the list you
    want is under one top-level key, and each item keeps its body text two
    levels down rather than at the top.

        json.load(open(path, encoding="utf-8"))   gives you a dict
        data["some_key"]                          gives you the list
        item["a"]["b"]                            reaches a nested value

    doc_id      use the announcement's own id, prefixed "ann-"
    source_type "announcement"
    title       the announcement title
    text        title and body together, same reasoning as the FAQ reader
    updated     the posted date, which lives in the metadata, not the content
    """
    out = []
    data = json.load(open(path, encoding="utf-8"))

    for item in data.get("announcements", []):
        item_id = item.get("id") or item.get("announcement_id") or item.get("announcementId")
        title = item.get("title") or item.get("headline") or ""

        body = item.get("body") or item.get("content") or item.get("details") or ""
        if isinstance(body, dict):
            for key in ("text", "body", "content", "description", "message", "summary"):
                if key in body:
                    body = body[key]
                    break
        if isinstance(body, list):
            body = " ".join(str(part) for part in body)
        body = str(body).strip()

        updated = ""
        for container in (item.get("metadata"), item.get("meta"), item.get("info"), item.get("details")):
            if isinstance(container, dict):
                for key in ("posted", "updated", "date", "published", "timestamp"):
                    if key in container:
                        updated = str(container[key]).strip()
                        break
                if updated:
                    break

        text = f"{title} {body}" if body else title
        out.append(record(
            doc_id=f"ann-{item_id}",
            source_file=path.name,
            source_type="announcement",
            title=title,
            text=text,
            updated=updated,
        ))
    return out
    
def read_handbook_pdf(path):
    

    FURNITURE = ["NORTHSIDE YOUTH FC", "Revision 4", "Uncontrolled when printed", "Page "]

    text = "\n".join(p.extract_text() for p in PdfReader(path).pages)

    out = []
    current = None                     # the section being built, or None

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if any(f in line for f in FURNITURE):
            continue

        m = re.match(r"^(\d+)\.\s+(.+)$", line)
        if m:
            if current:
                out.append(record(
                    doc_id=f"handbook-s{current['num']}",
                    source_file=path.name,
                    source_type="handbook",
                    title=current["title"],
                    text=" ".join(current["body"]),
                ))
            current = {"num": m.group(1), "title": m.group(2), "body": []}
        elif current:
            current["body"].append(line)

    if current:
        out.append(record(
            doc_id=f"handbook-s{current['num']}",
            source_file=path.name,
            source_type="handbook",
            title=current["title"],
            text=" ".join(current["body"]),
        ))

    return out
def read_real_handbook(path, club):
    """Real handbooks from other clubs. Font evidence first, text heuristics
    as the fallback. Kept separate from read_handbook_pdf on purpose —
    Northside stays untouched as the regression fixture."""
    secs = split_sections_by_font(path)
    used = "font"
    if not secs:
        text = "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
        secs = split_sections(text, threshold=5)
        used = "text-heuristic"

    out = []
    for i, (title, body) in enumerate(secs, 1):
        if not body.strip():
            continue
        out.append(record(
            doc_id=f"{club}-s{i}",
            source_file=path.name,
            source_type="handbook",
            title=title,
            text=body,
        ))
    print(f"  {path.name:<20} {used:<16} {len(out):>3} records")
    return out

FEE_ROW = re.compile(
    r"(U\d+\s*[–-]\s*U\d+)\s+£([\d.]+)\s+£([\d.]+)\s*x\s*(\d+)\s+(Yes|No|Training top only)"
)

def split_fee_table(records):
    """A table is not prose. Each row becomes its own self-contained record,
    so a retriever can return one age band without dragging its neighbours."""
    out = []
    for r in records:
        rows = FEE_ROW.findall(r["text"])
        if not rows:
            out.append(r)
            continue

        # the parent section keeps its prose, minus the flattened table
        prose = FEE_ROW.sub(" ", r["text"]).replace(
            "Age group Season fee Instalment Kit included", " ")
        out.append(record(r["doc_id"], r["source_file"], r["source_type"],
                          r["title"], prose, r["updated"]))

        for band, fee, inst, n, kit in rows:
            band = " ".join(band.split())
            out.append(record(
                doc_id=f"{r['doc_id']}-{band.lower().replace(' ', '').replace('–', '-')}",
                source_file=r["source_file"],
                source_type=r["source_type"],
                title=f"{band} season fee",
                text=(f"{band}: season fee £{fee}, or {n} instalments of £{inst}. "
                      f"Kit included: {kit}."),
                updated=r["updated"],
            ))
    return out


# --------------------------------------------------------------- GIVEN
def validate(records):
    """Split records into good and bad. Loud failure beats silent corruption:
    a record with empty text will embed into meaningless vector space and
    quietly pollute every retrieval you run for the rest of the course."""
    good, bad, seen = [], [], set()
    for r in records:
        problems = []
        if set(r.keys()) != set(FIELDS):
            problems.append(f"wrong keys: {sorted(set(r.keys()) ^ set(FIELDS))}")
        if not r.get("text", "").strip():
            problems.append("empty text")
        if not r.get("title", "").strip():
            problems.append("empty title")
        if r.get("doc_id") in seen:
            problems.append("duplicate doc_id")
        # Text that only repeats the title carries no information a retriever
        # could use. Catches an announcement or section with an empty body.
        if r.get("text", "").strip() and r.get("text", "").strip() == r.get("title", "").strip():
            problems.append("text adds nothing beyond the title")
        seen.add(r.get("doc_id"))
        (bad if problems else good).append((r, problems) if problems else r)
    return good, bad


def main():
    readers = [
        ("faq_export.csv", read_faq_csv),
        ("announcements.json", read_announcements_json),
        ("handbook_2026.pdf", read_handbook_pdf),
    ]
    real_dir = RAW / "real"
    if real_dir.exists():
        print("\nreal handbooks:")
        real = []
        for pdf in sorted(real_dir.glob("*.pdf")):
            try:
                real.extend(read_real_handbook(pdf, pdf.stem))
            except Exception as e:
                print(f"  {pdf.name:<20} FAILED  {type(e).__name__}: {e}")
        good_real, bad_real = validate(real)
        print(f"\n{len(good_real)} valid, {len(bad_real)} rejected")
        for r, problems in bad_real:
            print(f"  REJECTED {r.get('doc_id','?'):<20} {'; '.join(problems)}")
        with open("data/records-real.jsonl", "w", encoding="utf-8") as f:
            for r in good_real:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    all_records = []
    for filename, fn in readers:
        path = RAW / filename
        if not path.exists():
            print(f"  ! missing {path}")
            continue
        got = fn(path)
        print(f"  {filename:<24} {len(got):>3} records")
        all_records.extend(got)
        all_records = split_fee_table(all_records)
    good, bad = validate(all_records)

    print(f"\n{len(good)} valid, {len(bad)} rejected")
    for r, problems in bad:
        print(f"  REJECTED {r.get('doc_id','?'):<20} {'; '.join(problems)}")

    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in good:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nwrote {OUT}  ({len(good)} records)")

    if good:
        by_type = {}
        for r in good:
            by_type[r["source_type"]] = by_type.get(r["source_type"], 0) + 1
        print("by source_type:", dict(sorted(by_type.items())))
        print("\nfirst record:")
        print(json.dumps(good[0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
