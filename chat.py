"""Week 2, Weekday B — a chat loop that remembers.

    python chat.py

Three things to understand here, and the middle one is the whole point:

  1. STREAMING. Tokens print as they arrive instead of after a long pause.
  2. HISTORY. "Memory" in a chatbot is not a feature of the model. It is a
     list you keep and resend every turn. The model is stateless; you are
     the one doing the remembering.
  3. A BUDGET. That list grows forever, and you pay for all of it on every
     turn. Eventually it exceeds the context window and the call fails.

WHAT YOU WRITE
  main() TODO 1     append the user's message and the reply to history
  trim()  TODO 2    drop old turns when history gets too expensive

WHAT IS GIVEN
  stream_reply()    the streaming call
  count_tokens()    a rough token count
  the loop, input handling, and /commands

Type /quit to exit, /history to see what is being sent, /tokens for the count.
"""
import sys

from config import CONFIG, client

SYSTEM = (
    "You are the assistant for a youth sports club. Answer briefly and plainly. "
    "If you do not know something specific to this club, say so rather than guessing."
)

# Keep history under this many tokens. Small on purpose so you can watch trimming
# happen after a few turns rather than after a hundred.
BUDGET = 600


# --------------------------------------------------------------- GIVEN
def count_tokens(messages):
    """Rough token count for a message list. Approximate for non-OpenAI models,
    but consistent, which is what matters for a budget."""
    text = "".join(m["content"] for m in messages)
    try:
        import tiktoken
        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        return len(text) // 4      # fallback: ~4 characters per token


def stream_reply(cli, messages):
    """Send the messages, print the reply as it arrives, return the full text."""
    parts = []
    stream = cli.chat.completions.create(
        model=CONFIG["model"],
        messages=messages,
        temperature=CONFIG["temperature"],
        max_tokens=CONFIG["max_tokens"],
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        piece = chunk.choices[0].delta.content
        if piece:
            print(piece, end="", flush=True)
            parts.append(piece)
    print()
    return "".join(parts)


# --------------------------------------------------------------- YOURS
def trim(messages, budget):
    """TODO 2 — drop the oldest turns until the history fits the budget.

    messages looks like:
        [ {"role": "system",    ...},   <- ALWAYS keep this one, it sets behavior
          {"role": "user",      ...},   <- oldest turn
          {"role": "assistant", ...},
          {"role": "user",      ...},   <- newest turn
          {"role": "assistant", ...} ]

    While count_tokens(messages) is over budget and there is more than just the
    system message plus one exchange left, remove the two messages right after
    the system message — one user turn and its reply — and check again.

    Removing from a list:
        messages.pop(1)     removes the item at position 1 and shifts the rest down

    Return the trimmed list. Returning it unchanged is a valid first version;
    get the loop working, then come back and make this real.
    """
    while count_tokens(messages) > budget and len(messages) > 3:
        messages.pop(1)
        messages.pop(1)
            
    return messages


def main():
    cli = client()
    messages = [{"role": "system", "content": SYSTEM}]

    print(f"model: {CONFIG['model']}   budget: {BUDGET} tokens")
    print("/quit  /history  /tokens\n")

    while True:
        try:
            user = input("you: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user:
            continue
        if user == "/quit":
            break
        if user == "/tokens":
            print(f"     history is {count_tokens(messages)} tokens "
                  f"across {len(messages)} messages\n")
            continue
        if user == "/history":
            for m in messages:
                print(f"     [{m['role']:<9}] {m['content'][:70]}")
            print()
            continue

        # ---------------- TODO 1 ----------------
        # a) add the user's message to history before sending
        messages.append({"role": "user", "content": user})
        # b) call stream_reply(cli, messages) and keep what it returns
        print("bot: ", end="", flush=True)
        reply = stream_reply(cli, messages)
        # c) add the reply to history as {"role": "assistant", ...}
        messages.append({"role": "assistant", "content": reply})
        print()
        # Miss (a) and the model never sees the question.
        # Miss (c) and it forgets every answer it gave — try it once on purpose,
        # ask a follow-up question, and watch what happens.

       
        messages = trim(messages, BUDGET)

        
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n{type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
    