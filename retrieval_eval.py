"""Week 5 — the baseline. Objective, repeatable, and not a matter of opinion.

    python retrieval_eval.py                       # the real corpus, BM25
    python retrieval_eval.py --k 3
    python retrieval_eval.py --file data/records.jsonl   # Northside, to compare

WHAT THIS ANSWERS THAT FOUR HAND REVIEWS COULD NOT

  answerable    Is there ANY SINGLE record in the whole corpus containing every
                answer key? This is the self-contained rate, measured instead of
                judged. It does not care about bullet points, capitalisation,
                spacing, or how anyone felt on the day. Same number every run.

  hit@k         Is such a record inside the top k the retriever actually
                returned? The gap between `answerable` and `hit@k` is the
                retriever's fault. Everything below `answerable` is the corpus's
                fault. Before this, those two failures were indistinguishable,
                which is why "under 60% means the chunking is the problem" was a
                guess.

  union@k       Do the top k records TOGETHER contain every key, even if no
                single one does? When union@k is well above hit@k, the answer
                exists but is split across chunks — a merge problem, not a
                retrieval problem.

  refused       On the must-refuse questions, did the top result score below the
                threshold? A retriever with no floor always returns its least-bad
                guess, and a model handed a least-bad guess will answer from it.

WHY THE CASES NAME DOCUMENTS AND NOT RECORDS
  The Week 3 eval named the record to retrieve by id. When the fee table was
  split into per-band records, the case handed models a paragraph with no fees in
  it and the scores did not move — the eval was blind to the change it existed to
  measure. Cases here name answer KEYS and at most a source document, so
  rechunking cannot invalidate them. Rechunk freely; rerun; the number means the
  same thing.

RETRIEVAL
  BM25 over whitespace tokens. Deliberately the dumbest thing that works: this is
  the baseline the embedding retriever has to beat in Weekday B, and a baseline
  you do not understand is not a baseline. `search()` is the only function the
  embedding version needs to replace.

OUTPUT
  docs/retrieval-baseline.md
  out/retrieval_eval.csv
"""
import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

RECORDS = Path("data/records-real.jsonl")
QUESTIONS = Path("data/questions-real.jsonl")

TOKEN = re.compile(r"[a-z0-9$£€.\-/]+")
# Words that appear in nearly every record and carry no retrieval signal. Kept
# short on purpose — an aggressive stop list quietly deletes real queries like
# "who do I call" and then you spend an afternoon wondering why.
STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "for", "is", "are",
        "be", "on", "at", "it", "this", "that", "with", "as", "by", "from"}


def tokens(text):
    return [t for t in TOKEN.findall(text.lower()) if t not in STOP]


class BM25:
    """Okapi BM25. Roughly: a term is worth more when it is rare across the
    corpus, more when it is frequent in this record, and less when the record is
    long — so a 5,000-character slab cannot win simply by containing everything.

    That last property matters here. club-02's seven slabs would dominate a raw
    term-count ranking, and the eval would report excellent retrieval into
    records no parent could read."""

    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.docs = [tokens(d) for d in docs]
        self.len = [len(d) for d in self.docs]
        self.avg = sum(self.len) / max(len(self.docs), 1)
        self.tf = [Counter(d) for d in self.docs]
        df = Counter()
        for d in self.docs:
            df.update(set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def score(self, query, i):
        s = 0.0
        tf, dl = self.tf[i], self.len[i]
        for t in tokens(query):
            f = tf.get(t, 0)
            if not f:
                continue
            s += self.idf.get(t, 0) * (f * (self.k1 + 1)) / (
                f + self.k1 * (1 - self.b + self.b * dl / max(self.avg, 1)))
        return s

    def search(self, query, k=5):
        scored = [(self.score(query, i), i) for i in range(len(self.docs))]
        scored.sort(key=lambda p: -p[0])
        return [(i, s) for s, i in scored[:k]]


def contains_all(text, keys):
    """Case-insensitive, whitespace-insensitive containment.

    Whitespace-insensitive because the extractor still loses the odd word space,
    and a record that says `Respectand Responsibility` answers the question about
    club values exactly as well as one that says it correctly. Spacing is a
    cosmetic defect; the review kept scoring it as a fatal one."""
    hay = "".join(text.split()).lower()
    return all("".join(k.split()).lower() in hay for k in keys)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(RECORDS))
    ap.add_argument("--questions", default=str(QUESTIONS))
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--floor", type=float, default=2.0,
                    help="BM25 score below which a result counts as 'nothing "
                         "relevant found'. Tune it on the must-refuse cases, "
                         "then leave it alone.")
    args = ap.parse_args()

    recs = [json.loads(l) for l in open(args.file, encoding="utf-8") if l.strip()]
    qs = [json.loads(l) for l in open(args.questions, encoding="utf-8") if l.strip()]
    texts = [f"{r['title']} {r['text']}" for r in recs]
    bm = BM25(texts)

    print(f"{len(recs)} records · {len(qs)} questions · k={args.k} · floor={args.floor}\n")

    rows, by_doc = [], defaultdict(lambda: [0, 0])
    for q in qs:
        hits = bm.search(q["question"], args.k)
        top_score = hits[0][1] if hits else 0.0

        if q["expect"] == "refuse":
            ok = top_score < args.floor
            rows.append({"qid": q["qid"], "category": q["category"],
                         "expect": "refuse", "answerable": "", "hit": "",
                         "union": "", "refused": int(ok),
                         "top_score": round(top_score, 2), "winner": ""})
            print(f"  {q['qid']}  refuse    {'ok' if ok else 'LEAKED'}"
                  f"   top={top_score:>6.2f}   {q['question'][:46]}")
            continue

        keys = q["keys"]
        answerable_idx = [i for i, t in enumerate(texts) if contains_all(t, keys)]
        answerable = bool(answerable_idx)
        hit_idx = next((i for i, _ in hits if i in answerable_idx), None)
        union = contains_all(" ".join(texts[i] for i, _ in hits), keys)

        winner = recs[hit_idx]["doc_id"] if hit_idx is not None else ""
        # Credit the document the answer was actually retrieved FROM. Crediting
        # `answerable_idx[0]` instead — the first record in file order that
        # happens to contain the keys — attributes the question to whichever
        # club was ingested earliest, which is not a fact about anything.
        src_idx = hit_idx if hit_idx is not None else (
            answerable_idx[0] if answerable else None)
        if src_idx is not None:
            src = recs[src_idx]["source_file"]
            by_doc[src][0] += 1
            if hit_idx is not None:
                by_doc[src][1] += 1

        rows.append({"qid": q["qid"], "category": q["category"],
                     "expect": "answerable", "answerable": int(answerable),
                     "hit": int(hit_idx is not None), "union": int(union),
                     "refused": "", "top_score": round(top_score, 2),
                     "winner": winner})

        mark = ("hit " if hit_idx is not None else
                "MISS" if answerable else "GONE")
        print(f"  {q['qid']}  {mark}      top={top_score:>6.2f}   "
              f"{q['question'][:46]}"
              + (f"   -> {winner}" if winner else ""))

    ans = [r for r in rows if r["expect"] == "answerable"]
    ref = [r for r in rows if r["expect"] == "refuse"]
    n = max(len(ans), 1)
    a = sum(r["answerable"] for r in ans)
    h = sum(r["hit"] for r in ans)
    u = sum(r["union"] for r in ans)

    print(f"\n{'='*62}")
    print(f"  answerable      {a}/{len(ans)}  ({a*100//n}%)   "
          f"the answer sits in one record somewhere")
    print(f"  hit@{args.k}           {h}/{len(ans)}  ({h*100//n}%)   "
          f"and the retriever found it")
    print(f"  union@{args.k}         {u}/{len(ans)}  ({u*100//n}%)   "
          f"the top {args.k} together contain it")
    if ref:
        r_ok = sum(r["refused"] for r in ref)
        print(f"  refused         {r_ok}/{len(ref)}         "
              f"declined when it should have")
    print(f"{'='*62}")
    print(f"  corpus  loses {len(ans)-a} questions — no single record answers them")
    print(f"  ranking loses {a-h} questions — a record answers it, top {args.k} missed it")

    # Where to put the refusal floor is a decision, not a constant. BM25 scores
    # are not comparable across corpora, so a number that worked for someone
    # else's documents means nothing here. Read it off your own two populations.
    if ref:
        worst_leak = max((r["top_score"] for r in ref), default=0)
        weakest_hit = min((r["top_score"] for r in ans if r["hit"]), default=0)
        print(f"\nrefusal floor: must-refuse questions top out at {worst_leak:.2f}; "
              f"the weakest real hit scores {weakest_hit:.2f}")
        if worst_leak < weakest_hit:
            print(f"  a floor anywhere in ({worst_leak:.2f}, {weakest_hit:.2f}) "
                  f"separates them cleanly — try --floor "
                  f"{(worst_leak + weakest_hit) / 2:.1f}")
        else:
            print("  the two overlap, so NO absolute floor separates them. That is "
                  "a finding, not a tuning problem: BM25 score is not a measure of "
                  "whether an answer is present. Week 6's model judge exists for "
                  "exactly this.")

    if by_doc:
        print("\nby document (of the questions it could answer, how many were found):")
        for src in sorted(by_doc):
            tot, got = by_doc[src]
            print(f"  {src:<14} {got}/{tot}")

    Path("out").mkdir(exist_ok=True)
    cols = ["qid", "category", "expect", "answerable", "hit", "union",
            "refused", "top_score", "winner"]
    with open("out/retrieval_eval.csv", "w", encoding="utf-8", newline="") as f:
        f.write(",".join(cols) + "\n")
        for r in rows:
            f.write(",".join(str(r[c]) for c in cols) + "\n")

    out = Path("docs/retrieval-baseline.md")
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("# Retrieval baseline\n\n")
        f.write(f"`{args.file}` — {len(recs)} records · {len(qs)} questions · "
                f"BM25 · k={args.k} · refusal floor {args.floor}\n\n")
        f.write("| metric | result | meaning |\n|---|---|---|\n")
        f.write(f"| answerable | {a}/{len(ans)} ({a*100//n}%) | one record holds the whole answer |\n")
        f.write(f"| hit@{args.k} | {h}/{len(ans)} ({h*100//n}%) | and it was retrieved |\n")
        f.write(f"| union@{args.k} | {u}/{len(ans)} ({u*100//n}%) | the top {args.k} together hold it |\n")
        if ref:
            f.write(f"| refused | {sum(r['refused'] for r in ref)}/{len(ref)} | declined correctly |\n")
        if by_doc:
            f.write("\n## By document\n\n| source | answerable | retrieved |\n|---|---|---|\n")
            for src in sorted(by_doc):
                tot, got = by_doc[src]
                f.write(f"| {src} | {tot} | {got} |\n")
        f.write("\n## Where the losses are\n\n"
                f"- **{len(ans)-a}** questions have no single record that answers them — corpus\n"
                f"- **{a-h}** questions have one and the ranking missed it — retriever\n")
        f.write("\n## What I change first, and why\n\n_one paragraph, before you change anything._\n")

    print(f"\nwrote {out} and out/retrieval_eval.csv")


if __name__ == "__main__":
    main()
