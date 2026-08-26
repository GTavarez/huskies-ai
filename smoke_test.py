"""Week 1, Weekday B — the smoke test.

Proves four things at once: your key works, your model answers, you can read
token counts, and temperature does what you think it does.

    python smoke_test.py
"""
import json
from pathlib import Path
from config import CONFIG, client, stamp

PROMPT = "In two sentences, explain what a youth sports club registration form is for."


def ask(cli, temperature):
    kwargs = dict(
        model=CONFIG["model"],
        messages=[{"role": "user", "content": PROMPT}],
        temperature=temperature,
        max_tokens=CONFIG["max_tokens"],
    )
    resp = cli.chat.completions.create(**kwargs)
    u = resp.usage
    return {
        "temperature": temperature,
        "text": resp.choices[0].message.content.strip(),
        "prompt_tokens": getattr(u, "prompt_tokens", None),
        "completion_tokens": getattr(u, "completion_tokens", None),
        "total_tokens": getattr(u, "total_tokens", None),
    }


def main():
    cli = client()
    runs = []
    print(f"model: {CONFIG['model']}  via  {CONFIG['base_url']}\n")

    for temp in (0.0, 0.0, 1.0):
        r = ask(cli, temp)
        runs.append(r)
        print(f"--- temperature {temp} ---")
        print(r["text"])
        print(f"[prompt {r['prompt_tokens']} | completion {r['completion_tokens']} "
              f"| total {r['total_tokens']} tokens]\n")

    same = runs[0]["text"] == runs[1]["text"]
    print(f"Two runs at temperature 0 produced {'IDENTICAL' if same else 'DIFFERENT'} text.")
    print("At temperature 0 most providers are near-deterministic but not guaranteed;")
    print("note which yours is, because it sets how much run-to-run noise your")
    print("Week 5 measurements will carry.\n")

    out = Path("out/smoke_test.json")
    out.write_text(json.dumps({"config": stamp(), "prompt": PROMPT, "runs": runs}, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
