"""Patient access audit — what actually happens when someone tries to book.

    python access_audit.py                    # run one, writes the one-pager
    python access_audit.py --blank            # print the field sheet to fill by hand

TWENTY MINUTES, FOUR CHECKS
  1. Call as a new patient during business hours
  2. Try to book online from the homepage, on a phone
  3. Call after hours
  4. Note whether anything confirms

THE RULE THAT MAKES THIS WORTH SENDING
  Report what happened. Do not report what it costs them.

  You cannot know their no-show rate, their slot value, or their call volume, and
  a practice manager who does know will stop reading the moment you invent one.
  Industry benchmarks go in a clearly separate section, labelled as benchmarks,
  with their source — never multiplied against a guess to produce a
  dollar figure that looks like a measurement.

  This is the same discipline as the retrieval eval: a number that cannot carry
  the weight put on it is worse than no number, because it looks like evidence.

TONE
  This is a gift, not an audit finding. The practice manager did not build the
  phone system and is probably the person most frustrated by it. Neutral verbs,
  no adjectives, no advice until they ask.

OUTPUT
  out/audit-<practice>.md
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

FIELD_SHEET = """
PATIENT ACCESS AUDIT — field sheet
practice: ____________________  date: __________  who called: ____________

1. PHONE, BUSINESS HOURS          call at a mid-morning or mid-afternoon time
   time of call                   ______
   rings before pickup            ______
   seconds to a human             ______      (0 if straight to a person)
   hold music / queue / IVR       ______
   transfers                      ______
   could you book on this call    Y / N
   next available new patient     ______ days out
   offered anything else          ______      (waitlist, online link, callback)

2. ONLINE BOOKING                 start at the homepage, on a PHONE not a laptop
   booking link on homepage       Y / N
   taps from homepage to a slot   ______
   works on mobile                Y / N
   real slots or request form     SLOTS / REQUEST
   account required first         Y / N

3. AFTER HOURS                    call after 6pm or on a weekend
   what happened                  ______________________________
   says when they will call back  Y / N

4. AFTER THE CONTACT
   confirmation received          Y / N   channel ______  within ______
   anything else                  ______________________________
"""


def ask(prompt, default=""):
    sys.stdout.write(prompt)
    sys.stdout.flush()
    line = sys.stdin.readline()
    if not line:
        return default
    return line.strip() or default


def yn(prompt):
    while True:
        v = ask(prompt).strip().lower()
        if v in ("y", "yes"):
            return True
        if v in ("n", "no"):
            return False
        if v in ("?", "", "u"):
            return None
        print("    y, n, or ? if you could not tell.")


def mark(v, yes="yes", no="no"):
    return "not checked" if v is None else (yes if v else no)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blank", action="store_true", help="print the field sheet")
    args = ap.parse_args()
    if args.blank:
        print(FIELD_SHEET)
        return

    print(__doc__.split("OUTPUT")[0].rstrip())
    print("=" * 70)
    print("Fill this in AFTER the calls, from your field sheet. Enter to skip any.")
    print("=" * 70)

    practice = ask("\npractice name: ") or "practice"
    when = ask("date of the audit [today]: ") or datetime.now().strftime("%B %-d, %Y") \
        if sys.platform != "win32" else (ask("date of the audit [today]: ")
                                         or datetime.now().strftime("%B %d, %Y"))

    print("\n1. PHONE, BUSINESS HOURS")
    t_call = ask("  time of the call: ")
    secs = ask("  seconds to reach a human (or 'never'): ")
    transfers = ask("  transfers: ")
    booked = yn("  could you book on that call? [y/n/?] ")
    nextavail = ask("  next available new-patient appointment, in days: ")
    offered = ask("  anything else offered (waitlist, link, callback): ")

    print("\n2. ONLINE BOOKING, ON A PHONE")
    haslink = yn("  booking link on the homepage? [y/n/?] ")
    taps = ask("  taps from homepage to a bookable slot: ")
    mobile = yn("  usable on a phone? [y/n/?] ")
    realslots = yn("  real slots, not a request form? [y/n/?] ")
    account = yn("  account required before booking? [y/n/?] ")

    print("\n3. AFTER HOURS")
    after = ask("  what happened: ")
    callback = yn("  did it say when someone would call back? [y/n/?] ")

    print("\n4. AFTER")
    confirmed = yn("  confirmation received? [y/n/?] ")
    channel = ask("  by what channel, how fast: ")

    out = Path("out") / f"audit-{practice.lower().replace(' ', '-')}.md"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# Patient access snapshot — {practice}\n\n")
        f.write(f"_What happened when someone tried to book an appointment, "
                f"{when}. Observations only — I have no access to your "
                f"schedule, your call volume or your no-show rate, so there are "
                f"no estimates here about what any of it costs._\n\n")

        f.write("## What happened\n\n| | |\n|---|---|\n")
        f.write(f"| Called at | {t_call or '—'} |\n")
        f.write(f"| Time to reach a person | {secs or '—'} seconds |\n")
        if transfers:
            f.write(f"| Transfers | {transfers} |\n")
        f.write(f"| Booked on that call | {mark(booked)} |\n")
        if nextavail:
            f.write(f"| Next available new patient | {nextavail} days out |\n")
        if offered:
            f.write(f"| Also offered | {offered} |\n")
        f.write(f"| Booking link on the homepage | {mark(haslink)} |\n")
        if taps:
            f.write(f"| Taps from homepage to a slot | {taps} |\n")
        f.write(f"| Usable on a phone | {mark(mobile)} |\n")
        f.write(f"| Real slots vs request form | "
                f"{mark(realslots, 'real slots', 'request form')} |\n")
        f.write(f"| Account required first | {mark(account)} |\n")
        f.write(f"| After hours | {after or '—'} |\n")
        f.write(f"| Said when they would call back | {mark(callback)} |\n")
        f.write(f"| Confirmation | {mark(confirmed)}"
                f"{' — ' + channel if channel else ''} |\n")

        f.write("\n## For context — not your numbers\n\n"
                "These are industry figures, not measurements of this practice. "
                "I include them so the observations above have a scale, not to "
                "estimate anything about your revenue.\n\n"
                "- MGMA polled 236 practice leaders in December 2025 on their top "
                "priority for 2026: **no-shows 27%, online scheduling 24%, phone "
                "access 22%, wait times 21%**.\n"
                "- **71% of medical groups** have fewer than one in four patients "
                "booking through a digital tool.\n"
                "- No-shows are estimated to consume around **14% of a medical "
                "group's revenue on a given day**.\n\n"
                "Source: MGMA Stat, *Patient access priorities for 2026*.\n")

        f.write("\n## What I would look at next\n\n"
                "_Only if you want it — happy to leave it here._\n\n"
                "1. \n2. \n3. \n")

        f.write(f"\n---\n\nGisell Tavarez · GT Digital Solutions LLC · "
                f"licensed paramedic · giselltavarez.com\n")

    print(f"\nwrote {out}")
    print("\nBefore you send it:")
    print("  - read it once for adjectives and delete them. 'Slow', 'confusing'")
    print("    and 'outdated' turn a gift into a complaint.")
    print("  - leave 'what I would look at next' to three items, max, and make")
    print("    the cheapest one first.")
    print("  - the person receiving this did not build the phone system and is")
    print("    probably the one most annoyed by it. Write to an ally.")


if __name__ == "__main__":
    main()
