"""Week 1, Weekend block — tokenize the corpus three ways and chart the difference.

    python src/tokenizers_compare.py

Produces out/token_distributions.png and out/token_counts.csv.

The point is not that one tokenizer wins. It is that "how long is this document"
has three different answers, and only one of them is the one you get billed for.
"""
import csv
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DOCS = Path("data/docs")
OUT = Path("out")
WORD_RE = re.compile(r"\w+|[^\w\s]")


def tok_word(text):
    """Split on words and punctuation. What a human means by 'how long is it'."""
    return WORD_RE.findall(text)


def tok_char(text):
    """Every character. The finest possible split, and the least useful."""
    return list(text)


def tok_subword(text):
    """What the model actually sees. Requires tiktoken and one download on first run."""
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    return enc.encode(text)


def load_subword():
    try:
        tok_subword("warm up the encoder")
        return tok_subword
    except Exception as e:
        print(f"! subword tokenizer unavailable ({type(e).__name__}).")
        print("  tiktoken downloads its vocabulary on first use and needs network access.")
        print("  Running with word and character tokenizers only.\n")
        return None


def main():
    files = sorted(DOCS.glob("*.txt"))
    if not files:
        sys.exit(f"No .txt files in {DOCS}. Put your corpus there first.")

    subword = load_subword()
    tokenizers = {"word": tok_word, "char": tok_char}
    if subword:
        tokenizers["subword"] = subword

    rows, series = [], {k: [] for k in tokenizers}
    for f in files:
        text = f.read_text()
        row = {"doc_id": f.stem, "bytes": len(text.encode())}
        for name, fn in tokenizers.items():
            n = len(fn(text))
            row[name] = n
            series[name].append(n)
        rows.append(row)

    OUT.mkdir(exist_ok=True)
    with open(OUT / "token_counts.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"{len(files)} documents\n")
    print(f"{'tokenizer':<10}{'total':>10}{'mean':>9}{'min':>7}{'max':>7}{'vs word':>10}")
    word_total = sum(series["word"])
    for name, vals in series.items():
        print(f"{name:<10}{sum(vals):>10,}{sum(vals)/len(vals):>9.0f}"
              f"{min(vals):>7}{max(vals):>7}{sum(vals)/word_total:>9.2f}x")

    fig, axes = plt.subplots(1, len(series), figsize=(4.2 * len(series), 3.6), sharey=False)
    if len(series) == 1:
        axes = [axes]
    for ax, (name, vals) in zip(axes, series.items()):
        ax.hist(vals, bins=8, color="#125C64", edgecolor="white")
        ax.set_title(f"{name}  ·  {sum(vals):,} total", fontsize=11)
        ax.set_xlabel("tokens per document", fontsize=9)
        ax.tick_params(labelsize=8)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_ylabel("documents", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "token_distributions.png", dpi=140)
    print(f"\nwrote {OUT/'token_counts.csv'} and {OUT/'token_distributions.png'}")

    if subword:
        ratio = sum(series["subword"]) / word_total
        print(f"\nYour corpus runs about {ratio:.2f} subword tokens per word.")
        print("Write that number down. Week 5 uses it to size retrieval against context stuffing.")


if __name__ == "__main__":
    main()
