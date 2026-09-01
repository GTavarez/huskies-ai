"""Week 2, weekend — what temperature actually does to your output.

    python temp_sweep.py

You have been running everything at temperature 0 because Week 1 was about
making results reproducible. Now find out what you gave up.

THE EXPERIMENT
  Two prompts, deliberately different in kind:

    OPEN    "write a short message to parents" — many good answers exist
    CLOSED  "reply with only the time"         — one good answer exists

  Each is asked RUNS times at each temperature. The seed changes on every run,
  so what you are measuring is the model's own willingness to vary, not the
  seed pinning it in place.

WHAT IS MEASURED
  unique      how many distinct answers came back out of RUNS
  similarity  mean pairwise similarity, 1.000 = every run identical
  length      mean characters, and how much that spread

WHAT TO EXPECT, AND WHY IT MATTERS
  At temperature 0 the model takes the highest-probability token every time,
  so both prompts should come back 1 unique / similarity 1.000 no matter what
  the seed is. That is the noise floor you measured in Week 1, confirmed again.

  As temperature rises, the two lines should separate. The open prompt has
  many plausible next tokens at every step, so it scatters early. The closed
  prompt has almost none, so it holds — until the temperature gets high enough
  to make a wrong token attractive, and then it breaks.

  That gap is the whole reason this matters for the retrieval system you are
  building. A question answered FROM a retrieved document is a closed prompt.
  Turning up temperature there does not make it more creative, it makes it
  more likely to contradict the document you just handed it.

OUTPUT
  out/temp_sweep.csv    one row per (prompt, temperature)
  out/temp_sweep.png    the chart
  out/temp_sweep.json   every raw answer, plus the config that produced them

Roughly 60 calls. On a local model expect a few minutes. Go make coffee.
"""
import itertools
import json
import statistics
from difflib import SequenceMatcher
from pathlib import Path

from config import CONFIG, client, stamp

OUT = Path("out")

TEMPERATURES = [0.0, 0.3, 0.6, 0.9, 1.2]
RUNS = 6

PROMPTS = {
    "open": (
        "Write one short text message telling parents that tomorrow's 6pm "
        "practice has moved to 7pm."
    ),
    "closed": (
        "Practice starts at 7pm. A parent asks what time practice starts. "
        "Reply with only the time and nothing else."
    ),
}


def ask(cli, prompt, temperature, seed):
    """One call. Everything except temperature and seed is held fixed —
    that is what makes this a sweep and not just a pile of outputs."""
    r = cli.chat.completions.create(
        model=CONFIG["model"],
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        seed=seed,
        max_tokens=60,
    )
    return (r.choices[0].message.content or "").strip()


def similarity(answers):
    """Mean similarity over every pair. 1.000 means every run came back the same.

    Pairs, not consecutive runs: two runs that differ from each other but both
    match a third would look stable if you only compared neighbours."""
    pairs = list(itertools.combinations(answers, 2))
    if not pairs:
        return 1.0
    return statistics.fmean(SequenceMatcher(None, a, b).ratio() for a, b in pairs)


def main():
    cli = client()
    total = len(PROMPTS) * len(TEMPERATURES) * RUNS
    print(f"model: {CONFIG['model']}   {total} calls "
          f"({len(PROMPTS)} prompts x {len(TEMPERATURES)} temperatures x {RUNS} runs)\n")

    rows, raw = [], []
    for name, prompt in PROMPTS.items():
        print(f"{name}:")
        for t in TEMPERATURES:
            answers = [ask(cli, prompt, t, seed=100 + i) for i in range(RUNS)]
            lengths = [len(a) for a in answers]
            row = {
                "prompt": name,
                "temperature": t,
                "unique": len(set(answers)),
                "runs": RUNS,
                "similarity": round(similarity(answers), 4),
                "mean_len": round(statistics.fmean(lengths), 1),
                "stdev_len": round(statistics.stdev(lengths) if len(lengths) > 1 else 0.0, 1),
            }
            rows.append(row)
            raw.append({**row, "answers": answers})
            print(f"  t={t:<4} {row['unique']} of {RUNS} unique   "
                  f"similarity {row['similarity']:.3f}   "
                  f"len {row['mean_len']:.0f} +/- {row['stdev_len']:.0f}")
        print()

    OUT.mkdir(exist_ok=True)

    with open(OUT / "temp_sweep.csv", "w", encoding="utf-8", newline="") as f:
        cols = ["prompt", "temperature", "unique", "runs", "similarity", "mean_len", "stdev_len"]
        f.write(",".join(cols) + "\n")
        for r in rows:
            f.write(",".join(str(r[c]) for c in cols) + "\n")

    with open(OUT / "temp_sweep.json", "w", encoding="utf-8") as f:
        json.dump({"config": stamp(), "runs_per_point": RUNS,
                   "prompts": PROMPTS, "results": raw}, f, indent=2, ensure_ascii=False)

    chart(rows)

    print(f"wrote {OUT/'temp_sweep.csv'}, {OUT/'temp_sweep.json'}, {OUT/'temp_sweep.png'}\n")
    print("Now open temp_sweep.json and READ the answers at t=1.2 for the closed")
    print("prompt. The number in the table tells you they differed. Only the text")
    print("tells you whether any of them are still correct — and that difference,")
    print("between a metric moving and an answer being wrong, is the thing to keep.")


def chart(rows):
    import matplotlib
    matplotlib.use("Agg")          # no display in a terminal; write straight to file
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    colors = {"open": "#125C64", "closed": "#B4553F"}

    for name in PROMPTS:
        pts = [r for r in rows if r["prompt"] == name]
        ax1.plot([p["temperature"] for p in pts], [p["similarity"] for p in pts],
                 marker="o", color=colors[name], label=name)

    ax1.set_xlabel("temperature")
    ax1.set_ylabel("mean pairwise similarity")
    ax1.set_title("How alike are repeated answers?")
    ax1.set_ylim(0, 1.05)
    ax1.axhline(1.0, color="#999", linewidth=0.8, linestyle=":")
    ax1.legend(frameon=False)
    ax1.grid(alpha=0.25)

    width = 0.10
    for i, name in enumerate(PROMPTS):
        pts = [r for r in rows if r["prompt"] == name]
        xs = [p["temperature"] + (i - 0.5) * width for p in pts]
        ax2.bar(xs, [p["unique"] for p in pts], width=width,
                color=colors[name], label=name)

    ax2.set_xlabel("temperature")
    ax2.set_ylabel(f"distinct answers out of {RUNS}")
    ax2.set_title("How many different answers came back?")
    ax2.set_yticks(range(0, RUNS + 1))
    ax2.legend(frameon=False)
    ax2.grid(alpha=0.25, axis="y")

    fig.suptitle(f"Temperature sweep — {CONFIG['model']}", y=1.02)
    fig.tight_layout()
    fig.savefig(OUT / "temp_sweep.png", dpi=150, bbox_inches="tight")


if __name__ == "__main__":
    main()
