# Scheduled Routines

Three Routines drive the week. All are created and **currently disabled** —
see the blocker below before enabling.

| Routine | Cron (UTC) | Local (ET) | Trigger ID |
|---|---|---|---|
| Refresh dashboard | `0 11-23 * * 1-5` | hourly, 7am–7pm weekdays | `trig_01Dgemdpn6S9hEDWUmg4iq4x` |
| New prospecting | `30 11 * * 1,3,5` | Mon/Wed/Fri 7:30am | `trig_01GKWNfDkCGQXsiUcZHK64Hb` |
| Follow-ups | `30 11 * * 2,4` | Tue/Thu 7:30am | `trig_012GFozyZFxAunpaHjkihXTs` |

## Blocker: they have no connector access

Routines created through the MCP tool store no MCP connectors, so the sessions
they fire run **without Gmail or ZoomInfo**. Passing `connectors` explicitly
returns *"the connectors parameter is not available for this organization."*

Every one of these jobs needs Gmail. Left enabled, the hourly refresh would
fail thirteen times a day and the dashboard would go stale while appearing
scheduled — worse than having no Routine, because the failure is silent.

So all three are **disabled**. To turn them on, open the Routine in the
claude.ai Routines UI, grant it Gmail (and ZoomInfo for the prospecting one),
and enable. The cron and the prompt are already correct; only the connector
grant is missing.

## Cron is UTC, and that matters twice a year

`30 11` is 7:30am **EDT**. When the US drops to EST in November it becomes
6:30am. To hold 7:30am year-round, change the hour to `12` at the DST
changeover — or accept the drift and leave it.

## Why the schedule is shaped this way

**Refresh runs hourly, not continuously.** One hour is the shortest interval
the scheduler allows, and it is plenty: the thing being watched is inbound
email, which does not arrive faster than a person can act on it. Confining it
to 7am–7pm weekdays keeps it from burning runs overnight when nothing changes.

**Opening week is outreach-only** (Tyler, 2026-07-29). The first new week of
reaching out is Wed 29 – Fri 31 July, and he wants all of it spent on new
outreach rather than chasing a book that has only just gone out. Rather than
build a second set of Routines for one week, the Tue/Thu follow-up prompt opens
with a date check: **on 2026-07-30 it runs new prospecting instead.** From
Tue 4 August it behaves normally. Friday 31 July needs no special case — it is
already a prospecting day.

That date check is deliberately written as a literal date, not "if this is the
first week". A relative rule would silently keep firing forever; a literal one
expires by itself.

## What the Routines will not do

- **Never send.** Every job creates Gmail drafts only. Tyler sends.
- **Never move a pipeline stage automatically.** `sync_activity.py --apply`
  writes only mechanical facts — that a message was sent, that an address is
  dead. Whether a reply means "interested" is a judgement call, and getting it
  wrong is expensive (see the Blackwood note in `scoring.md`).
- **Never touch the Bass Classic book** while it is on hold.
- **Never draft to a `DEAD-EMAIL` address** or to a domain the Deliverability
  panel shows as a server block.

## Republishing is part of the job

Committing without republishing leaves the live artifact stale. Every Routine
ends by republishing to
`https://claude.ai/code/artifact/a51a1c17-df10-4262-be18-b76193f6fece`
with favicon ⛳. This was missed by hand once and the dashboard sat a day
behind while looking current.
