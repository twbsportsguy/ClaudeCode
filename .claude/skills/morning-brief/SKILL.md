---
name: morning-brief
description: "Who should I call today" — a daily prioritized action list for Tyler. Reads the master tracker, ranks the best moves for the day (hot A-list, drafts ready to send, replies to chase, contacts to find), and prints a short brief with the specific next action per prospect. Optionally arms a recurring Routine so it lands every weekday morning.
---

# /morning-brief — "Who should I call today"

A 30-second read that tells Tyler exactly where to spend his selling time
today. It does **not** prospect or draft — it triages what's already in the
pipeline and hands back a ranked to-do list with the specific next action for
each name. Think of it as the cockpit's "needs-attention queue" in prose.

## Inputs
None required. Optional:
- A number (`/morning-brief 5`) → cap the call list at that many names.
- `arm` → after printing today's brief, offer to create the weekday Routine
  (see the bottom of this file). Don't create it silently.

## Step 1 — Load the pipeline
Read `tracker/prospects.csv` (the source of truth). For each row you need:
Company, Contact, Title, Rank, Score, Status, and whether a draft exists
(check `outbox/` and Gmail drafts via `mcp__Gmail__list_drafts` when Gmail is
up). Group rows by company; a company's Score/Rank is shared across its
contacts. Pull the Recommended Package the same way the dashboard does
(`config/packages.md` logic) so each line can name what to sell.

## Step 2 — Sync fresh replies first (fast)
Before ranking, do a light reply-sweep so the brief reflects reality: run the
reply-sync in `.claude/skills/prospect/SKILL.md` Step 0 (search Gmail threads
for prospects in the tracker). Any new real reply moves that prospect to the
top of today's list as a **"reply — respond now"** item and updates the Status
column per the CLAUDE.md stage rules. If Gmail is down, say so and skip.

## Step 3 — Build today's ranked list
Bucket every actionable prospect and order the buckets like this:

1. **Replies to chase** — anyone at `Interested: 50%` or higher, or with a new
   inbound reply. Highest priority; these are warm.
2. **Call today · A-list** — Rank A companies whose contacts already have a
   draft ready to send (draft exists but not yet sent). Action: *review & send.*
3. **Draft next** — Rank A/B companies with contacts mapped but **no** draft
   yet. Action: *draft outreach* (offer to run `/prospect` on them).
4. **Find a contact** — companies with zero contacts in the tracker. Action:
   *find the owner/GM* (name the ZoomInfo gap or the phone number to try).
5. **Follow-ups due** — non-repliers past the cadence window in
   `config/followups.md`. Action: *send follow-up.*

Within each bucket, sort by Partnership Score (desc). Respect the optional cap.

## Step 4 — Print the brief
Keep it tight and scannable — this is read on a phone with coffee. Format:

```
☀️  Morning brief — <weekday>, <date>
Pipeline: <N> companies · <N> A-list · $<opp>K in play · <N> drafts ready

🔥 Respond now (<n>)
  • <Company> — <Contact>, <Title> — <one line: what they said / why warm> → reply
▶️  Call today · drafts ready (<n>)
  • <Company> — <Contact> — <Recommended Package · price> → review & send draft
✍️  Draft next (<n>)
  • <Company> (Score <s>) — <Recommended Package> → run /prospect
📇  Find a contact (<n>)
  • <Company> (Score <s>) — no decision-maker on file → try <phone / ZoomInfo>
🔁  Follow-ups due (<n>)
  • <Company> — <Contact> — last touched <date> → follow up
```

Rules:
- Show at most 5 lines per bucket unless asked for more; append
  "…and <k> more" when truncated.
- Every line ends with a **concrete verb** (reply / send / draft / call /
  follow up) — never a vague "look into."
- If a bucket is empty, omit it. If everything's empty, say "Pipeline's clear —
  time to prospect. Want me to run autopilot?" and stop.
- Close with one suggested first move: *"Start with <top item> — <why>."*

## Step 5 — Offer the actions (don't auto-run)
After the brief, offer the natural next step in one line: e.g. "Want me to send
the 3 ready drafts, draft the 'Draft next' set, or run autopilot for fresh
names?" Wait for Tyler to pick. Sending still routes through Gmail drafts only —
never send without his go-ahead (CLAUDE.md rule).

## Arming the weekday Routine (only if asked, or on `arm`)
Offer to create a recurring Routine that fires this brief every weekday morning
(suggest **7:30 AM ET**, Mon–Fri). Use the scheduling tool available in the
session (`create_trigger` / CronCreate). Cron is **UTC** — 7:30 AM ET is
`30 11 * * 1-5` during EDT (summer) / `30 12 * * 1-5` during EST (winter);
confirm which with Tyler. The Routine's prompt should be:
"Run /morning-brief and post the brief." Bind it to this session (self-bind) so
it continues the workflow with full context. Confirm the time before creating
it, and tell Tyler he can pause it anytime.
