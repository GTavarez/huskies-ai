"""Week 2, weekend — two models, the same three prompts, side by side.

    python compare_models.py                    # lists what you have, then asks
    python compare_models.py --with qwen2.5:0.5b
    python compare_models.py --a llama3.2:latest --b gemma3:1b

WHY THIS EXISTS
  "The model" is not one thing. Two files that both answer questions can differ
  in size, in training data, and — the one that catches people out — in whether
  they were instruction-tuned at all.

  A BASE model is trained to continue text. Give it "What time is practice?"
  and a good base model may well produce "What time is the game? What time do
  we meet?" — it is finishing the document, and it is not malfunctioning.

  An INSTRUCT model has been further trained on request-and-response pairs, and
  wrapped in a chat template that marks who is speaking. That template is what
  turns a text continuer into something that answers you.

  Everything you build in Weeks 4-8 assumes the second kind. Load the first kind
  by accident and your retrieval system will fail in a way that looks like a
  prompting bug and is not.

FINDING A BASE MODEL TO TEST WITH
  On ollama.com, open a model's Tags page. Tags containing "text" are base
  weights; the plain tag is the instruct one. If you cannot find a base tag,
  compare two instruct models of very different sizes instead — you will see
  less about tuning, but a lot about capability, which is the other half of
  the choice you make in Week 3.

      ollama list                 what you already have
      ollama pull qwen2.5:0.5b    a small instruct model, quick to download

WHAT YOU DO WITH THE OUTPUT
  Read the answers. Fill in the three sentences in docs/week-02.md. The point
  is not the table — it is you being able to say what changed and why.

OUTPUT
  out/model_compare.md
"""
import argparse
import sys
from pathlib import Path

from config import CONFIG, client

OUT = Path("out")

PROMPTS = [
    ("a direct question",
     "What time does practice start?"),
    ("an instruction with a format rule",
     "List exactly three items a player must bring to practice. "
     "Number them 1 to 3 and write nothing else."),
    ("a half-finished sentence",
     "The registration deadline for the spring season is"),
]

SYSTEM = ("You are the assistant for a youth sports club. Answer briefly and plainly. "
          "If you do not know something specific to this club, say so rather than guessing.")


def available(cli):
    """Model ids the server will actually serve. Asking beats guessing — a tag
    mismatch is the single most common reason a call 404s."""
    try:
        return sorted(m.id for m in cli.models.list().data)
    except Exception as e:
        print(f"could not list models: {type(e).__name__}: {e}", file=sys.stderr)
        return []


def ask(cli, model, prompt, system=True):
    msgs = ([{"role": "system", "content": SYSTEM}] if system else [])
    msgs.append({"role": "user", "content": prompt})
    try:
        r = cli.chat.completions.create(
            model=model,
            messages=msgs,
            temperature=CONFIG["temperature"],
            seed=CONFIG["seed"],
            max_tokens=CONFIG["max_tokens"],
        )
        return (r.choices[0].message.content or "").strip()
    except Exception as e:
        return f"[{type(e).__name__}: {e}]"


def block(text, width=72, indent="    "):
    """Wrap for reading in a terminal. Long single-line answers are unreadable
    and you are going to be comparing these by eye."""
    import textwrap
    if not text:
        return indent + "[empty]"
    lines = []
    for para in text.split("\n"):
        lines.extend(textwrap.wrap(para, width) or [""])
    return "\n".join(indent + ln for ln in lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default=CONFIG["model"], help="first model (default: your configured one)")
    ap.add_argument("--b", help="second model")
    ap.add_argument("--with", dest="b_alias", help="alias for --b")
    args = ap.parse_args()

    cli = client()
    have = available(cli)
    if have:
        print("models this server can serve:")
        for m in have:
            print(f"  {m}")
        print()

    a = args.a
    b = args.b or args.b_alias

    if not b:
        others = [m for m in have if m != a]
        if others:
            b = others[0]
            print(f"no second model given, using {b}\n")
        else:
            print("You only have one model, so there is nothing to compare yet.\n"
                  "Pull a second one and run this again, for example:\n"
                  "    ollama pull qwen2.5:0.5b\n"
                  "    python compare_models.py --with qwen2.5:0.5b\n"
                  "Or pass one explicitly with --a and --b.")
            raise SystemExit(1)

    if have:
        for m in (a, b):
            if m not in have:
                print(f"'{m}' is not in the list above. Check the exact tag "
                      f"(ollama reports 'llama3.2:latest', not 'llama3.2').",
                      file=sys.stderr)
                raise SystemExit(1)

    print(f"A = {a}\nB = {b}\n")

    results = []
    for kind, prompt in PROMPTS:
        print("=" * 74)
        print(f"{kind.upper()}\n  {prompt}\n")
        ra = ask(cli, a, prompt)
        rb = ask(cli, b, prompt)
        results.append((kind, prompt, ra, rb))
        print(f"  A · {a}")
        print(block(ra))
        print(f"\n  B · {b}")
        print(block(rb))
        print()

    OUT.mkdir(exist_ok=True)
    path = OUT / "model_compare.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Model comparison\n\n- **A** — `{a}`\n- **B** — `{b}`\n")
        f.write(f"- temperature {CONFIG['temperature']}, seed {CONFIG['seed']}, "
                f"max_tokens {CONFIG['max_tokens']}\n- system prompt was sent to both\n\n")
        for kind, prompt, ra, rb in results:
            f.write(f"## {kind}\n\n> {prompt}\n\n**A — {a}**\n\n```\n{ra}\n```\n\n"
                    f"**B — {b}**\n\n```\n{rb}\n```\n\n")
        f.write("## What differed\n\n_Three sentences. Write them yourself._\n\n"
                "1. \n2. \n3. \n")

    print(f"wrote {path}\n")
    print("Look at the third prompt in particular. A model that ANSWERS the")
    print("half-finished sentence and a model that CONTINUES it are doing two")
    print("different jobs, and only one of them is the job you need in Week 5.")


if __name__ == "__main__":
    main()
