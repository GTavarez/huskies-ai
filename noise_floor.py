"""Week 1, step 10 — measure how much your setup varies when nothing changes.

    python noise_floor.py            # 5 runs
    python noise_floor.py --runs 10

Runs one identical, seeded, temperature-0 request several times and reports how
much the answers differ from each other.

Why this matters: in Week 6 you will claim your system improved over the Week 5
baseline. That claim is only meaningful if the improvement is bigger than the
variation you get from changing nothing at all. This measures that floor.
"""
import argparse
import difflib
import json
import statistics
from pathlib import Path

from config import CONFIG, client, stamp

PROMPT = "In two sentences, explain what a youth sports club registration form is for."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5)
    args = ap.parse_args()

    cli = client()
    print(f"model: {CONFIG['model']}  via  {CONFIG['base_url']}")
    print(f"temperature 0, seed {CONFIG['seed']}, {args.runs} identical requests\n")

    texts = []
    for i in range(args.runs):
        resp = cli.chat.completions.create(
            model=CONFIG["model"],
            messages=[{"role": "user", "content": PROMPT}],
            temperature=0.0,
            seed=CONFIG["seed"],
            max_tokens=CONFIG["max_tokens"],
        )
        texts.append(resp.choices[0].message.content.strip())
        print(f"  run {i + 1}/{args.runs} done")

    unique = len(set(texts))
    sims = [difflib.SequenceMatcher(None, texts[i], texts[j]).ratio()
            for i in range(len(texts)) for j in range(i + 1, len(texts))]
    lo, mean = (min(sims), statistics.mean(sims)) if sims else (1.0, 1.0)

    print(f"\nunique answers      {unique} of {args.runs}")
    print(f"similarity, lowest  {lo:.3f}")
    print(f"similarity, mean    {mean:.3f}")

    print()
    if unique == 1:
        print("Deterministic. Every run gave identical text.")
        print("A small score difference in Week 6 is likely to be a real difference.")
    elif mean >= 0.90:
        print("Near-deterministic. Wording drifts slightly, meaning is stable.")
        print("Treat Week 6 improvements under about 2 points as inside the noise.")
    else:
        print("Noisy. Identical inputs give substantially different wording.")
        print("Two consequences for the rest of the course:")
        print("  1. Run every measurement 3 times and report the mean, not one run.")
        print("  2. An improvement smaller than your run-to-run spread is not an improvement.")

    print("\nRecord the mean similarity in your tracker. Week 6 needs it.")

    out = Path("out/noise_floor.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({
        "config": stamp(), "runs": args.runs, "prompt": PROMPT,
        "unique_answers": unique, "similarity_min": lo, "similarity_mean": mean,
        "texts": texts,
    }, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
