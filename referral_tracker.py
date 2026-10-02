"""Referral partners — count conversations, not sends.

    python referral_tracker.py                 # add one, then show the board
    python referral_tracker.py --board         # just the board
    python referral_tracker.py --due           # who needs a follow-up today

WHY THIS EXISTS INSTEAD OF A COLUMN IN THE CSV
  28 cold emails produced 0 replies, and for five weeks the number that got
  looked at was "emails sent". Sends are the one quantity in outreach that is
  entirely under your control, which is exactly why counting them feels
  productive and tells you nothing.

  The criterion is 10 CONVERSATIONS by end of Week 8. A conversation is a call
  or a real exchange with a human. This tool will not let a `sent` count toward
  it, because the whole failure mode of the last five weeks was a metric that
  moved whether or not anything happened.

A DECLINE IS A RESULT
  `declined` with a reason is worth more than five `sent`. It is the only thing
  that distinguishes "the offer is wrong" from "nobody saw it", and those have
  opposite fixes. The tool asks for the reason and will not take an empty one.

OUTPUT
  data/referral_partners.csv
"""
import argparse
import csv
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

OUT = Path("data/referral_partners.csv")
FIELDS = ["name", "org", "tier", "state", "channel", "first_contact",
          "last_touch", "next_touch", "notes"]

STATES = {
    "sent":         "contacted. Counts for nothing on its own.",
    "replied":      "they wrote or called back.",
    "conversation": "you actually talked. THIS is what the criterion counts.",
    "intro":        "they introduced you to a client.",
    "declined":     "a clear no — log why.",
}
GOAL = 10


def ask(prompt, lower=False):
    sys.stdout.write(prompt)
    sys.stdout.flush()
    line = sys.stdin.readline()
    if not line:
        return ""
    line = line.strip()
    return line.lower() if lower else line


def load():
    if not OUT.exists():
        return []
    with open(OUT, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(rows):
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def board(rows):
    counts = Counter(r["state"] for r in rows)
    talked = counts["conversation"] + counts["intro"]

    print(f"\n{'=' * 58}")
    bar = "#" * talked + "." * max(GOAL - talked, 0)
    print(f"  conversations  {talked}/{GOAL}   [{bar}]")
    print(f"{'=' * 58}")
    for s, blurb in STATES.items():
        print(f"  {s:<14} {counts[s]:>3}   {blurb}")

    if counts["declined"]:
        print("\n  why they said no —")
        for r in rows:
            if r["state"] == "declined" and r["notes"]:
                print(f"    {r['org'][:24]:<24} {r['notes'][:44]}")

    if talked >= GOAL:
        print("\n  Criterion met. Now the question is whether any of those ten")
        print("  produced an introduction — if none did, the offer is the problem,")
        print("  not the channel, and that is worth knowing.")
    elif counts["sent"] >= 15 and talked == 0:
        print("\n  15+ contacted and nobody has talked to you. That is a signal")
        print("  about the OPENING, not about volume. Change the first sentence")
        print("  before sending more.")


def due(rows):
    today = date.today().isoformat()
    waiting = [r for r in rows
               if r["state"] in ("sent", "replied", "conversation")
               and r["next_touch"] and r["next_touch"] <= today]
    if not waiting:
        print("\nnothing due today.")
        return
    print(f"\n{len(waiting)} due —")
    for r in sorted(waiting, key=lambda r: r["next_touch"]):
        print(f"  {r['next_touch']}  {r['state']:<13} {r['org'][:26]:<26} "
              f"{r['name'][:18]:<18} {r['notes'][:30]}")


def add(rows):
    print("\nnew touch (empty org to stop)")
    while True:
        org = ask("  org: ")
        if not org:
            break
        existing = next((r for r in rows if r["org"].lower() == org.lower()), None)
        if existing:
            print(f"    known — currently '{existing['state']}', "
                  f"first contacted {existing['first_contact']}")

        name = ask("  person: ") or (existing["name"] if existing else "")
        tier = ""
        while tier not in ("a", "b"):
            tier = ask("  tier [a = no money ever / b = commission ok]: ", lower=True)

        print("  state:", " · ".join(STATES))
        state = ""
        while state not in STATES:
            state = ask("  > ", lower=True)

        if state == "declined":
            note = ""
            while len(note) < 8:
                note = ask("  why did they say no? (a sentence) ")
                if len(note) < 8:
                    print("    The reason is the only part of a decline worth "
                          "keeping. Write it.")
        else:
            note = ask("  notes: ")

        channel = ask("  channel [email/linkedin/phone/inperson]: ", lower=True)
        today = date.today().isoformat()
        nxt = ""
        if state in ("sent", "replied", "conversation"):
            days = ask("  follow up in how many days? [4] ") or "4"
            try:
                nxt = (datetime.now() + timedelta(days=int(days))).date().isoformat()
            except ValueError:
                nxt = (datetime.now() + timedelta(days=4)).date().isoformat()

        if existing:
            existing.update(state=state, last_touch=today, next_touch=nxt,
                            notes=note or existing["notes"], channel=channel or
                            existing["channel"], name=name, tier=tier)
        else:
            rows.append({"name": name, "org": org, "tier": tier, "state": state,
                         "channel": channel, "first_contact": today,
                         "last_touch": today, "next_touch": nxt, "notes": note})
        save(rows)
        print(f"  saved. {org} -> {state}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", action="store_true")
    ap.add_argument("--due", action="store_true")
    args = ap.parse_args()

    rows = load()
    if args.due:
        due(rows)
    elif args.board:
        board(rows)
    else:
        add(rows)
        board(rows)
        due(rows)


if __name__ == "__main__":
    main()
