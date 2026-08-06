# Scheduled Routines

## Current setup, 2026-08-05: ONE Routine, once a weekday morning

| Routine | ID | Cron (UTC) | Local | State |
|---|---|---|---|---|
| **Finley daily — sweep, tracker, drafts** | `trig_01Dgemdpn6S9hEDWUmg4iq4x` | `30 11 * * 1-5` | weekdays 7:30am ET | **live** |
| ~~Finley prospecting autopilot~~ | `trig_01UoHSH8buAT6XeLYa673zBK` | — | — | folded in, disabled |
| ~~Finley follow-ups~~ | `trig_018QSnQzvaXZksfBrieNB1ar` | — | — | folded in, disabled |
| ~~SalesFlow new prospecting / follow-ups~~ | `…64Hb` / `…ihXTs` | — | — | superseded, disabled |

**Why one:** the old shape ran **70 jobs a week** — 65 of them the hourly
dashboard refresh. On 2026-08-05 that refresh fired 7 times before noon and
committed nothing, doing a full Gmail sweep each time. Its entire week of
output was four commits, all in one night, all the same refresh. Meanwhile the
two Routines that actually make drafts ran 5 times a week and produced nothing
at all. The new shape is **5 jobs a week**, a 14x cut, and the one surviving
job does the whole pipeline.

**Why this trigger and not the other two:** `trig_01Dgemdpn6S9hEDWUmg4iq4x` is
the only trigger that has ever written to this repo (five commits, 2026-08-05
01:34–01:48Z, including two merge commits resolving concurrent runs). Six fires
of the other two produced nothing. Rather than keep debugging why, the work
moved onto the one with a proven write path. This is evidence, not certainty —
the refresh job is also much shorter, so its success may be about length rather
than the trigger. Checkpointing (below) is the hedge either way.

**Checkpoint commits are the important part.** The prompt commits and pushes
after the inbox sync, then after every 5 drafts, instead of once at the end. Six
runs have died partway and delivered nothing; a run that dies at 60% should bank
60%. A partial push is a success.

### What one morning run produces

Inbox swept, tracker updated, **50 drafts** waiting in Gmail (Mon/Wed/Fri) or
every 7-day-overdue follow-up (Tue/Thu), **12 companies' news refreshed**, and
the dashboard republished. Opening the tracker should be the only step Tyler
takes.

### The newsroom rotation, and why 12

Added 2026-08-06, after Tyler noticed the headlines never changed — the block
was a hardcoded literal nothing wrote. `tools/build_news.py --targets` picks
which companies to look up, prioritised so the ones in a live conversation are
never stale.

| Band | Companies | Covered at 12/run |
|---|---:|---|
| Live conversation | 75 | — |
| A-rank | 20 | **~1.6 weeks** for both |
| Already drafted | 65 | |
| Not yet worked | 544 | ~12 weeks for the whole book |
| Ruled out | 19 | never queried |

12 per run is 60 a week. The 95 companies that matter get re-checked well inside
the 21-day staleness window, and the long tail still moves. Raising it buys
faster coverage of band 3, which is the least valuable band — so 12 is the
right knob setting unless the live pipeline grows a lot.

A company checked with **no news** is recorded as checked. "Nothing found" is a
real answer and stops it being re-queried tomorrow.

**Deliberately not hourly.** "Drafts appearing through the day" costs 13x more
and delivers the same thing later — prospects do not arrive hourly, and a
morning batch is already a day's work waiting. If volume needs to go up, raise
the per-run draft target before adding a second run.

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

## The standard preamble

`update_trigger` can change the **prompt**, name, cron, model and enabled state.
It cannot change `outcomes`, `sources` or `mcp_connections`. So the pinned
branch cannot be unpinned from here — the prompt has to stop depending on it.

Every Routine prompt starts with this block. It assumes nothing about the
working directory or the starting branch, because both have been wrong.

    ## Preamble — run this before anything else, and do not skip it on failure.
    
    Do not assume a working directory. Find the clone:
      ls; git rev-parse --show-toplevel 2>/dev/null
    If there is no clone, call add_repo (owner twbsportsguy, repo ClaudeCode,
    access push), run the clone command it returns, then call
    register_repo_root with the clone path. Do NOT pre-check with curl or
    git ls-remote — unauthenticated checks 404 on private repos and will
    mislead you into reporting "repo not connected" when it is fine.
    
    You may start on an auto-assigned branch such as claude/cool-lovelace.
    That branch is not where the work lives. Get the real tree:
      git fetch origin claude/sales-prospecting-workflow-wcsfty
      git checkout -B work origin/claude/sales-prospecting-workflow-wcsfty
    Confirm before continuing:
      test -f tools/fetch_inbox.py && test -f config/what-works.md || \
        echo "STALE TREE — stop and report"
    Do NOT use the row count of tracker/prospects.csv as the staleness check.
    Frozen main carries 1,131 rows against the branch's 1,240, so any
    "more than 1000 rows" test passes on the stale tree and proves nothing.
    The four files added since the freeze — tools/fetch_inbox.py,
    tools/reply_features.py, config/what-works.md, tracker/email-corpus.jsonl —
    are absent from main entirely, so their presence is a real discriminator.
    
    At the end, push in this order and stop at the first that succeeds:
      1. git push origin HEAD:claude/sales-prospecting-workflow-wcsfty
      2. git push -u origin HEAD          (your assigned branch; say which)
      3. GitHub API fallback: commit the changed files with
         mcp__github__create_or_update_file against branch
         claude/sales-prospecting-workflow-wcsfty. This path does not use git
         credentials at all, so it survives a push sandbox.
    Whichever worked, say so by name. If all three failed, paste the verbatim
    error from each — that text is worth more than a summary.

**Why the API fallback matters.** Three fires on 2026-08-02 produced no commit
and no error anyone could read, because a fired session's chat reply lands in a
container nobody opens and the refresh Routine has all notifications off. Git
was the only channel and git was the thing failing. `create_or_update_file`
writes through the GitHub API instead, so a run can report its own failure even
when `git push` is what broke.

## Second smoke test, 2026-08-04: ALSO DID NOT CLEAR

Two more fires, both silent. Running total: **five fires, zero writes.**

| Fire | Trigger | What it was asked to do | Result |
|---|---|---|---|
| 4 | `[TEST]` (since deleted) | add_repo → clone → commit a self-test file | nothing |
| 5 | refresh `trig_01Dgemdpn6S9hEDWUmg4iq4x` | **git commands only** — no Gmail, no tools, no artifact | nothing |

Fire 5 is the one that matters. It ran against the fully-configured Routine —
repo in `sources`, Gmail and ZoomInfo in `mcp_connections` — and was asked for
nothing but `pwd`, `git branch`, a one-line file, and two pushes. Fifteen
minutes later: no new branch on origin, no `tracker/routine-selftest.md`, and
no commit this session did not make. So the failure is not the pipeline, not
Gmail, not ZoomInfo, and not the volume of work. **A fired session cannot get
a byte back into this repo.**

What has been ruled out, each by evidence rather than reasoning:

- *Missing repo* — `sources` carries twbsportsguy/ClaudeCode on all three.
- *Missing connectors* — `mcp_connections` carries Gmail + ZoomInfo on all three.
- *Wrong branch in the prompt* — fire 5 was told to push to `HEAD` as well, so
  it did not need to know any branch name.
- *Too much work to finish* — fire 5 had about six commands to run.

Still unknown: whether `git push` fails, or whether the session never reaches
it. Nothing distinguishes the two from here, because the only channel that
would carry the error is the one that is broken. Hence the API fallback in the
preamble above — `mcp__github__create_or_update_file` and `issue_write` use no
git credentials, so the next fire can report its own failure even if push is
what breaks. **That fallback is untested. It is the best remaining hypothesis,
not a fix.**

### The working model, meanwhile

Every draft in this book was produced by Tyler asking for a run in-session.
That is the load-bearing path and it has never failed. Treat the Routines as an
experiment running in the background until one of them writes something.

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
