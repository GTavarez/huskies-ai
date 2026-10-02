# Consultant referral — this week's batch

## First: a correction to the playbook

Your playbook targets **SCORE mentors** and offers **15% commission**. SCORE's
Code of Ethics forbids exactly that. Their volunteers agree to:

> "Never accept fees, commissions, kickbacks or things of value from third
> parties when recommending products or services to a client"

and

> "Never solicit business from any SCORE client"

So a commission offer to a SCORE mentor asks them to break the agreement they
signed to volunteer. Best case they decline politely. Worst case you're the
person who tried to pay a volunteer a kickback, in a network where everyone
knows everyone.

The same logic very probably applies to **NJSBDC advisors** — federally funded
through the SBA, same conflict-of-interest posture. Treat them as no-commission
until one tells you otherwise.

**This does not kill the channel. It splits it into two.**

---

## Two tiers, two different offers

| | **Tier A — no money changes hands** | **Tier B — commission** |
| --- | --- | --- |
| who | SCORE mentors, NJSBDC advisors, university SBDCs, county economic-development offices | private consultants, CPAs, business coaches, marketing/ops freelancers |
| why they refer | it makes their client better off, which is literally their job | 15% of the project |
| your ask | "can I be a resource your clients use" | "introduce me and I'll pay you" |
| what you must never say | commission, referral fee, cut, kickback | — |

Tier A is not the consolation prize. A SCORE chapter mentors hundreds of small
businesses a year and has no commercial agenda, which makes a recommendation
from one worth more than a paid one.

---

## The offer, for both tiers

Stop leading with the commission. Lead with **a free diagnostic only you can
do**, because you have just spent two weeks doing it and have the receipts.

> I take a business's own documents — handbook, policies, FAQ, price list — and
> tell them whether an AI assistant could actually answer customer questions
> from them. Most of the time the answer is no, and the reason is never what
> anyone expects.

You have the evidence for that claim now. Four real club handbooks:

- **one of the four was completely unreadable by a machine** — the pages were
  rotated, so every extraction interleaved sentences into nonsense
- **every summary metric said that document was the healthiest of the four** —
  right number of sections, right lengths, no fragments
- of the questions a parent actually asks, a search over the whole corpus
  answered **72%**, and the best configuration reached **81%**
- and **no confidence score, in any of three retrieval methods, could tell the
  difference between "I found the answer" and "I found words that look like the
  question"**

That last one is why a business cannot safely put a chatbot on its own
documents without someone checking. **That is your product.** Not "I build AI
chatbots" — everyone says that. *"I tell you whether your documents can support
one, and I have measured four real ones."*

Thirty minutes per document, free, no obligation. It's a real gift, it costs you
almost nothing now that the pipeline exists, and it gives a consultant something
to hand a client that makes the consultant look good.

---

## This week's five

Four are real NJ organizations with public contact points. The fifth comes from
your own `consultant_prospects.csv`.

| # | who | tier | link |
| --- | --- | --- | --- |
| 1 | SCORE Northeast NJ (Hackensack) | A | score.org/nj/northeast-nj |
| 2 | SCORE Central Jersey | A | score.org/nj/central-jersey |
| 3 | NJSBDC at Rutgers Newark | A | rnsbdc.com |
| 4 | NJSBDC at William Paterson (Wayne) | A | wpunj.edu/sbdc |
| 5 | pick one private consultant from your CSV | B | — |

For the SCORE chapters, find the **chapter chair or branch manager** on the
chapter page — not an individual mentor. Chapter leadership is who decides what
resources get shared with the whole chapter, and one yes there reaches every
mentor in it.

---

## Tier A message — email

> Subject: free document check for your clients — no strings
>
> Hi [name],
>
> I'm a software engineer in New Jersey. I've spent the last two months building
> AI document assistants for small organizations, and I found something I think
> your mentors would want to know about.
>
> I tested four real organizations' handbooks. One of them was completely
> unusable by any AI tool — the pages were rotated, so every sentence came out
> scrambled — and every quality check I ran said it was the *best* of the four.
> You cannot see this problem by looking at the document. It looks perfect to a
> human.
>
> A lot of your clients are being sold AI chatbots right now. Some of their
> documents can't support one, and nobody is checking.
>
> I'll run the check free for any client you point at me — about 30 minutes,
> they get a plain-English report on whether their documents would work, and
> there's no pitch attached and nothing to buy.
>
> Worth a 15-minute call?
>
> Gisell Tavarez
> GT Digital Solutions LLC
> giselltavarez.com

**Do not mention commission, referral fees, or a cut anywhere in a Tier A
conversation — not in the email, not on the call, not later.**

## Tier A message — voicemail (20 seconds)

> Hi [name], this is Gisell Tavarez, software engineer here in New Jersey.
> I've been testing whether small organizations' documents can actually support
> an AI assistant — and I found one where the answer was no and every quality
> check said yes. I'd like to offer that check free to your clients. No cost, no
> pitch. My number is [number]. Thanks for your time.

## Tier B message — the one where money is allowed

> Hi [name],
>
> Quick one. I build AI document assistants for small businesses — the thing
> that answers "what are your hours / what's your refund policy / what do I need
> to bring" from a client's own documents.
>
> I start every engagement with a free 30-minute check on whether the documents
> can actually support one. Often they can't, and the reason is never obvious —
> I tested four real handbooks recently and one was machine-unreadable while
> every metric said it was fine.
>
> If you've got clients who'd benefit, I pay **15% of the project value, and 15%
> of any monthly retainer for as long as it runs**. You make the introduction, I
> do the work, you stay out of it.
>
> Open to a short call?

---

## Track conversations, not sends

This is the whole point of the new criterion — **10 conversations by end of
Week 8**. A send is not a conversation. Use these five states:

| state | means |
| --- | --- |
| `sent` | you contacted them. Worth nothing on its own. |
| `replied` | they wrote or called back. |
| **`conversation`** | **you talked. This is what you are counting.** |
| `intro` | they introduced you to a client. |
| `declined` | a clear no. **Also valuable — log the reason.** |

A `declined` with a reason is worth more than five `sent`. It is the only thing
that tells you whether the offer is wrong or just unheard.

Run `python referral_tracker.py` to add and count them.

---

## Why this beats what you were doing

| | cold email to clubs | this |
| --- | --- | --- |
| sends needed per client | ~200-300 | one yes from a chapter chair reaches every mentor in the chapter |
| what you lead with | "I build AI assistants" | a measurement nobody else has |
| trust at first contact | zero | borrowed from the person introducing you |
| cost to them of saying yes | they take a risk on a stranger | none — you are giving their client something free |
