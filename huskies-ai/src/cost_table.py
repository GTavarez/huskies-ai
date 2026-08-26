"""Week 1, Weekend block — join metadata to the corpus and price it by source.

    python src/cost_table.py                 # uses the default illustrative rate
    python src/cost_table.py --rate 3.00     # your provider's $ per 1M input tokens

Run tokenizers_compare.py first — this reads out/token_counts.csv.

This is the table that makes Week 5's "why not paste the whole corpus" argument
concrete instead of theoretical, using your own numbers.
"""
import argparse
from pathlib import Path

import pandas as pd

COUNTS = Path("out/token_counts.csv")
META = Path("data/metadata.csv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rate", type=float, default=3.00,
                    help="USD per 1M input tokens. Default is illustrative — use your own.")
    args = ap.parse_args()

    if not COUNTS.exists():
        raise SystemExit(f"{COUNTS} not found. Run: python src/tokenizers_compare.py")

    counts = pd.read_csv(COUNTS)
    meta = pd.read_csv(META)
    df = counts.merge(meta, on="doc_id", how="left", validate="one_to_one")

    missing = df["source_type"].isna().sum()
    if missing:
        print(f"! {missing} documents have no metadata row. Fix data/metadata.csv "
              f"before you trust anything below.\n")

    # Prefer real subword tokens; fall back to a word-count estimate if tiktoken
    # could not run, and say so rather than quietly mixing units.
    if "subword" in df.columns:
        df["tokens"] = df["subword"]
        basis = "subword tokens (tiktoken)"
    else:
        df["tokens"] = (df["word"] * 1.33).round().astype(int)
        basis = "ESTIMATED from word count x 1.33 — rerun with tiktoken for real figures"

    df["cost_per_full_context_call"] = df["tokens"] / 1_000_000 * args.rate

    by_source = (df.groupby("source_type")
                   .agg(docs=("doc_id", "count"),
                        tokens=("tokens", "sum"),
                        mean_tokens=("tokens", "mean"))
                   .sort_values("tokens", ascending=False))
    by_source["share"] = (by_source["tokens"] / by_source["tokens"].sum() * 100).round(1)
    by_source["mean_tokens"] = by_source["mean_tokens"].round(0).astype(int)

    total = int(df["tokens"].sum())
    print(f"basis: {basis}")
    print(f"rate:  ${args.rate:.2f} per 1M input tokens (illustrative unless you passed --rate)\n")
    print("Per source type, most expensive first")
    print(by_source.to_string())

    print(f"\nWhole corpus: {total:,} tokens")
    print(f"  Cost of stuffing all of it into ONE question:  ${total/1_000_000*args.rate:.4f}")
    four_chunks = 4 * 300
    print(f"  Cost of retrieving 4 chunks (~{four_chunks} tokens):        "
          f"${four_chunks/1_000_000*args.rate:.4f}")
    print(f"  Ratio: {total/four_chunks:.0f}x more context per question without retrieval")
    print("\nThis corpus is small, so the absolute numbers look harmless. Multiply by")
    print("a thousand questions a day, then by a real corpus, and it stops looking harmless.")

    out = Path("out/cost_by_source.csv")
    by_source.to_csv(out)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
