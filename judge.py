"""Week 7 — the model judge. The thing that finally attacks `refused 0/11`.

    ollama pull qwen2.5:1.5b          # the judge, if you do not have it
    python judge.py                   # answer every question, then judge it
    python judge.py --k 3
    python judge.py --answerer llama3.2:latest --judge qwen2.5:1.5b

THE PROBLEM THIS EXISTS FOR
  Across three ranking functions and six weeks, one result never moved:

      refused 0/11 — no score threshold separates "found the answer" from
      "found words that look like the question"

  On BM25 the worst leak scored 17.91 against a weakest genuine hit of 6.28. The
  wrong answer outscored the right one. That is not a tuning problem. A
  retrieval score measures similarity between a query and a passage; whether the
  passage ANSWERS the question is a different property, and no ranking function
  looks at it.

  So stop asking the ranker. Retrieve, hand the context to a model, and let a
  SECOND model read the question, the context and the answer, and say whether
  the answer was actually supported.

THREE OUTCOMES, NOT TWO
  answered      the model answered and the context supports it
  refused       the model declined
  unsupported   the model answered and the context does NOT support it

  That third one is the whole reason for the exercise. A system that answers
  everything scores perfectly on "answer rate" and is unshippable. Counting
  refusals alone cannot see it either — only reading the answer against the
  context can.

TWO MODELS ON PURPOSE
  The answerer and the judge are different models by default. A model grading its
  own output is the same circularity that inflated Week 5's hit@5 from 35% to
  72% — when the thing generating your test data and the thing being tested share
  a mechanism, you measure the mechanism.

  Caveat worth writing in the week note: qwen2.5:1.5b is a small judge. It will
  be wrong sometimes. Spot-check ten rows by hand before quoting any number from
  here, and say in the note that you did.

OUTPUT
  docs/judge-report.md
  out/judge.csv
"""
import argparse
import csv
import json
import re
import time
from pathlib import Path

from retrieval_eval import BM25, contains_all
from embed_eval import Embedded, rrf, OUT

RECORDS = Path("data/records-real.jsonl")
QUESTIONS = Path("data/questions-real.jsonl")

# The refusal sentence goes at the very END, with nothing after it. Week 2:
# qwen2.5:0.5b copied the sentence AND the instruction that followed it, so the
# parent saw the prompt. Nothing behind it means nothing to leak.
GROUNDED = (
    "You answer questions for parents using ONLY the club documents below. "
    "Do not use general knowledge about how clubs usually work. Do not guess. "
    "If the documents do not contain the answer, reply with exactly this "
    "sentence and nothing after it: "
    "That is not covered in the club documents."
)

REFUSAL = "not covered in the club documents"

# The judge sees the question, the context and the answer — never the expected
# label. Giving it the label would make it agree with the eval by construction.
JUDGE = (
    "You are checking whether an answer is supported by the source text it was "
    "supposed to come from.\n\n"
    "Reply with exactly one word:\n"
    "SUPPORTED   - the answer is stated in the source text\n"
    "REFUSED     - the answer declines to answer\n"
    "UNSUPPORTED - the answer states something the source text does not say\n\n"
    "An answer that is true in general but absent from the source text is "
    "UNSUPPORTED. Reply with one word only."
)


def ask_model(cli, model, system, user, max_tokens=200, temperature=0, seed=7):
    t0 = time.perf_counter()
    try:
        r = cli.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=temperature, seed=seed, max_tokens=max_tokens)
        return (r.choices[0].message.content or "").strip(), time.perf_counter() - t0
    except Exception as e:
        return f"[{type(e).__name__}: {e}]", time.perf_counter() - t0


def verdict_of(raw):
    """First recognised word wins. Small models pad their answers."""
    u = (raw or "").upper()
    for word in ("UNSUPPORTED", "SUPPORTED", "REFUSED"):
        if word in u:
            return word
    return "UNPARSED"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--answerer", default="llama3.2:latest")
    ap.add_argument("--judge", default="qwen2.5:1.5b")
    ap.add_argument("--embed-model", default="nomic-embed-text")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0, help="first N questions only")
    args = ap.parse_args()

    from config import client
    cli = client()

    recs = [json.loads(l) for l in open(RECORDS, encoding="utf-8") if l.strip()]
    qs = [json.loads(l) for l in open(QUESTIONS, encoding="utf-8") if l.strip()]
    if args.limit:
        qs = qs[:args.limit]
    texts = [f"{r['title']} {r['text']}" for r in recs]

    print(f"{len(recs)} records · {len(qs)} questions · k={args.k}")
    print(f"answerer: {args.answerer}   judge: {args.judge}\n")

    bm = BM25(texts)
    em = Embedded(texts, args.embed_model, OUT / f"embeddings-{args.embed_model}.json")

    def retrieve(q, k):
        return [(i, s) for i, s in rrf(bm.search(q, k * 2), em.search(q, k * 2))[:k]]

    rows = []
    for n, q in enumerate(qs, 1):
        hits = retrieve(q["question"], args.k)
        context = "\n\n".join(f"[{recs[i]['doc_id']}] {texts[i]}" for i, _ in hits)

        answer, secs = ask_model(
            cli, args.answerer, GROUNDED,
            f"Club documents:\n\n{context}\n\nParent's question: {q['question']}")

        said_refusal = REFUSAL in answer.lower()
        raw_judge, _ = ask_model(
            cli, args.judge, JUDGE,
            f"SOURCE TEXT:\n{context}\n\nQUESTION:\n{q['question']}\n\n"
            f"ANSWER:\n{answer}", max_tokens=8)
        v = verdict_of(raw_judge)
        # The literal refusal string is not a judgement call, so it overrules a
        # small judge that misreads one.
        if said_refusal:
            v = "REFUSED"

        retrieved_ok = ""
        if q["expect"] == "answerable":
            good = {i for i, t in enumerate(texts) if contains_all(t, q["keys"])}
            retrieved_ok = int(any(i in good for i, _ in hits))

        rows.append({"qid": q["qid"], "expect": q["expect"], "verdict": v,
                     "retrieved": retrieved_ok, "secs": round(secs, 1),
                     "question": q["question"], "answer": answer.replace("\n", " ")})
        mark = {"SUPPORTED": "ok  ", "REFUSED": "ref ",
                "UNSUPPORTED": "MADE UP", "UNPARSED": "????"}[v]
        print(f"  {q['qid']}  {q['expect'][:6]:<6} {mark:<8} {q['question'][:44]}")

    ans = [r for r in rows if r["expect"] == "answerable"]
    ref = [r for r in rows if r["expect"] == "refuse"]

    # On must-refuse questions, refusing IS the correct behaviour.
    correct_refusals = sum(1 for r in ref if r["verdict"] == "REFUSED")
    leaked = [r for r in ref if r["verdict"] != "REFUSED"]
    # On answerable questions, refusing when the answer WAS retrieved is a miss.
    answered_ok = sum(1 for r in ans if r["verdict"] == "SUPPORTED")
    made_up = [r for r in ans if r["verdict"] == "UNSUPPORTED"]
    over_refused = [r for r in ans if r["verdict"] == "REFUSED" and r["retrieved"] == 1]

    print(f"\n{'=' * 62}")
    print(f"  correct refusals   {correct_refusals}/{len(ref)}   "
          f"declined when the corpus has no answer")
    print(f"  answered, grounded {answered_ok}/{len(ans)}   "
          f"answered and the context supports it")
    print(f"  INVENTED           {len(made_up)}      "
          f"answered something the context does not say")
    print(f"  over-refused       {len(over_refused)}      "
          f"declined even though the answer was retrieved")
    print(f"{'=' * 62}")
    print(f"  BM25 could not do the first row at all: 0/{len(ref)}.")
    if len(ref):
        print(f"  A model reading the context gets {correct_refusals}/{len(ref)}.")

    if made_up:
        print("\nINVENTED — read every one of these by hand:")
        for r in made_up:
            print(f"  {r['qid']}  {r['question'][:46]}")
            print(f"        {r['answer'][:150]}")

    OUT.mkdir(exist_ok=True)
    # A partial run must never overwrite a full one. --limit is for trying the
    # pipeline out, and the first time it was used it silently replaced a
    # 40-question report with a 10-question one. A flag that destroys the result
    # you were about to read is a bad flag.
    suffix = f"-limit{args.limit}" if args.limit else ""
    cols = ["qid", "expect", "verdict", "retrieved", "secs", "question", "answer"]
    with open(OUT / f"judge{suffix}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    doc = Path(f"docs/judge-report{suffix}.md")
    doc.parent.mkdir(exist_ok=True)
    with open(doc, "w", encoding="utf-8") as f:
        f.write(f"# Model judge\n\n{len(recs)} records · {len(qs)} questions · "
                f"hybrid retrieval, k={args.k}\n\n"
                f"- answerer: `{args.answerer}`\n- judge: `{args.judge}`\n\n")
        f.write("| | | |\n|---|---|---|\n")
        f.write(f"| correct refusals | {correct_refusals}/{len(ref)} | "
                f"declined when the corpus has no answer |\n")
        f.write(f"| answered, grounded | {answered_ok}/{len(ans)} | "
                f"and the context supports it |\n")
        f.write(f"| **invented** | **{len(made_up)}** | "
                f"answered something the context does not say |\n")
        f.write(f"| over-refused | {len(over_refused)} | "
                f"declined although the answer was retrieved |\n")
        f.write(f"\nFor comparison, the best a retrieval score could do on the "
                f"first row was **0/{len(ref)}** — on every ranker tried.\n")
        if leaked:
            f.write("\n## Leaked — answered a question the corpus cannot answer\n\n")
            for r in leaked:
                f.write(f"- **{r['question']}** — {r['answer'][:200]}\n")
        f.write("\n## Did you spot-check the judge?\n\n"
                "_A 1.5B judge is wrong sometimes. Read ten rows of `out/judge.csv` "
                "by hand, say how many the judge got right, and quote that number "
                "next to every figure above. A judge you have not audited is the "
                "same mistake as an eval you have not audited._\n")
    print(f"\nwrote {doc} and out/judge{suffix}.csv")


if __name__ == "__main__":
    main()
