"""Week 5 step 1, the fast way — find the answers, you approve them.

    python draft_answers.py                       # work the queue
    python draft_answers.py --show 6              # more candidates per question
    python draft_answers.py --keep q01,q03,q19    # redo everything else

WHAT THIS AUTOMATES, AND WHAT IT DELIBERATELY DOES NOT

  Automated: the hunting. For each question it searches the four handbooks and
  shows the passages that best match, each with its own proposed answer key. You
  press the number of the one that answers the question, or n if none does.

  The first version of this showed ONE candidate and asked y/n. Twenty-one
  straight `y` presses later, the eval contained keys like `The Club serves over
  1` and an acknowledgements page as the answer to "how are teams created". A
  yes/no prompt on a single option is not really a choice — it is a default with
  a confirmation step, and defaults get accepted. Several options with no
  default is a choice.

  Not automated: the questions. They come from real club FAQ pages — other
  clubs, writing down what parents actually ask them — not from these handbooks
  and not from anybody's idea of a good test case. That matters more than it
  looks. An eval whose questions were chosen by reading the corpus can only ask
  what the corpus already answers well, and will report a flattering number
  forever. Week 3 taught this the expensive way: the eval named the record to
  retrieve, so when the chunking changed the scores did not move.

  Not automated: the verdict. You accept or reject every proposal.

WHAT THIS COSTS YOU — SAY IT OUT LOUD IN THE WEEK NOTE
  The keys are proposed by a text search over the PDFs, so the eval measures:
  "can the retriever find, in a chunked corpus, what a plain text search found
  in the source document?" That is a genuine and useful question — it is exactly
  the chunking-plus-ranking question — but it is narrower than "can a parent get
  an answer", and a passage too mangled for a text search to match will never
  become a question at all. Expect the number to be optimistic. Write that down
  next to it.

  The searching happens over the RAW PDFs, never over data/records-real.jsonl.
  Proposing keys from the records would let the eval confirm its own chunking,
  and `answerable` would read 100% forever.

OUTPUT
  data/questions-real.jsonl   (append-only, same file make_questions.py writes)
"""
import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

RAW = Path("data/raw/real")
OUT = Path("data/questions-real.jsonl")

# Real questions from real club FAQ pages — AYSO Region 1031 and CVUSC — plus a
# few the handbooks themselves are clearly about. Add your own at the bottom;
# just do not go fishing in the records for ones that will score well.
SEED = [
    ("What do I do if my child gets a concussion?", "safety"),
    ("How many volunteer hours does my family have to do?", "volunteering"),
    ("What do I need to buy for my child to play?", "kit"),
    ("Do I need to buy a uniform?", "kit"),
    ("Who do I talk to first if I have a problem with the coach?", "conflict"),
    ("What happens if I yell at the referee?", "conduct"),
    ("What age groups does the club have?", "registration"),
    ("Can I get a refund if my child quits?", "money"),
    ("How many players are on a team?", "schedule"),
    ("Can my child play up an age group?", "registration"),
    ("Do I have to sign a photo release?", "registration"),
    ("When is practice and how often do teams practice?", "schedule"),
    ("How are the teams created?", "registration"),
    ("Do I have to volunteer?", "volunteering"),
    ("Where are the games played?", "schedule"),
    ("How big is the time commitment?", "schedule"),
    ("Can I coach from the sideline?", "conduct"),
    ("What happens if my child is injured during a game?", "safety"),
    ("Do boys and girls play on the same teams?", "registration"),
    ("How much does it cost to play?", "money"),
    ("Is there a payment plan?", "money"),
    ("What is the club's mission?", "registration"),
    ("Can I be an assistant coach?", "volunteering"),
    ("What if I cannot afford the fees?", "money"),
]

TOKEN = re.compile(r"[a-z0-9$£€]+")
STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "for", "is", "are",
        "be", "on", "at", "it", "this", "that", "with", "as", "by", "from",
        "do", "i", "my", "what", "how", "can", "if", "does", "will", "you"}


def toks(s):
    return [t for t in TOKEN.findall(s.lower()) if t not in STOP]


def passages(width=420, stride=260):
    """The four handbooks as overlapping windows of plain text.

    Overlapping on purpose: an answer that straddles a boundary is invisible to
    a non-overlapping window, and this step must not miss answers for the same
    reason the chunker does — that failure belongs to the chunker, and the eval
    exists to catch it there."""
    from pypdf import PdfReader
    out = []
    for pdf in sorted(RAW.glob("*.pdf")):
        try:
            text = " ".join(" ".join(
                (p.extract_text() or "") for p in PdfReader(pdf).pages).split())
        except Exception as e:
            print(f"  (skipping {pdf.name}: {e})")
            continue
        for i in range(0, max(len(text) - 1, 1), stride):
            chunk = text[i:i + width]
            if len(chunk) > 80:
                out.append((pdf.stem, chunk))
    return out


class Index:
    def __init__(self, docs):
        self.docs = docs
        self.tf = [Counter(toks(t)) for _, t in docs]
        df = Counter()
        for c in self.tf:
            df.update(c.keys())
        n = len(docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def top(self, q, k=3):
        qt = toks(q)
        scored = []
        for i, c in enumerate(self.tf):
            s = sum(self.idf.get(t, 0) * min(c.get(t, 0), 3) for t in qt)
            if s:
                scored.append((s, i))
        scored.sort(reverse=True)
        return [(self.docs[i][0], self.docs[i][1], s) for s, i in scored[:k]]


def propose_key(question, passage):
    """The shortest exact fragment of the passage that carries the answer.

    Prefers a sentence containing a number or an amount, because those are the
    keys that survive rewording — `$525` means one thing, `the fees are
    reasonable` means nothing a string test can check. Falls back to whichever
    sentence shares most words with the question."""
    qt = set(toks(question))
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", passage) if len(s.strip()) > 25]
    if not sentences:
        return ""

    def score(s):
        st = set(toks(s))
        hit = len(qt & st)
        numeric = 2 if re.search(r"[\$£€]\s?\d|\b\d{1,4}\b", s) else 0
        return hit + numeric

    best = max(sentences, key=score)
    if score(best) == 0:
        return ""

    # Trim to something short enough to be an exact match but long enough to be
    # unambiguous. Prefer the clause around the number if there is one.
    m = re.search(r"[^,;:]{0,45}(?:[\$£€]\s?[\d,]+|\b\d{1,4}\b)[^,;:]{0,45}", best)
    frag = m.group(0) if m else best
    # The window is a character count, so it can open in the middle of a word —
    # the first attempt proposed 'D TO FULFILL ONE OF THE VOLUNTEER POSITIONS',
    # which is the tail of 'EXPECTED'. A key that starts mid-word will never
    # match anything and looks like nonsense in the eval file.
    if m and m.start() > 0 and best[m.start() - 1] not in " \t":
        frag = frag.split(" ", 1)[1] if " " in frag else frag
    frag = frag.strip(" ,;:.")
    words = frag.split()
    while len(" ".join(words)) > 72 and len(words) > 4:
        words.pop()
    frag = " ".join(words).strip(" ,;:.")
    return frag if len(frag) >= 8 else ""


def ask(prompt, lower=True):
    import sys
    sys.stdout.write(prompt)
    sys.stdout.flush()
    line = sys.stdin.readline()
    if not line:
        return "q"
    line = line.strip()
    return line.lower() if lower else line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int, default=4,
                    help="candidate passages per question; each comes with its "
                         "own proposed key, and you pick by number")
    ap.add_argument("--keep", default="",
                    help="comma-separated qids to keep; every other question is "
                         "dropped and asked again. Use after a pass where you "
                         "accepted keys too quickly.")
    args = ap.parse_args()

    rows = []
    if OUT.exists():
        rows = [json.loads(l) for l in open(OUT, encoding="utf-8") if l.strip()]

    if args.keep:
        wanted = {q.strip().lower() for q in args.keep.split(",") if q.strip()}
        kept = [r for r in rows if r["qid"].lower() in wanted]
        with open(OUT, "w", encoding="utf-8") as f:
            for r in kept:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"kept {len(kept)} of {len(rows)}; the rest will be asked again.\n")
        rows = kept

    done = {r["question"].lower() for r in rows}
    n_existing = len(rows)

    print("Building the index over the four handbooks ...", flush=True)
    idx = Index(passages())
    print(f"{len(idx.docs)} passages.\n")
    print("=" * 74)
    print("  1-%d  accept THAT passage's key        e  type your own key" % args.show)
    print("  n    none of these answers it — record a must-refuse case")
    print("  s    skip for now                     q  stop (all saved)")
    print("=" * 74)
    print("Read the question, then read the keys. If none of them would answer\n"
          "the question for a parent, the answer is n — that is a result, not a\n"
          "failure, and you need five of them.")

    queue = [(q, c) for q, c in SEED if q.lower() not in done]
    added = 0

    for q, cat in queue:
        hits = idx.top(q, args.show)
        print(f"\n{'-'*74}\n{q}   [{cat}]")

        options = []
        for n, (src, passage, score) in enumerate(hits, 1):
            key = propose_key(q, passage)
            options.append((src, key))
            print(f"\n  [{n}] {src}")
            print(f"      {passage[:260]}{'...' if len(passage) > 260 else ''}")
            print(f"      key: {key!r}" if key else "      key: (none found)")

        choice = ask(f"\n  [1-{len(options)}/e/n/s/q] ")
        if choice == "q":
            break
        if choice == "s":
            continue

        key, doc = "", ""
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            doc, key = options[int(choice) - 1]
        elif choice == "e":
            key = ask("  key (copy it exactly from a passage above): ", lower=False)
            doc = options[0][0] if options else ""

        if key:
            row = {"qid": f"q{n_existing + added + 1:02d}", "category": cat,
                   "question": q, "expect": "answerable", "answer": key,
                   "keys": [key], "document": doc,
                   "note": "key proposed by text search, chosen by hand"}
        else:
            row = {"qid": f"q{n_existing + added + 1:02d}", "category": cat,
                   "question": q, "expect": "refuse", "answer": "", "keys": [],
                   "document": "",
                   "note": "no passage in the four handbooks answers this"}

        OUT.parent.mkdir(exist_ok=True)
        with open(OUT, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        added += 1
        print(f"  saved {row['qid']} ({row['expect']}).")

    total = n_existing + added
    print(f"\n{added} added · {total} questions in {OUT}")
    if total >= 12:
        print("Run:  python retrieval_eval.py")
    else:
        print(f"{12 - total} more for a usable baseline.")


if __name__ == "__main__":
    main()
