# Scheduled Routines

## Root cause, 2026-08-04: the outcome branch, not the repo

Two diagnoses before this one were wrong and are recorded here so nobody spends
another week on them.

**Wrong #1 — "the environment needs a repo attached."** Mine, 2026-08-04. Cloud
environments hold network policy, environment variables and setup scripts. They
do not hold repositories; repos attach per session. Adding an environment fixes
nothing. (https://code.claude.com/docs/en/claude-code-on-the-web)

**Wrong #2 — "fired sessions have no repo, because `create_trigger` has no repo
parameter."** Also mine. The tool has no such parameter, which is true and
misleading. Reading the stored config back shows all three live Routines already
carry the repo:

    sources: [{git_repository: {url: "https://github.com/twbsportsguy/ClaudeCode"}}]

**What the config actually shows.** Each Routine is pinned to an auto-generated
*outcome branch* that has never existed on the remote:

| Routine | `outcomes` branch | on origin? |
|---|---|---|
| Finley prospecting `trig_01UoHSH8buAT6XeLYa673zBK` | `claude/brave-noether` | no |
| Finley follow-ups `trig_018QSnQzvaXZksfBrieNB1ar` | `claude/optimistic-gauss` | no |
| SalesFlow refresh `trig_01Dgemdpn6S9hEDWUmg4iq4x` | `claude/cool-lovelace` | no |
| ~~superseded prospecting~~ | `claude/exciting-thompson` | no |
| ~~superseded follow-ups~~ | `claude/tender-babbage` | no |

Every prompt tells the session to check out
`claude/sales-prospecting-workflow-wcsfty`. The Routine is pinned somewhere else.
Five branches assigned, five branches that do not exist — consistent with "three
fires, zero commits" below.

## Do NOT delete and recreate these Routines

The obvious repair — recreate them correctly — destroys what works. A Routine
created by the assistant via `create_trigger` from this session comes back with:

- **no `mcp_connections`.** The tool warns: *"this trigger stores no MCP
  connectors ... Connectors on triggers created via this tool are limited to
  those the calling session itself holds; this call had none to pass through."*
  Passing `connectors` explicitly returns *"not available for this
  organization."* The Gmail + ZoomInfo grants on the three live Routines were
  added **by Tyler in the claude.ai UI on 2026-07-31** and cannot be reproduced
  from here.
- **no `sources`.** So a replacement genuinely would have no repo — the failure
  mode I wrongly attributed to the existing ones.

A replacement is therefore strictly worse than what is already there: same
branch problem, plus no Gmail, no ZoomInfo, no repo. **Repair in place with
`update_trigger`, or change it in the UI. Never delete-and-recreate.**

## Smoke-test verdict, 2026-08-02: DID NOT CLEAR

Three fired runs, **zero commits** on any branch. Connectors are attached and at
least one run reached the artifact-publish step, so this is not a permissions
problem with Gmail — it is that **work does not come back into the repo**.

| Fire | When | Instruction | Result |
|---|---|---|---|
| 1 | Fri 07-31 15:03 | full refresh | **Published the artifact** (proven by a 409 publish conflict). No commit. |
| 2 | Sun 08-02 17:10 | minimal, "reply in chat" | Nothing observable — see the design error below. |
| 3 | Sun 08-02 17:10 | minimal, "commit a report file" | No commit after 11 minutes. |

**A design error of mine on fire 2:** a fired Routine runs in a *different
container*, so a chat reply and a `/tmp` file are both invisible from here. Git
is the only channel between the two. Fire 3 corrected for that and still
produced nothing.

**Hypothesis, explicitly not a conclusion:** fired sessions may lack git push
credentials for this branch. It fits both observations — the Artifact service
worked, `git push` never landed — but nothing here proves it, and the
instruction on this test was not to guess.

### What this means for Monday

The 7:30am prospecting Routine will fire. Two outcomes are possible and they are
very different:

- **Drafts appear in Gmail but the tracker does not update.** Partially useful,
  and fully recoverable — the tracker can be reconciled from Gmail afterwards,
  which is exactly what was done by hand on 2026-07-31 (the inbox sync that
  caught the Kymera referral and two bounces).
- **Nothing appears at all.** Then the Routines are not load-bearing and the
  working model is Tyler asking for runs in-session, which has produced every
  draft in this book so far.

**Let Monday run.** It costs nothing to watch, and Gmail drafts are the outcome
that actually matters — a commit is bookkeeping that can be replayed.

### The check that is actually valid

Do **not** test "is there a commit newer than baseline X" while also committing
from this session — that produces a false pass, which nearly happened on
2026-08-02. The valid checks are:

1. Did a commit appear that **this session did not make**? (`git log` across all
   branches, compared against what you pushed.)
2. Did **new Gmail drafts** appear that nobody here created?

---

**Status as of 2026-07-31, 11:03am ET: connectors granted, three Routines live.**

| Routine | ID | Cron (UTC) | Local (ET) | State |
|---|---|---|---|---|
| Finley prospecting autopilot | `trig_01UoHSH8buAT6XeLYa673zBK` | `30 11 * * 1,3,5` | Mon/Wed/Fri 7:30am | **live** |
| Finley follow-ups | `trig_018QSnQzvaXZksfBrieNB1ar` | `30 11 * * 2,4` | Tue/Thu 7:30am | **live** |
| SalesFlow refresh dashboard | `trig_01Dgemdpn6S9hEDWUmg4iq4x` | `0 11-23 * * 1-5` | hourly, 7am–7pm weekdays | **live** |
| ~~SalesFlow new prospecting~~ | `trig_01GKWNfDkCGQXsiUcZHK64Hb` | — | — | **superseded, disabled** |
| ~~SalesFlow follow-ups~~ | `trig_012GFozyZFxAunpaHjkihXTs` | — | — | **superseded, disabled** |

All five carry Gmail and ZoomInfo now. The two superseded ones are renamed
`[SUPERSEDED — do not enable]` because they share **identical cron expressions**
with the two live ones — enabling either would fire the same job twice on the
same branch at the same minute, with two sessions pushing to one branch. They
are kept rather than deleted only so the decision stays reversible; deleting
them is safe whenever Tyler wants.

## What went wrong, and what fixed it

Two things were broken at once, which is why it looked like nothing was running.

**1. Wrong branch.** The two Routines that actually fired were created 2026-07-20
and pointed at `main`. Main is frozen at 2026-07-29 00:52 and has none of the
tracker (1,200+ rows), the reply-feature learner, `config/what-works.md`, the
email corpus or any voice rule added since. A run on 2026-07-31 at 7:33am ET
checked out that stale tree and committed nothing. **Fixed 2026-07-31:** both
now target `claude/sales-prospecting-workflow-wcsfty` and carry the current
rules, including the 12–20 draft floor and the area-code check.

**2. No connectors.** Routines created through the MCP tool store no MCP
connectors, and passing `connectors` explicitly returns *"the connectors
parameter is not available for this organization."* So the fired sessions had no
Gmail and no ZoomInfo — they could not read the inbox or pull a contact.
**Fixed 2026-07-31 by Tyler**, in the claude.ai Routines UI. Confirmed: the API
now returns an `mcp_connections` block naming ZoomInfo and Gmail on every
Routine.

The lesson worth keeping: **a Routine firing is not a Routine working.**
`last_fired_at` was updating the whole time. The only reliable check is whether
the branch got a commit.

## Verifying after any change

Do not wait until the next scheduled fire to find out. Use `fire_trigger` on the
**refresh** Routine — it is read-only, creates no drafts, and needs Gmail, so it
is the safest possible smoke test. Pass a `text` argument asking it to confirm
Gmail, ZoomInfo and the branch before doing anything else, then check the branch
for a new commit.

## Cron is UTC, and that matters twice a year

`30 11` is 7:30am **EDT**. When the US drops to EST in November it becomes
6:30am. To hold 7:30am year-round, change the hour to `12` at the changeover —
or accept the drift.

## What the Routines will not do

- **Never send.** Every job creates Gmail drafts only. Tyler sends.
- **Never move a pipeline stage automatically.** `sync_activity.py --apply`
  writes only mechanical facts — that a message was sent, that an address is
  dead. Whether a reply means "interested" is a judgement call, and a "wrong
  person" reply is neither interest nor a no.
- **Never touch the Bass Classic book** while it is on hold.
- **Never draft to a `DEAD-EMAIL` address** or a server-blocked domain.

## Republishing is part of the job

Committing without republishing leaves the live artifact stale. Every Routine
ends by republishing to
`https://claude.ai/code/artifact/a51a1c17-df10-4262-be18-b76193f6fece`
with favicon ⛳. This was missed by hand once and the dashboard sat a day behind
while looking current.
