"""A two-minute preview of Weeks 4 and 5 — the same question, twice.

    python grounding_demo.py
    python grounding_demo.py --model qwen2.5:0.5b

Yesterday your chatbot said "I don't have that information about this club",
and this morning a smaller model invented "practice starts at 8:00 AM". Both
were asked a question whose answer was already sitting in data/records.jsonl.

This script asks four questions twice each:

    UNGROUNDED   question only, exactly what you have been doing all week
    GROUNDED     question with the relevant record pasted in above it

Nothing else changes. Same model, same temperature, same seed.

WHAT IS HONEST ABOUT THIS, AND WHAT IS NOT
  The retrieval is FAKE. Look at QUESTIONS below: I hand-wrote which record
  goes with which question. That is the one piece of cheating here, and it is
  precisely the piece Weeks 4 and 5 exist to remove — turning "Gisell already
  knew it was handbook-s1" into "the system found handbook-s1 out of 17, and
  will still find it out of 17,000."

  Everything else on this page is real. The prompt shape, the instruction to
  refuse when the context does not cover the question, the token cost of
  carrying the context — all of that survives into the finished system.

THE FOURTH QUESTION IS THE IMPORTANT ONE
  Three questions have answers in the corpus. The fourth does not, on purpose.
  Grounding is only worth having if the model still says "not in these
  documents" when the documents are silent. A system that answers three
  questions correctly and confidently invents the fourth is not better than
  where you started — it is worse, because now you trust it.

OUTPUT
  out/grounding_demo.md
"""
import argparse
import json
from pathlib import Path

from config import CONFIG, client

RECORDS = Path("data/records.jsonl")
OUT = Path("out")

# question -> the doc_id a real retriever would have to find on its own.
# None means "no record covers this", which is the control case.
QUESTIONS = [
    ("What should my child bring to practice?", "faq-F005"),
    ("How is my child's age group decided?", "handbook-s1"),
    ("After lightning is seen, how long before play can resume?", "handbook-s6"),
    ("What time is training tomorrow?", None),
]

PLAIN = ("You are the assistant for a youth sports club. Answer briefly and plainly.")

# The three sentences that turn a text generator into a document-answering
# system. Every one of them is doing work:
#   sentence 1 restricts the source of truth
#   sentence 2 blocks the "here is what clubs usually do" hedge that reads
#             like an answer and is not one
#   sentence 3 gives it permission to fail, which is what stops invention
#
# ORDER MATTERS, and this is a fix, not a preference. In the first version
# sentence 3 came second, and qwen2.5:0.5b answered question 4 with the
# refusal sentence PLUS the instruction that followed it in this prompt —
# it copied straight on past the end of the sentence it was told to emit.
# A small model that starts reproducing your system prompt keeps going until
# it runs out of prompt. So the literal string it must output now sits at the
# very end, with nothing behind it to leak.
GROUNDED = (
    "You are the assistant for a youth sports club. Answer using ONLY the "
    "club documents provided below. Do not add general knowledge about how "
    "clubs usually work. If the documents do not contain the answer, reply "
    "with exactly this sentence and nothing after it: "
    "That is not covered in the club documents."
)


def load():
    if not RECORDS.exists():
        raise SystemExit(f"{RECORDS} not found — run ingest.py first.")
    return {r["doc_id"]: r for r in
            (json.loads(line) for line in open(RECORDS, encoding="utf-8"))}


def ask(cli, model, system, user):
    r = cli.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=CONFIG["temperature"],
        seed=CONFIG["seed"],
        max_tokens=CONFIG["max_tokens"],
    )
    return (r.choices[0].message.content or "").strip()


def tokens(text):
    try:
        import tiktoken
        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        return len(text) // 4


def wrap(text, indent="    ", width=72):
    import textwrap
    out = []
    for para in (text or "[empty]").split("\n"):
        out.extend(textwrap.wrap(para, width) or [""])
    return "\n".join(indent + ln for ln in out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=CONFIG["model"])
    args = ap.parse_args()

    recs = load()
    cli = client()
    print(f"model: {args.model}   corpus: {len(recs)} records\n")

    results = []
    for question, doc_id in QUESTIONS:
        rec = recs.get(doc_id) if doc_id else None
        if doc_id and not rec:
            print(f"  ! {doc_id} is not in records.jsonl, skipping")
            continue

        # The whole corpus would not fit in a real system. Here it would, and
        # that is exactly why this demo cannot stand in for retrieval: at 17
        # records you could paste everything, at 17,000 you cannot.
        context = (f"[{rec['doc_id']}] {rec['title']}\n{rec['text']}"
                   if rec else "[no documents matched this question]")
        grounded_user = f"CLUB DOCUMENTS:\n{context}\n\nQUESTION: {question}"

        plain_answer = ask(cli, args.model, PLAIN, question)
        grounded_answer = ask(cli, args.model, GROUNDED, grounded_user)

        cost_plain = tokens(PLAIN + question)
        cost_grounded = tokens(GROUNDED + grounded_user)

        results.append({
            "question": question, "doc_id": doc_id,
            "plain": plain_answer, "grounded": grounded_answer,
            "cost_plain": cost_plain, "cost_grounded": cost_grounded,
        })

        print("=" * 74)
        print(f"{question}")
        print(f"  retrieved: {doc_id or 'NOTHING — no record covers this'}\n")
        print(f"  UNGROUNDED   ({cost_plain} prompt tokens)")
        print(wrap(plain_answer))
        print(f"\n  GROUNDED     ({cost_grounded} prompt tokens, "
              f"{cost_grounded - cost_plain:+d})")
        print(wrap(grounded_answer))
        print()

    OUT.mkdir(exist_ok=True)
    path = OUT / "grounding_demo.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Grounding demo — {args.model}\n\n"
                f"Retrieval is hand-written here. Weeks 4-5 replace that.\n\n")
        for r in results:
            f.write(f"## {r['question']}\n\n"
                    f"retrieved: `{r['doc_id'] or 'nothing'}`\n\n"
                    f"**Ungrounded** ({r['cost_plain']} prompt tokens)\n\n"
                    f"```\n{r['plain']}\n```\n\n"
                    f"**Grounded** ({r['cost_grounded']} prompt tokens)\n\n"
                    f"```\n{r['grounded']}\n```\n\n")

    extra = sum(r["cost_grounded"] - r["cost_plain"] for r in results)
    print(f"wrote {path}")
    print(f"grounding cost {extra} extra prompt tokens across "
          f"{len(results)} questions — on every single call, forever.\n")
    print("Three things to take from this:")
    print("  1. Where the ungrounded answer was wrong, it was wrong CONFIDENTLY.")
    print("  2. The grounded answers carry specifics no model could have guessed.")
    print("  3. Question 4 is the test. If it refused, the guard works. If it")
    print("     answered anyway, the guard does not — and finding that out is")
    print("     worth more than the three that went right.")


if __name__ == "__main__":
    main()
