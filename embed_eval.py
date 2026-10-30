"""Week 5, Weekday B — semantic retrieval, measured against the BM25 baseline.

    ollama pull nomic-embed-text          # once, ~274 MB
    python embed_eval.py                  # embeddings vs BM25, same questions
    python embed_eval.py --k 3
    python embed_eval.py --hybrid         # add the combined ranker

THE COMPARISON IS THE POINT
  BM25 matches WORDS. Ask "what do I do if my child gets a concussion" and it
  finds records containing 'concussion' and 'child'. Ask "who do I call when my
  kid gets hurt" and it finds nothing, because not one of those words appears in
  the answer.

  Embeddings match MEANING — or rather, they match position in a space built so
  that text used in similar ways lands nearby. That is not the same thing as
  meaning, and the difference shows up as confident nonsense: two passages about
  money rank close together whether or not either answers the question about
  money.

  So the interesting result is not "which is better". It is WHICH QUESTIONS EACH
  ONE WINS, because that tells you whether hybrid is worth building, and hybrid
  is what actually ships.

WHAT IS HELD FIXED
  Same records, same questions, same answer keys, same k, same scoring. The only
  thing that changes is how candidates are ranked. That is what makes this an
  experiment rather than two anecdotes — and it is why a question set with a few
  mislabelled refusals is still fine here: both rankers face the identical set,
  so the DIFFERENCE between them is clean even where the absolute number is not.

THE COST YOU SHOULD NOTICE
  BM25 needs no model, no download, no GPU, and indexes 142 records in
  milliseconds. Embeddings need a 274 MB model and one forward pass per record.
  If the scores come out close, BM25 is the better engineering answer for a club
  laptop, and 'we used embeddings' is not a reason to ship them.

OUTPUT
  out/embeddings-<model>.json    cached vectors, so reruns are instant
  docs/retrieval-compare.md
"""
import argparse
import json
import math
import time
from pathlib import Path

from retrieval_eval import BM25, contains_all

RECORDS = Path("data/records-real.jsonl")
QUESTIONS = Path("data/questions-real.jsonl")
OUT = Path("out")


def embed(texts, model, base=None):
    """Embed a list of strings through Ollama.

    Tries the OpenAI-compatible route first because that is what the rest of
    this repo speaks, and falls back to Ollama's native endpoint, which older
    builds serve instead."""
    import urllib.error
    import urllib.request

    base = (base or "http://localhost:11434").rstrip("/")
    vectors, batch = [], 32
    for i in range(0, len(texts), batch):
        chunk = texts[i:i + batch]
        body = json.dumps({"model": model, "input": chunk}).encode()
        for path, key in (("/v1/embeddings", "data"), ("/api/embed", "embeddings")):
            req = urllib.request.Request(
                base + path, data=body,
                headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    payload = json.load(r)
            except urllib.error.HTTPError as e:
                if e.code in (404, 405):
                    continue
                detail = e.read().decode(errors="replace")[:200]
                raise SystemExit(
                    f"\n{path} returned {e.code}: {detail}\n\n"
                    f"If it says the model is not found:  ollama pull {model}")
            except Exception as e:
                raise SystemExit(
                    f"\nCould not reach Ollama at {base} ({e}).\n"
                    "Is `ollama serve` running?")
            got = payload.get(key)
            if got is None:
                continue
            vectors += [d["embedding"] if isinstance(d, dict) else d for d in got]
            break
        else:
            raise SystemExit("Neither /v1/embeddings nor /api/embed answered "
                             "with vectors. Check your Ollama version.")
        print(f"    {min(i + batch, len(texts))}/{len(texts)}", end="\r", flush=True)
    print(" " * 30, end="\r")
    return vectors


def unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else v


def cosine(a, b):
    """Dot product of two already-normalised vectors."""
    return sum(x * y for x, y in zip(a, b))


class Embedded:
    def __init__(self, texts, model, cache):
        self.model = model
        vecs = None
        if cache.exists():
            blob = json.loads(cache.read_text(encoding="utf-8"))
            # The cache is keyed by how many records there were and by the text
            # itself. Reusing vectors after the corpus was rechunked would
            # silently compare a new corpus against an old index — the kind of
            # bug that does not crash and does not look wrong.
            if blob.get("model") == model and blob.get("texts") == texts:
                vecs = blob["vectors"]
                print(f"  reusing cached vectors ({len(vecs)})")
        if vecs is None:
            print(f"  embedding {len(texts)} records with {model} ...")
            t0 = time.perf_counter()
            vecs = embed(texts, model)
            print(f"  {time.perf_counter() - t0:.1f}s")
            cache.parent.mkdir(exist_ok=True)
            cache.write_text(json.dumps(
                {"model": model, "texts": texts, "vectors": vecs}), encoding="utf-8")
        self.vecs = [unit(v) for v in vecs]

    def search(self, query, k=5):
        q = unit(embed([query], self.model)[0])
        scored = sorted(((cosine(q, v), i) for i, v in enumerate(self.vecs)),
                        reverse=True)
        return [(i, s) for s, i in scored[:k]]


def rrf(*rankings, k=60):
    """Reciprocal rank fusion — the hybrid ranker, in four lines.

    Each list contributes 1/(k + rank) to every document it returns. No score
    normalisation, which matters because BM25 scores are unbounded and cosine
    scores live in [-1, 1]; averaging them directly would let BM25 shout down
    the embeddings on every query."""
    pool = {}
    for ranking in rankings:
        for rank, (i, _) in enumerate(ranking, 1):
            pool[i] = pool.get(i, 0) + 1 / (k + rank)
    return sorted(pool.items(), key=lambda p: -p[1])


def score_run(name, searcher, recs, texts, qs, k):
    """hit@k and the refusal leak, for one ranker."""
    rows = []
    for q in qs:
        try:
            hits = searcher(q["question"], k, q.get("document", ""))
        except TypeError:
            hits = searcher(q["question"], k)
        if q["expect"] == "refuse":
            rows.append({"qid": q["qid"], "expect": "refuse", "hit": 0,
                         "top": hits[0][1] if hits else 0.0})
            continue
        keys = q["keys"]
        good = {i for i, t in enumerate(texts) if contains_all(t, keys)}
        found = next((i for i, _ in hits if i in good), None)
        rows.append({"qid": q["qid"], "expect": "answerable",
                     "answerable": int(bool(good)),
                     "hit": int(found is not None),
                     "winner": recs[found]["doc_id"] if found is not None else "",
                     "top": hits[0][1] if hits else 0.0})
    return name, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="nomic-embed-text")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--hybrid", action="store_true")
    ap.add_argument("--by-club", action="store_true",
                    help="restrict each question's search to its own club")
    args = ap.parse_args()

    recs = [json.loads(l) for l in open(RECORDS, encoding="utf-8") if l.strip()]
    qs = [json.loads(l) for l in open(QUESTIONS, encoding="utf-8") if l.strip()]
    texts = [f"{r['title']} {r['text']}" for r in recs]
    ans = [q for q in qs if q["expect"] == "answerable"]

    print(f"{len(recs)} records · {len(qs)} questions · k={args.k} · "
          f"scope: {'per club' if args.by_club else 'whole corpus'}\n")
    bm = BM25(texts)
    em = Embedded(texts, args.model, OUT / f"embeddings-{args.model}.json")

    # A parent belongs to one club; the corpus holds four and they contradict
    # each other. Scoping the search is the product requirement and it is also
    # what stops "right answer, wrong handbook" from scoring as a miss.
    club_of = [r["doc_id"].rsplit("-", 1)[0] for r in recs]

    def scoped(fn):
        def search(query, k, club=""):
            if not (args.by_club and club):
                return fn(query, k)
            return [(i, sc) for i, sc in fn(query, len(texts))
                    if club_of[i] == club][:k]
        return search

    runs = [score_run("bm25", scoped(bm.search), recs, texts, qs, args.k),
            score_run("embed", scoped(em.search), recs, texts, qs, args.k)]
    if args.hybrid:
        def hybrid(query, k, club=""):
            wide = len(texts) if (args.by_club and club) else k * 2
            lex = scoped(bm.search)(query, wide, club)
            sem = scoped(em.search)(query, wide, club)
            return [(i, s) for i, s in rrf(lex[:k * 2], sem[:k * 2])[:k]]
        runs.append(score_run("hybrid", hybrid, recs, texts, qs, args.k))

    # A ranker's scores are only comparable to its OWN scores. BM25 is
    # unbounded, cosine lives in [-1, 1], and RRF sums 1/(60 + rank) so it
    # cannot exceed about 0.03 however good the match is. Printing one column of
    # "worst leak" across all three invites the conclusion that RRF at 0.03 is
    # six hundred times safer than BM25 at 18.02, which is not a fact about
    # retrieval — it is a fact about arithmetic. So print each ranker's leak
    # NEXT TO its own weakest genuine hit, and say whether the two separate.
    print(f"\n{'ranker':<9}{'hit@' + str(args.k):>9}   "
          f"{'worst leak':>11}{'weakest hit':>13}   separates?")
    print("-" * 62)
    for name, rows in runs:
        a = [r for r in rows if r["expect"] == "answerable"]
        h = sum(r["hit"] for r in a)
        leak = max((r["top"] for r in rows if r["expect"] == "refuse"), default=0)
        weakest = min((r["top"] for r in a if r["hit"]), default=0)
        sep = "yes" if leak < weakest else "NO"
        print(f"{name:<9}{h}/{len(a)}{h*100//max(len(a),1):>7}%   "
              f"{leak:>11.3f}{weakest:>13.3f}   {sep}")
    print("\nLeak and hit columns are comparable DOWN a row, never across rows:\n"
          "BM25 is unbounded, cosine is [-1,1], RRF tops out near 0.03.")

    # The whole reason to run both: not the totals, the disagreements.
    by = {name: {r["qid"]: r for r in rows} for name, rows in runs}
    print("\nwhere they disagree")
    print("-" * 46)
    any_diff = False
    for q in ans:
        b, e = by["bm25"][q["qid"]]["hit"], by["embed"][q["qid"]]["hit"]
        if b != e:
            any_diff = True
            print(f"  {'BM25 only ' if b else 'EMBED only'}  {q['question'][:52]}")
    if not any_diff:
        print("  none — the two rankers agree on every answerable question.")
        print("  That is a real result: on this corpus the embedding model is")
        print("  not buying you anything BM25 was not already giving you, and")
        print("  it costs 274 MB and a forward pass per record to run.")

    # A tie in the TOTAL is not a tie in the composition. Hybrid reached 19/25
    # on the same run where embeddings reached 19/25, and the obvious reading —
    # "RRF adds nothing" — is only true if it is the SAME nineteen. RRF reorders
    # a merged pool, so it can rescue a question the semantic ranker missed and
    # drop one it had, netting zero while changing which parent gets an answer.
    # Equal numbers were the thing that misled this project in Week 5; print the
    # set difference, not the count.
    if "hybrid" in by:
        rescued = [q for q in ans
                   if by["hybrid"][q["qid"]]["hit"] and not by["embed"][q["qid"]]["hit"]]
        dropped = [q for q in ans
                   if by["embed"][q["qid"]]["hit"] and not by["hybrid"][q["qid"]]["hit"]]
        print("\nwhat fusing actually changed, question by question")
        print("-" * 46)
        for q in rescued:
            print(f"  RRF RESCUED  {q['question'][:52]}")
        for q in dropped:
            print(f"  RRF DROPPED  {q['question'][:52]}")
        if not rescued and not dropped:
            print("  nothing — hybrid hit the identical set embeddings hit.")
            print("  Fusing BM25 in changed the ranking and changed no outcome,")
            print("  so the lexical index is pure maintenance cost here.")
        else:
            print(f"  net {len(rescued) - len(dropped):+d} questions, "
                  f"{len(rescued)} rescued and {len(dropped)} dropped.")
            print("  Equal totals, different questions. Read the lists, not the")
            print("  count — a wash in the metric is not a wash for a parent.")

    OUT.mkdir(exist_ok=True)
    doc = Path("docs/retrieval-compare.md")
    doc.parent.mkdir(exist_ok=True)
    with open(doc, "w", encoding="utf-8") as f:
        f.write(f"# Retrieval — BM25 vs embeddings\n\n")
        f.write(f"{len(recs)} records · {len(ans)} answerable questions · "
                f"k={args.k} · `{args.model}`\n\n")
        f.write("| ranker | hit@%d | worst refusal leak |\n|---|---|---|\n" % args.k)
        for name, rows in runs:
            a = [r for r in rows if r["expect"] == "answerable"]
            h = sum(r["hit"] for r in a)
            leak = max((r["top"] for r in rows if r["expect"] == "refuse"), default=0)
            f.write(f"| {name} | {h}/{len(a)} ({h*100//max(len(a),1)}%) | {leak:.2f} |\n")
        f.write("\n## Disagreements\n\n")
        for q in ans:
            b, e = by["bm25"][q["qid"]]["hit"], by["embed"][q["qid"]]["hit"]
            if b != e:
                f.write(f"- **{'BM25' if b else 'embeddings'} only** — {q['question']}\n")
        if "hybrid" in by:
            rescued = [q for q in ans if by["hybrid"][q["qid"]]["hit"]
                       and not by["embed"][q["qid"]]["hit"]]
            dropped = [q for q in ans if by["embed"][q["qid"]]["hit"]
                       and not by["hybrid"][q["qid"]]["hit"]]
            f.write("\n## What fusing actually changed\n\n")
            if not rescued and not dropped:
                f.write("Hybrid hit the **identical set** embeddings hit — not "
                        "merely the same count. Fusing BM25 in changed the "
                        "ranking and changed no outcome, so on this corpus the "
                        "lexical index is maintenance cost with nothing behind "
                        "it.\n")
            else:
                for q in rescued:
                    f.write(f"- **RRF rescued** — {q['question']}\n")
                for q in dropped:
                    f.write(f"- **RRF dropped** — {q['question']}\n")
                f.write(f"\nNet {len(rescued) - len(dropped):+d}: "
                        f"{len(rescued)} rescued, {len(dropped)} dropped. Equal "
                        f"totals, different questions — a wash in the metric is "
                        f"not a wash for a parent.\n")

        f.write("\n## Which one ships, and why\n\n"
                "_Name the cost as well as the score. An embedding model that wins "
                "by one question is not obviously worth 274 MB on a club's laptop._\n")
    print(f"\nwrote {doc}")


if __name__ == "__main__":
    main()
