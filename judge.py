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
GROUNDED_V1 = (
    "You answer questions for parents using ONLY the club documents below. "
    "Do not use general knowledge about how clubs usually work. Do not guess. "
    "If the documents do not contain the answer, reply with exactly this "
    "sentence and nothing after it: "
    "That is not covered in the club documents."
)

# V1 refused four questions whose answer was sitting in the context it was
# handed (q09 referee, q11 play up, q28 tryout, q30 switch teams). Two of its
# three instructions are prohibitions, and "Do not guess" is the broadest thing
# in the prompt — a 3B model reads it as "decline unless certain" and declines.
#
# V2 changes the shape rather than the strictness. The search instruction comes
# first and is positive. The prohibition is narrowed from "do not guess" to the
# thing actually being prevented: importing facts the documents do not contain.
# Refusal is gated behind a test the model can apply — nothing in the documents
# TOUCHES the question — instead of a confidence threshold it cannot calibrate.
#
# This is expected to cost correct refusals. A prompt that refuses less will
# refuse less on the must-refuse rows too, and that trade is the entire point of
# running both: `--prompt v1` and `--prompt v2` write separate files so the two
# can be read side by side instead of one replacing the other.
GROUNDED_V2 = (
    "You answer questions for parents using ONLY the club documents below.\n"
    "First, search the documents for anything that answers the question, even "
    "partially. If you find it, answer in one or two sentences using what the "
    "documents say.\n"
    "Do not add facts from general knowledge about how clubs usually work.\n"
    "Only if nothing in the documents touches the question, reply with exactly "
    "this sentence and nothing after it: "
    "That is not covered in the club documents."
)

PROMPTS = {"v1": GROUNDED_V1, "v2": GROUNDED_V2}

# The sentence the prompt asks for, with the negation removed. The models drop
# words from it, so the negation cannot be part of the match.
REFUSAL_CORE = "covered in the club documents"
REFUSAL_SENTENCE = "That is not covered in the club documents."

# ---------------------------------------------------------------- the gate
#
# Prompt v1 and v2 are better than each other on opposite halves of the
# question set, from one rewritten paragraph. A prompt has one setting and the
# questions have two populations, so no wording settles it.
#
# The gate splits the populations first. It reads the question and the retrieved
# context — NOT a candidate answer — and decides only whether the answer is in
# there. MISSING short-circuits: the refusal sentence is emitted verbatim and
# the answerer is never called, which removes the fabrication path entirely for
# those rows rather than asking a 3B model to resist it. COVERED hands the
# question to the permissive prompt, which is where v2 earns its three answers.
#
# This is a HARDER task than the judge's. The judge sees question + context +
# answer and checks one against the other; the gate sees question + context and
# has to predict. The judge's 9/15 does not transfer and should not be quoted as
# if it will — the gate accuracy table below is what says whether routing works.
GATE = (
    "You decide whether a set of club documents contains the answer to a "
    "parent's question. You are not answering the question.\n\n"
    "Reply with exactly one word:\n"
    "COVERED - the documents state the answer\n"
    "MISSING - the documents do not state the answer\n\n"
    "Documents that discuss the general topic without stating the specific "
    "answer are MISSING. Reply with one word only."
)


def gate_of(raw):
    u = (raw or "").upper()
    for word in ("MISSING", "COVERED"):
        if word in u:
            return word
    return "UNPARSED"


def refusal_kind(answer):
    """None, "clean", or "corrupt".

    q36 answered "That is covered in the club documents." — the template with
    `not` deleted. A substring test for "not covered in the club documents"
    missed it, so a sentence carrying no information was scored as an answer and
    the judge then rated it SUPPORTED.

    The failure was asymmetric, which is why it mattered: on a must-refuse row a
    corrupted refusal is scored as a leak, so the system is punished for
    refusing correctly; on an answerable row it is scored as an answer, which
    inflates the grounded count. Floor in one direction, inflation in the other.

    So match on the core phrase and use length as the discriminator — a refusal
    is a short sentence and nothing else, while an answer that happens to
    mention the documents keeps going. `corrupt` is reported separately rather
    than folded in, because a model that cannot copy one sentence reliably is a
    finding about the model and not about retrieval."""
    a = " ".join((answer or "").lower().split()).strip(' ."')
    if REFUSAL_CORE not in a or len(a) > 90:
        return None
    return "clean" if "not " + REFUSAL_CORE in a else "corrupt"

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
    ap.add_argument("--prompt", choices=sorted(PROMPTS), default="v1",
                    help="which grounded prompt to answer with")
    ap.add_argument("--label", default="", help="extra tag for the output files")
    ap.add_argument("--gate", default="",
                    help="model that decides COVERED/MISSING before answering; "
                         "must differ from --judge, or the grader is grading "
                         "its own routing decision")
    args = ap.parse_args()
    grounded = PROMPTS[args.prompt]
    # The grader's verdict IS the measurement. If the same model gates and
    # grades, a question it ruled COVERED gets its answer graded by the model
    # that already decided the context covers it — the Week 5 circularity in a
    # new place, where the proposer and the scorer shared a mechanism.
    if args.gate and args.gate == args.judge:
        raise SystemExit(
            f"--gate and --judge are both {args.judge}. The grader would be "
            f"grading its own routing call.\n"
            f"  try: --gate llama3.2:1b --judge {args.judge}")

    from config import client
    cli = client()

    recs = [json.loads(l) for l in open(RECORDS, encoding="utf-8") if l.strip()]
    qs = [json.loads(l) for l in open(QUESTIONS, encoding="utf-8") if l.strip()]
    if args.limit:
        qs = qs[:args.limit]
    texts = [f"{r['title']} {r['text']}" for r in recs]

    print(f"{len(recs)} records · {len(qs)} questions · k={args.k}")
    print(f"answerer: {args.answerer}   judge: {args.judge}   "
          f"prompt: {args.prompt}"
          + (f"   gate: {args.gate}" if args.gate else "   gate: off") + "\n")

    bm = BM25(texts)
    em = Embedded(texts, args.embed_model, OUT / f"embeddings-{args.embed_model}.json")

    def retrieve(q, k):
        return [(i, s) for i, s in rrf(bm.search(q, k * 2), em.search(q, k * 2))[:k]]

    rows = []
    for n, q in enumerate(qs, 1):
        hits = retrieve(q["question"], args.k)
        context = "\n\n".join(f"[{recs[i]['doc_id']}] {texts[i]}" for i, _ in hits)

        gate = ""
        secs = 0.0
        if args.gate:
            raw_gate, gsecs = ask_model(
                cli, args.gate, GATE,
                f"Club documents:\n\n{context}\n\n"
                f"Parent's question: {q['question']}", max_tokens=8)
            gate = gate_of(raw_gate)
            secs += gsecs

        if gate == "MISSING":
            # Short-circuit. Nothing generates, so nothing can be invented.
            answer = REFUSAL_SENTENCE
        else:
            answer, asecs = ask_model(
                cli, args.answerer, grounded,
                f"Club documents:\n\n{context}\n\n"
                f"Parent's question: {q['question']}")
            secs += asecs

        kind = refusal_kind(answer)
        raw_judge, _ = ask_model(
            cli, args.judge, JUDGE,
            f"SOURCE TEXT:\n{context}\n\nQUESTION:\n{q['question']}\n\n"
            f"ANSWER:\n{answer}", max_tokens=8)
        v = verdict_of(raw_judge)
        # A refusal is not a judgement call, so it overrules a small judge that
        # misreads one — including a refusal the model mangled.
        if kind:
            v = "REFUSED"

        retrieved_ok = ""
        if q["expect"] == "answerable":
            good = {i for i, t in enumerate(texts) if contains_all(t, q["keys"])}
            retrieved_ok = int(any(i in good for i, _ in hits))

        rows.append({"qid": q["qid"], "expect": q["expect"], "verdict": v,
                     "gate": gate, "refusal": kind or "",
                     "retrieved": retrieved_ok,
                     "secs": round(secs, 1), "question": q["question"],
                     "answer": answer.replace("\n", " ")})
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
    # UNSUPPORTED on ANY row is a fabrication, and on a must-refuse row it is
    # the worst outcome in the matrix: the model invented an answer to a
    # question the documents cannot answer at all. Filtering to `ans` here
    # excluded exactly that case, so prompt v2 fabricated an injury procedure
    # ("ask the referee if you may enter the field") and the report printed
    # INVENTED 0. A metric that cannot see its own worst outcome is worse than
    # no metric, because it is quotable.
    made_up = [r for r in rows if r["verdict"] == "UNSUPPORTED"]
    made_up_unanswerable = [r for r in made_up if r["expect"] == "refuse"]
    over_refused = [r for r in ans if r["verdict"] == "REFUSED" and r["retrieved"] == 1]

    print(f"\n{'=' * 62}")
    print(f"  correct refusals   {correct_refusals}/{len(ref)}   "
          f"declined when the corpus has no answer")
    print(f"  answered, grounded {answered_ok}/{len(ans)}   "
          f"answered and the context supports it")
    print(f"  INVENTED           {len(made_up)}      "
          f"answered something the context does not say")
    print(f"    of those, on questions the corpus CANNOT answer: "
          f"{len(made_up_unanswerable)}")
    print(f"  over-refused       {len(over_refused)}      "
          f"declined even though the answer was retrieved")
    corrupt = [r for r in rows if r["refusal"] == "corrupt"]

    # Gate accuracy against something objective, not against the label.
    #
    # The gate reads the RETRIEVED CONTEXT, so the right question is "is the
    # answer in this context", and `retrieved` already answers it exactly:
    # 1 means some record in the top k contains every answer key. For a
    # must-refuse question no record anywhere contains it, so MISSING is right.
    #
    # That makes MISSING the correct call on an answerable question the
    # retriever missed — six of them on this set. Grading the gate against the
    # LABEL would score those as errors and push it toward answering from
    # context that does not contain the answer, which is the fabrication path.
    # The gate's job is honesty about what was retrieved, not agreement with the
    # eval's optimism.
    def gate_truth(r):
        return "COVERED" if (r["expect"] == "answerable"
                             and r["retrieved"] == 1) else "MISSING"

    gated = [r for r in rows if r["gate"]]
    print(f"  mangled refusals   {len(corrupt)}      "
          f"meant to refuse, dropped a word from the sentence")
    print(f"{'=' * 62}")
    if gated:
        right = [r for r in gated if r["gate"] == gate_truth(r)]
        cov_t = [r for r in gated if gate_truth(r) == "COVERED"]
        mis_t = [r for r in gated if gate_truth(r) == "MISSING"]
        print(f"  GATE  {len(right)}/{len(gated)} correct, judged against "
              f"whether the answer was actually in the retrieved context")
        print(f"    said COVERED when it was:   "
              f"{sum(1 for r in cov_t if r['gate'] == 'COVERED')}/{len(cov_t)}")
        print(f"    said MISSING when it was:   "
              f"{sum(1 for r in mis_t if r['gate'] == 'MISSING')}/{len(mis_t)}")
        unp = [r for r in gated if r["gate"] == "UNPARSED"]
        if unp:
            print(f"    UNPARSED (counted as COVERED, so it answers): {len(unp)}")
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
    parts = []
    if args.prompt != "v1":
        parts.append(args.prompt)
    if args.gate:
        parts.append("gated")
    if args.limit:
        parts.append(f"limit{args.limit}")
    if args.label:
        parts.append(args.label)
    suffix = "-" + "-".join(parts) if parts else ""
    cols = ["qid", "expect", "verdict", "gate", "refusal", "retrieved", "secs",
            "question", "answer"]
    with open(OUT / f"judge{suffix}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    doc = Path(f"docs/judge-report{suffix}.md")
    doc.parent.mkdir(exist_ok=True)
    with open(doc, "w", encoding="utf-8") as f:
        f.write(f"# Model judge\n\n{len(recs)} records · {len(qs)} questions · "
                f"hybrid retrieval, k={args.k}\n\n"
                f"- answerer: `{args.answerer}`\n- judge: `{args.judge}`\n"
                f"- grounded prompt: `{args.prompt}`\n"
                f"- gate: `{args.gate or 'off'}`\n\n")
        f.write("| | | |\n|---|---|---|\n")
        f.write(f"| correct refusals | {correct_refusals}/{len(ref)} | "
                f"declined when the corpus has no answer |\n")
        f.write(f"| answered, grounded | {answered_ok}/{len(ans)} | "
                f"and the context supports it |\n")
        f.write(f"| **invented** | **{len(made_up)}** | "
                f"answered something the context does not say |\n")
        f.write(f"| **invented on unanswerable** | **{len(made_up_unanswerable)}** | "
                f"fabricated an answer where the documents have none |\n")
        f.write(f"| over-refused | {len(over_refused)} | "
                f"declined although the answer was retrieved |\n")
        f.write(f"| mangled refusals | {len(corrupt)} | "
                f"meant to refuse, dropped a word from the sentence |\n")
        f.write(f"\nFor comparison, the best a retrieval score could do on the "
                f"first row was **0/{len(ref)}** — on every ranker tried.\n")
        if gated:
            right = [r for r in gated if r["gate"] == gate_truth(r)]
            cov_t = [r for r in gated if gate_truth(r) == "COVERED"]
            mis_t = [r for r in gated if gate_truth(r) == "MISSING"]
            f.write(f"\n## The gate\n\n`{args.gate}` reads the question and the "
                    f"retrieved context and decides COVERED or MISSING before "
                    f"anything is generated. MISSING emits the refusal sentence "
                    f"and never calls the answerer, so a routed-out question has "
                    f"no path to a fabricated answer.\n\n"
                    f"Scored against whether the answer was actually in the "
                    f"retrieved context — not against the label, because MISSING "
                    f"is the correct call on an answerable question the retriever "
                    f"missed.\n\n"
                    f"| | |\n|---|---|\n"
                    f"| gate correct | {len(right)}/{len(gated)} |\n"
                    f"| COVERED when the answer was there | "
                    f"{sum(1 for r in cov_t if r['gate'] == 'COVERED')}/{len(cov_t)} |\n"
                    f"| MISSING when it was not | "
                    f"{sum(1 for r in mis_t if r['gate'] == 'MISSING')}/{len(mis_t)} |\n")
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
