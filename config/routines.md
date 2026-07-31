# Scheduled Routines

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
