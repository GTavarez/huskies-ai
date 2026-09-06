"""Week 3, Weekday A — score candidate models on evidence you produced yourself.

    ollama pull gemma3:1b          # or whatever you want to consider
    python bench_models.py                       # everything the server offers
    python bench_models.py --models llama3.2:latest,qwen2.5:0.5b,gemma3:1b

THE POINT, AND IT IS NOT THE SCRIPT
  A model comparison built from published benchmark scores tells you how these
  models rank on somebody else's task. Yours is: answer questions about a youth
  football club from a handful of retrieved documents, on a laptop, and refuse
  when the documents do not cover the question.

  Nothing on a leaderboard measures that. So this measures it.

WHAT IS SCORED
  grounded    6 questions whose answers ARE in data/records.jsonl. The matching
              record is pasted in; a model is correct if the required fact
              appears in its answer. Substring matching, deliberately generous —
              you are testing whether the fact survived, not prose style.

  refusal     3 questions the documents do NOT answer. Correct means refusing.
              Anything else is a fabrication, and a fabrication costs more than
              a missed answer: a blank looks like a bug and gets fixed, a
              confident wrong answer looks like an answer and ships.

              Question 9 is the hard one. It asks the U19 fee, and it hands the
              model the fee table — which stops at U16-U18. The document is
              relevant and does not contain the answer. That is the failure mode
              that will actually bite you in Week 6, and a model that scores 6/6
              on grounded and misses this one is not the safer choice.

  latency     median wall-clock seconds per call, and tokens per second, over
              all 9 calls after a warm-up. Not a lab benchmark. It is the number
              that decides whether a parent waits or leaves.

  size        on-disk size, pulled from Ollama's own API when it is there.

WHAT THIS DOES NOT MEASURE
  License terms, context window, and whether the weights will still be
  downloadable in a year. Those go in your matrix by hand — they matter and no
  script can measure them.

OUTPUT
  out/model_bench.csv   one row per model
  out/model_bench.md    the scorecard, plus every answer that was marked wrong
"""
import argparse
import json
import re
import statistics
import time
import urllib.request
from pathlib import Path

from config import CONFIG, client

RECORDS = Path("data/records.jsonl")
OUT = Path("out")

REFUSAL = "That is not covered in the club documents."

SYSTEM = (
    "You are the assistant for a youth sports club. Answer using ONLY the "
    "club documents provided below. Do not add general knowledge about how "
    "clubs usually work. If the documents do not contain the answer, reply "
    "with exactly this sentence and nothing after it: " + REFUSAL
)

# (question, [doc_ids], required fact or None)
# empty list -> nothing is retrieved, the model must refuse
# fact None  -> the model must refuse even though documents ARE supplied
#
# Each case supplies a SHORT LIST, not one perfect document. Real retrieval
# returns the top k, most of which are near misses — a model that only behaves
# when handed exactly one correct paragraph will not survive Week 5.
CASES = [
    ("How many sessions may a new player attend before registering?",
     ["faq-F001", "faq-F002"], "two"),
    ("What is the season fee for a U11 player?",
     ["handbook-s2-u10-u12", "handbook-s2-u13-u15", "handbook-s2"], "150"),
    ("After lightning is seen, how long before play may resume?",
     ["handbook-s6"], "30"),
    ("Up to what point in the season is a subscription refundable?",
     ["faq-F004", "faq-F003"], "fourth week"),
    ("Who must accompany an under-13 player to an away fixture?",
     ["handbook-s5"], "parent"),
    ("How quickly must an injury be recorded in the log?",
     ["handbook-s7", "ann-A-2026-017"], "24 hours"),

    ("What time is training tomorrow?", [], None),
    ("Who is the club's current top scorer?", [], None),
    # The trap: every neighbouring band is supplied, and none of them is U19.
    ("What is the season fee for a U19 player?",
     ["handbook-s2-u16-u18", "handbook-s2-u13-u15", "handbook-s2"], None),
]


def load_records():
    if not RECORDS.exists():
        raise SystemExit(f"{RECORDS} not found — run ingest.py first.")
    return {r["doc_id"]: r for r in
            (json.loads(line) for line in open(RECORDS, encoding="utf-8"))}


def ollama_sizes(base_url):
    """Ollama exposes disk size at /api/tags. Best effort — a hosted provider
    will not have it, and the scorecard just leaves the column blank."""
    try:
        root = base_url.rstrip("/")
        if root.endswith("/v1"):
            root = root[:-3]
        with urllib.request.urlopen(root.rstrip("/") + "/api/tags", timeout=5) as r:
            data = json.load(r)
        return {m["name"]: round(m.get("size", 0) / 1e9, 2) for m in data.get("models", [])}
    except Exception:
        return {}


def build_prompt(question, recs):
    context = ("\n\n".join(f"[{r['doc_id']}] {r['title']}\n{r['text']}" for r in recs)
               if recs else "[no documents matched this question]")
    return f"CLUB DOCUMENTS:\n{context}\n\nQUESTION: {question}"


MONEY = re.compile(r"[£$€]\s?\d")

REFUSALS = (
    "not covered in the club documents",
    "do not contain", "not in the documents", "documents do not",
    "not provided in", "not specified", "not mentioned",
    "does not specify", "no information about",
)


def refused(answer):
    """Generous on punctuation and wording, strict on meaning. A model that says
    'the specific amount is not provided in the given information' is doing the
    right thing, and the first version of this function scored it as a failure.

    Widening a scorer is not free: every phrase added here is a phrase a wrong
    answer could contain by accident. Weigh that before adding more."""
    a = answer.lower()
    return any(p in a for p in REFUSALS)


def refused_cleanly(answer):
    """A refusal that still hands over a number is not a refusal. 'The fee is
    £195, though it is not specified for U19' would pass refused() and would
    still put a wrong figure in front of a parent."""
    return refused(answer) and not MONEY.search(answer)


def score_one(cli, model, recs):
    rows, lat = [], []

    # Warm-up. The first call to a cold model pays the load cost, and folding
    # that into the median would say more about your disk than the model.
    try:
        cli.chat.completions.create(
            model=model, messages=[{"role": "user", "content": "hi"}],
            max_tokens=1, temperature=0)
    except Exception as e:
        return None, [{"error": f"{type(e).__name__}: {e}"}]

    for question, doc_ids, fact in CASES:
        supplied = [recs[d] for d in doc_ids if d in recs]
        missing = [d for d in doc_ids if d not in recs]
        if missing:
            print(f"\n  ! case supplies unknown doc_id(s): {missing}", end="")
        t0 = time.perf_counter()
        try:
            r = cli.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": build_prompt(question, supplied)}],
                temperature=CONFIG["temperature"],
                seed=CONFIG["seed"],
                max_tokens=CONFIG["max_tokens"],
            )
            answer = (r.choices[0].message.content or "").strip()
            gen = getattr(getattr(r, "usage", None), "completion_tokens", 0) or 0
        except Exception as e:
            answer, gen = f"[{type(e).__name__}: {e}]", 0
        elapsed = time.perf_counter() - t0
        lat.append(elapsed)

        must_refuse = fact is None
        if must_refuse:
            ok = refused_cleanly(answer)
        else:
            ok = fact.lower() in answer.lower() and not refused(answer)

        rows.append({"question": question, "doc_id": ", ".join(doc_ids) or "-",
                     "expect": REFUSAL if must_refuse else fact,
                     "answer": answer, "ok": ok, "kind": "refusal" if must_refuse else "grounded",
                     "seconds": round(elapsed, 2),
                     "tok_s": round(gen / elapsed, 1) if elapsed else 0})

    grounded = [r for r in rows if r["kind"] == "grounded"]
    refusals = [r for r in rows if r["kind"] == "refusal"]
    summary = {
        "model": model,
        "grounded": f"{sum(r['ok'] for r in grounded)}/{len(grounded)}",
        "refusal": f"{sum(r['ok'] for r in refusals)}/{len(refusals)}",
        "median_s": round(statistics.median(lat), 2),
        "tok_s": round(statistics.median([r["tok_s"] for r in rows if r["tok_s"]] or [0]), 1),
    }
    return summary, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", help="comma-separated; default is everything the server offers")
    args = ap.parse_args()

    recs = load_records()
    cli = client()

    if args.models:
        models = [m.strip() for m in args.models.split(",") if m.strip()]
    else:
        models = sorted(m.id for m in cli.models.list().data)
    sizes = ollama_sizes(CONFIG["base_url"])

    print(f"corpus: {len(recs)} records   cases: {len(CASES)} "
          f"({sum(1 for c in CASES if c[2])} grounded, "
          f"{sum(1 for c in CASES if not c[2])} must-refuse)")
    print(f"models: {', '.join(models)}\n")

    summaries, details = [], {}
    for m in models:
        print(f"{m} ...", end="", flush=True)
        s, rows = score_one(cli, m, recs)
        if s is None:
            print(f"  SKIPPED — {rows[0]['error']}")
            continue
        details[m] = rows
        summaries.append({**s, "gb": sizes.get(m, "")})
        print(f"  grounded {s['grounded']}   refusal {s['refusal']}   "
              f"{s['median_s']}s   {s['tok_s']} tok/s")

    if not summaries:
        raise SystemExit("nothing ran.")

    cols = ["model", "gb", "grounded", "refusal", "median_s", "tok_s"]
    head = {"model": "model", "gb": "size GB", "grounded": "grounded",
            "refusal": "refusal", "median_s": "median s", "tok_s": "tok/s"}
    w = {c: max(len(head[c]), *(len(str(s[c])) for s in summaries)) for c in cols}

    print("\n" + "  ".join(head[c].ljust(w[c]) for c in cols))
    print("  ".join("-" * w[c] for c in cols))
    for s in summaries:
        print("  ".join(str(s[c]).ljust(w[c]) for c in cols))

    OUT.mkdir(exist_ok=True)
    with open(OUT / "model_bench.csv", "w", encoding="utf-8", newline="") as f:
        f.write(",".join(cols) + "\n")
        for s in summaries:
            f.write(",".join(str(s[c]) for c in cols) + "\n")

    with open(OUT / "model_bench.md", "w", encoding="utf-8") as f:
        f.write("# Candidate model scorecard\n\n")
        f.write(f"Corpus: {len(recs)} records. Temperature {CONFIG['temperature']}, "
                f"seed {CONFIG['seed']}. Measured on this machine, not quoted.\n\n")
        f.write("| " + " | ".join(head[c] for c in cols) + " |\n")
        f.write("|" + "|".join("---" for _ in cols) + "|\n")
        for s in summaries:
            f.write("| " + " | ".join(str(s[c]) for c in cols) + " |\n")
        f.write("\n## Every answer that was marked wrong\n\n")
        any_wrong = False
        for m, rows in details.items():
            wrong = [r for r in rows if not r["ok"]]
            if not wrong:
                continue
            any_wrong = True
            f.write(f"### {m}\n\n")
            for r in wrong:
                f.write(f"**{r['question']}**  \nretrieved `{r['doc_id']}`, "
                        f"expected `{r['expect']}`\n\n```\n{r['answer']}\n```\n\n")
        if not any_wrong:
            f.write("_None. Widen the case list — a test everything passes "
                    "measures nothing._\n\n")
        f.write("## Not measured here — fill in by hand\n\n"
                "| model | license | context window | still maintained? |\n"
                "|---|---|---|---|\n")
        for s in summaries:
            f.write(f"| {s['model']} |  |  |  |\n")
        f.write("\n## Recommendation\n\n"
                "_One page. Name the model you chose, the two or three numbers "
                "above that decided it, and — the part people skip — what you "
                "rejected and why. A recommendation with no rejected options is "
                "not a decision, it is a description._\n")

    print(f"\nwrote {OUT/'model_bench.csv'} and {OUT/'model_bench.md'}\n")
    print("Open model_bench.md and read the wrong answers before you look at the")
    print("table again. The table ranks the models; the wrong answers tell you")
    print("what kind of mistake each one makes, and that is what you are choosing.")


if __name__ == "__main__":
    main()
