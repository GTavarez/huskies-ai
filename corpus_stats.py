"""Week 3 — the numbers behind the corpus freeze.

    python corpus_stats.py

Prints a markdown table you paste into docs/corpus-manifest.md, plus the two
arithmetic results that decide how Week 5 gets built.

WHY THIS IS A SCRIPT AND NOT A TYPED TABLE
  You will run it again. Once when you swap Northside for a real club's
  documents, once more when the corpus grows, and again every time someone asks
  what this thing actually costs to run. A number you typed by hand is a number
  nobody trusts six weeks later.

WHAT IT DOES NOT DO
  It does not fill in the column that matters. "Can I verify the answers in this
  document?" is a judgment, it belongs to you, and it is the only reason the
  manifest exists — so the script leaves that column blank on purpose and never
  overwrites docs/corpus-manifest.md.
"""
import json
from collections import defaultdict
from pathlib import Path

RECORDS = Path("data/records.jsonl")
RAW = Path("data/raw")

# Your Week 1 measurement. Used only if tiktoken is unavailable, and labelled
# as an estimate when it is, because an estimate you mistake for a measurement
# is worse than no number.
TOKENS_PER_WORD = 1.17


def counter():
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return (lambda s: len(enc.encode(s))), "tiktoken cl100k_base", True
    except Exception:
        return (lambda s: round(len(s.split()) * TOKENS_PER_WORD)), \
               f"word count x {TOKENS_PER_WORD} (estimate)", False


def pages(name):
    """Page count for PDFs, blank for anything else."""
    p = RAW / name
    if p.suffix.lower() != ".pdf" or not p.exists():
        return ""
    try:
        from pypdf import PdfReader
        return str(len(PdfReader(p).pages))
    except Exception:
        return "?"


def main():
    if not RECORDS.exists():
        raise SystemExit(f"{RECORDS} not found — run ingest.py first.")

    rows = [json.loads(line) for line in open(RECORDS, encoding="utf-8")]
    tok, how, exact = counter()

    per = defaultdict(lambda: {"records": 0, "tokens": 0, "types": set()})
    for r in rows:
        e = per[r["source_file"]]
        e["records"] += 1
        e["tokens"] += tok(r["text"])
        e["types"].add(r["source_type"])

    total_tokens = sum(e["tokens"] for e in per.values())
    longest = max(rows, key=lambda r: tok(r["text"]))

    print(f"token count: {how}\n")
    print("| source file | type | pages | records | tokens | verifiable? | owner |")
    print("|---|---|---|---|---|---|---|")
    for name in sorted(per):
        e = per[name]
        size = RAW / name
        print(f"| `{name}` | {', '.join(sorted(e['types']))} | {pages(name)} "
              f"| {e['records']} | {e['tokens']} |  |  |")
    print(f"| **total** |  |  | **{len(rows)}** | **{total_tokens}** |  |  |")

    print(f"\nlongest record: {longest['doc_id']} ({tok(longest['text'])} tokens)")
    print(f"mean record:    {round(total_tokens / len(rows))} tokens")

    # The arithmetic that settles the "why not just paste everything" argument.
    print(f"\n--- what this costs per question ---")
    print(f"whole corpus in every prompt : {total_tokens:,} tokens")
    print(f"retrieving 4 records         : {round(total_tokens / len(rows) * 4):,} tokens")
    ratio = total_tokens / (total_tokens / len(rows) * 4)
    print(f"ratio                        : {ratio:.1f}x")

    if ratio < 5:
        print("\nThat ratio is small because this corpus is small. Twenty-one short")
        print("records fit in one prompt and retrieval saves you very little.")
        print("Re-run this on the real corpus. A 40-page handbook is roughly 26,000")
        print("tokens and the same comparison stops being a rounding error.")

    if not exact:
        print("\nNOTE: tiktoken was unavailable, so every token figure above is an")
        print("estimate from your Week 1 ratio. Write it in the manifest as an")
        print("estimate, or install tiktoken and re-run before you freeze.")

    print("\nPaste the table into docs/corpus-manifest.md and fill the last two")
    print("columns by hand. 'Verifiable?' is the whole point: if you cannot check")
    print("an answer yourself, that document cannot appear in an eval set, so it")
    print("cannot support any claim you make in Week 6.")


if __name__ == "__main__":
    main()
