"""Week 3, Weekday B — three task shapes, measured.

    python pipelines_bench.py
    python pipelines_bench.py --rate 0.15        # $ per 1M input tokens, to price it
    python pipelines_bench.py --model qwen2.5:1.5b

THE POINT
  Week 3 Weekday A asked which model. This asks a different question: does the
  SHAPE of the task change what it costs you? Three shapes, same model, same
  machine:

    sentiment      12 short inputs, one-word outputs      many calls, tiny each
    summarize      4 long inputs, medium outputs          few calls, heavy each
    extract        6 medium inputs, structured JSON out   format compliance

  They are not three different difficulties. They are three different cost
  profiles, and the one that looks cheapest per call is not always the one that
  is cheapest per useful answer.

WHAT IS MEASURED
  median s       the number a user feels
  p95 s          the number that generates complaints
  in / out       prompt and completion tokens, summed over the run
  tok/s          completion tokens per second
  failures       calls that errored, or JSON that would not parse

ABOUT MEMORY, WHICH IS THE INTERESTING PART
  This script reports the peak memory of THIS PYTHON PROCESS, and for the Ollama
  path that number will be almost nothing — a few tens of MB. That is not a bug
  and it is the lesson: the model is not in your process. It is resident in the
  Ollama server, and your script is a thin client sending HTTP.

  So "how much memory does this need?" has no answer until you say whose memory.
  For the real figure, in another terminal while this runs:

      ollama ps

  That column is what decides whether this fits on a club's laptop or needs a
  machine you pay for monthly — which is a pricing question long before it is an
  engineering one.

  A speech-to-text pipeline belongs in this comparison and is left out on
  purpose: every option needs either a multi-gigabyte local install or a hosted
  API, and neither is worth doing before the corpus is real. Note it as a gap in
  the week note rather than pretending you measured it.

OUTPUT
  out/pipelines_bench.csv
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from config import CONFIG, client, stamp

RECORDS = Path("data/records.jsonl")
OUT = Path("out")

# Parent messages a club actually receives. Short, varied in tone, and a couple
# that are deliberately ambiguous — a classifier that is confident on all twelve
# is not reading them.
MESSAGES = [
    "Thanks so much for sorting the kit out, he was thrilled.",
    "Third week running the session has been moved with no notice.",
    "Can you confirm whether Saturday is at the usual pitch?",
    "Brilliant coaching this season, real difference in her confidence.",
    "I've paid twice now and nobody has come back to me about the refund.",
    "Is there parking at the away ground on Sunday?",
    "She came home upset again after training. We need to talk.",
    "All good here, just checking the deadline hasn't passed.",
    "Fantastic day, the whole squad looked like they were enjoying it.",
    "Nobody answers the phone and the website hasn't been updated since May.",
    "Quick one — does he need shin pads for the indoor session too?",
    "Happy to help on match days if you still need volunteers.",
]


def peak_rss_mb():
    """Peak resident memory of this process, in MB. Windows and POSIX.

    Reported for honesty, not because it is the number you want — see the note
    at the top of this file about whose memory it actually is."""
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class COUNTERS(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD),
                            ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t),
                            ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t),
                            ("PeakPagefileUsage", ctypes.c_size_t)]

            c = COUNTERS()
            c.cb = ctypes.sizeof(c)
            ctypes.windll.psapi.GetProcessMemoryInfo(
                ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(c), c.cb)
            return round(c.PeakWorkingSetSize / 1e6, 1)
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux reports kilobytes, macOS reports bytes.
        return round((peak / 1e3 if sys.platform != "darwin" else peak / 1e6), 1)
    except Exception:
        return None


def load_records():
    if not RECORDS.exists():
        raise SystemExit(f"{RECORDS} not found — run ingest.py first.")
    return [json.loads(line) for line in open(RECORDS, encoding="utf-8")]


def call(cli, model, system, user, max_tokens):
    """One call, timed. Returns (seconds, text, prompt_tokens, completion_tokens)."""
    t0 = time.perf_counter()
    try:
        r = cli.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=CONFIG["temperature"],
            seed=CONFIG["seed"],
            max_tokens=max_tokens,
        )
        text = (r.choices[0].message.content or "").strip()
        u = getattr(r, "usage", None)
        pin = getattr(u, "prompt_tokens", 0) or 0
        pout = getattr(u, "completion_tokens", 0) or 0
    except Exception as e:
        return time.perf_counter() - t0, f"[{type(e).__name__}: {e}]", 0, 0
    return time.perf_counter() - t0, text, pin, pout


# ------------------------------------------------------------------ the three
def task_sentiment(cli, model):
    system = ("Classify the sentiment of a message from a parent to a youth sports club. "
              "Reply with exactly one word: positive, neutral, or negative. Nothing else.")
    allowed = {"positive", "neutral", "negative"}
    rows = []
    for m in MESSAGES:
        s, text, pin, pout = call(cli, model, system, m, max_tokens=5)
        ok = text.strip().strip(".").lower() in allowed
        rows.append((s, pin, pout, ok))
    return rows


def task_summarize(cli, model, records):
    system = ("Summarise this club document in one sentence a parent could act on. "
              "Use only what the document says.")
    picks = [r for r in records if r["source_type"] == "handbook"][:4]
    rows = []
    for r in picks:
        s, text, pin, pout = call(cli, model, system, r["text"], max_tokens=80)
        ok = bool(text) and not text.startswith("[")
        rows.append((s, pin, pout, ok))
    return rows


def task_extract(cli, model, records):
    system = ('Return JSON only, no prose, with exactly these keys: '
              '{"topic": string, "action_required": true or false, "deadline": string or null}. '
              'Use only what the document says. If there is no deadline, use null.')
    picks = ([r for r in records if r["source_type"] == "announcement"] +
             [r for r in records if r["source_type"] == "faq"])[:6]
    rows = []
    for r in picks:
        s, text, pin, pout = call(cli, model, system, r["text"], max_tokens=120)
        ok = False
        try:
            body = text
            if "```" in body:                      # models love fencing JSON
                body = body.split("```")[1]
                body = body[4:] if body.lower().startswith("json") else body
            parsed = json.loads(body.strip())
            ok = set(parsed) == {"topic", "action_required", "deadline"}
        except Exception:
            ok = False
        rows.append((s, pin, pout, ok))
    return rows


def summarise(name, rows, rate):
    lat = [r[0] for r in rows]
    lat_sorted = sorted(lat)
    p95 = lat_sorted[min(len(lat_sorted) - 1, int(round(0.95 * (len(lat_sorted) - 1))))]
    tin = sum(r[1] for r in rows)
    tout = sum(r[2] for r in rows)
    fails = sum(0 if r[3] else 1 for r in rows)
    total_s = sum(lat)
    return {
        "task": name,
        "calls": len(rows),
        "median_s": round(statistics.median(lat), 2),
        "p95_s": round(p95, 2),
        "tokens_in": tin,
        "tokens_out": tout,
        "tok_s": round(tout / total_s, 1) if total_s else 0,
        "failures": fails,
        "per_1k_usd": round(tin / 1e6 * rate * (1000 / max(len(rows), 1)), 4) if rate else "",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=CONFIG["model"])
    ap.add_argument("--rate", type=float, default=0.0,
                    help="$ per 1M input tokens, to price 1,000 items of each shape")
    args = ap.parse_args()

    records = load_records()
    cli = client()
    print(f"model: {args.model}   corpus: {len(records)} records\n")

    # Warm-up, so the first task does not absorb the model load.
    call(cli, args.model, "Reply with OK.", "hi", 3)

    results = []
    for name, fn in [("sentiment", lambda: task_sentiment(cli, args.model)),
                     ("summarize", lambda: task_summarize(cli, args.model, records)),
                     ("extract",   lambda: task_extract(cli, args.model, records))]:
        print(f"{name} ...", end="", flush=True)
        rows = fn()
        r = summarise(name, rows, args.rate)
        results.append(r)
        print(f"  {r['calls']} calls   median {r['median_s']}s   p95 {r['p95_s']}s   "
              f"{r['tokens_in']} in / {r['tokens_out']} out   {r['failures']} failed")

    cols = ["task", "calls", "median_s", "p95_s", "tokens_in", "tokens_out", "tok_s", "failures"]
    if args.rate:
        cols.append("per_1k_usd")
    w = {c: max(len(c), *(len(str(r[c])) for r in results)) for c in cols}
    print("\n" + "  ".join(c.ljust(w[c]) for c in cols))
    print("  ".join("-" * w[c] for c in cols))
    for r in results:
        print("  ".join(str(r[c]).ljust(w[c]) for c in cols))

    mem = peak_rss_mb()
    print(f"\npeak memory of THIS process: {mem} MB"
          if mem is not None else "\npeak memory: unavailable on this platform")
    print("Run `ollama ps` in another terminal to see where the model actually lives.")

    OUT.mkdir(exist_ok=True)
    with open(OUT / "pipelines_bench.csv", "w", encoding="utf-8", newline="") as f:
        f.write(",".join(cols) + ",peak_rss_mb,model\n")
        for r in results:
            f.write(",".join(str(r[c]) for c in cols) + f",{mem},{args.model}\n")
    with open(OUT / "pipelines_bench.json", "w", encoding="utf-8") as f:
        json.dump({"config": stamp(), "model": args.model,
                   "peak_rss_mb": mem, "results": results}, f, indent=2)

    print(f"\nwrote {OUT/'pipelines_bench.csv'} and {OUT/'pipelines_bench.json'}\n")
    print("Two things to read off this before you write the week note:")
    print("  1. Compare median and p95 within each task. A p95 far above the")
    print("     median means some inputs are much more expensive than the average,")
    print("     and averages will mislead you about what users experience.")
    print("  2. Look at the failures column for 'extract'. Structured output is")
    print("     where small models break first, and it is the shape Week 7 depends")
    print("     on — an agent cannot ask you what the reply meant.")


if __name__ == "__main__":
    main()
