---
name: prospect
description: End-to-end sales prospecting pipeline. Give it any combination of city, state, industry, company, or person — it pulls companies and decision-maker contacts from ZoomInfo, researches ad/marketing spend on the web, ranks prospects A/B/C, updates the master tracker + Google Sheet, and creates a personalized Gmail draft per contact.
---

# /prospect — Corporate Partnerships Prospecting Pipeline

Inputs: **city, state, industry, company, person** — any combination, in any
order, and **a single one alone is enough**. "Charlotte", "dentists",
"North Carolina", "Acme Motors", or "Jane Smith" are each a valid full
request. **Coverage expands in rings — NC (home) → Southeast → East Coast →
nationwide** — home base is the Triangle (Chapel Hill). Stay home-weighted, and
on the outer rings prefer companies with a **Carolinas tie** (HQ, office,
alumni leadership, or a travel/Stay-&-Play reason) so the Carolina-Golf pitch
still lands. Fill sensible defaults for whatever is missing rather than asking:
- Industry only → sweep that industry, NC-first but allowed to reach outward.
- City/state/region only → sweep the core industries there (home services,
  healthcare, auto, legal/financial), a few top companies each. Honor whatever
  geography is named — "Atlanta", "Southeast", "nationwide" are all valid.
- `North Carolina` / no city → rotate NC metros per `config/autopilot.md`.
- `Southeast` / `East Coast` / `nationwide` → run the corresponding ring in
  `config/autopilot.md`, leading with Carolinas-tied companies.
- Person only → person lookup by name; ask for the company only if the name
  is too ambiguous to resolve.

Decide the mode:
- **Market sweep** — city/state and/or industry given, no specific company →
  find the best target companies in that market.
- **Account dive** — a company named → research that company + its decision makers.
- **Person lookup** — a person named → find/enrich that contact and their company.

Read `config/profile.md`, `scoring.md`, and the relevant `templates/*.md`
before drafting anything. Use the email signature from `config/profile.md`
verbatim (it includes the scheduling link).

## Autopilot mode (no input given)

If invoked with **no** city/industry/company/person (or the literal input
`auto`), **do not ask** for keywords. Pick the next targets yourself using
`config/autopilot.md`: dedupe against `tracker/prospects.csv`, choose 2
segments (industry × Triangle sub-market), append your choice + one-line
rationale to `tracker/autopilot-log.md`, then run Steps 0–8 for those
segments. This is what the scheduled Routine fires 2–3×/week.

## Follow-up mode (Tuesdays & Thursdays / input `followups`)

Tue/Thu are for **follow-ups, not new prospecting.** Run Step 0 (reply-sync)
first, then follow `config/followups.md`: find contacts already emailed who
haven't replied and are due a bump, draft short follow-ups per
`config/voice.md`, record `FU#`+date in each row's Notes, update Next Step,
and stage/create drafts per the gate. Mon/Wed/Fri stay new-prospecting
(autopilot) days.

## Step 0 — Sync inbox replies into the pipeline (run first, every time)

Before prospecting, reconcile replies so the tracker reflects reality. Also
run this on its own whenever the user asks to "check replies" / "update the
pipeline."

1. `mcp__Gmail__search_threads` for replies to outreach, e.g.
   `in:inbox newer_than:60d` (and/or the template subject lines). For any
   promising thread, `mcp__Gmail__get_thread` to read the full latest message.
   Search **both** of Tyler's addresses — `twbaity@alumni.unc.edu` and the
   older `tbaity@playersnext.com`. A lot of the earlier book was worked from
   the previous address, so a thread missing from one may be sitting in the
   other. Outreach still goes out from the current address only.

2. Match the sender to a tracker row by email (Contact Email column). If the
   reply is from someone not yet in the tracker but clearly at a prospect
   company, still act on it and note it.

   ### The playersnext inbox holds TWO campaigns — only one is ours
   `tbaity@playersnext.com` was used for Finley corporate partnerships **and**
   for a separate **PLAYERSNEXT youth-sports / foundation** push. Different
   offer, different companies, different answers. A "no" to youth sports is not
   a "no" to Finley, and importing one as the other would put false rejections
   on cards and skew every number in the win/loss analysis.

   **Skip the thread** when its subject or body carries the other campaign's
   markers: `What's Next for Youth Sports`, `PLAYERSNEXT` as the offer (rather
   than just the sender's signature), "athletes and families of youth sports",
   the PLAYERSNEXT foundation, or Max Lehmann's foundation work.

   **The cleanest signal is the subject line.** The Finley campaign went out as
   **"2026 UNC Finley Golf Club | Proud Partnership"** (and close variants —
   "Proud Partnerships", "Proud Partners"). Searching that phrase isolates the
   Finley book almost perfectly. The youth-sports campaign went out as "What's
   Next for Youth Sports | PLAYERSNEXT".

   **Keep the thread** only when it is recognisably Finley: it mentions Finley
   Golf Club, Carolina Golf, rounds, an outing, Night on the Range, Old Well
   Patron, Heels Club, or club branding — **or** the counterparty is already a
   contact in `tracker/prospects.csv`.

   Seen on the youth-sports side and **not** to be imported as Finley replies:
   Vessi, Vessel Bags, Vanguard Charitable, NetJets, Red Hat, DriveShack,
   McConnell Golf, the Hurricanes Foundation, Beast Philanthropy, 2nd Swing
   Golf, Rock Bottom Golf, Herschel, Alamance-Caswell County Medical Society.
   Note this excludes those *threads*, not those *companies* — several are good
   Finley prospects in their own right (Red Hat is Triangle-HQ'd), they just
   have not been pitched Finley yet.

   When a thread genuinely covers both, take only the Finley portion and say so
   in the note.

   ### Not everything from a prospect's domain is a reply
   Tyler receives **marketing and sales email from companies he has pitched**.
   Treating one of those as a reply would move a cold company to
   `Interested: 50%` on the strength of a newsletter, corrupt the win/loss
   analysis, and put a warm-sounding task on a card that nobody ever wrote.
   So a message only counts as a reply when **both** hold:

   **(a) It is on our thread.** The message sits in the same Gmail thread as
   outreach Tyler (or a colleague) sent, or its subject is a `Re:` of ours.
   A brand-new subject line from that domain is not a reply — it is a
   coincidence of domain.

   **(b) It is a person writing to Tyler**, not a broadcast. Reject when any
   of these is true:
   - sender local-part is a role or bulk address: `no-reply`, `noreply`,
     `donotreply`, `marketing`, `newsletter`, `news`, `updates`,
     `notifications`, `info`, `hello`, `team`, `events`, `support`, `sales`
   - the message carries a `List-Unsubscribe` header, or the body contains
     "unsubscribe", "view in browser", "manage your preferences", "you are
     receiving this because"
   - Gmail filed it under `category:promotions` or `category:updates`
   - it opens with no salutation or a generic one ("Hi there", "Hello,") and
     never names Tyler or Finley
   - the body pitches *their* product — a demo, webinar, free trial, their
     pricing, a conference booth. A reply discusses **our** offer; a vendor
     email discusses theirs.

   Useful Gmail query shape for the sweep:
   `in:inbox newer_than:60d -category:promotions -category:updates -from:no-reply`

   ### Run the classifier rather than eyeballing it
   `tools/analyze_inbox.py` applies every rule in this step mechanically.
   Judging a hundred messages by eye is where mistakes get made — the Blackwood
   error came from reading one snippet and calling a whole thread. Do this:

   1. Sweep with `mcp__Gmail__search_threads`, at minimum these three queries:
      - `from:mailer-daemon OR from:postmaster OR subject:"Delivery Status
        Notification" OR subject:"Undeliverable" OR subject:"Returned mail"`
      - `subject:"Automatic reply" OR subject:"Out of Office" OR "no longer with"`
      - `in:inbox newer_than:60d -category:promotions -category:updates`
   2. Concatenate the responses into one JSON list and run
      `python3 tools/analyze_inbox.py inbox.json`.
   3. Act on its four sections. It **proposes** tracker edits and never makes
      them — apply them yourself after reading.

   It buckets every inbound message into: `bounce-hard` / `bounce-soft`,
   `departed`, `auto-ooo`, `broadcast`, `unsolicited`, `irrelevant`,
   `other-campaign`, `ours`, and `reply-{positive,negative,referral,neutral}`.
   Only the `reply-*` buckets are replies; nothing else may move a stage.

   **Three outputs matter more than the replies:**
   - **Hard bounces.** The address is dead. Every future draft to it is wasted,
     and the row will otherwise keep resurfacing in follow-up runs forever.
   - **Departure notices.** These almost always name the replacement, which is
     a *better* contact than the one that bounced — a warm "your colleague told
     me to write to you". Add the new row; don't just kill the old one.
   - **Deliverability by domain**, which separates the two systemic failures
     because they need opposite responses. `stale` ("address not found") means
     our contact data is old — re-pull the company from ZoomInfo. `blocked`
     ("access denied", "recipient address rejected") means their mail server
     refuses outside senders — the addresses may be perfectly correct and
     re-sourcing will change nothing, so switch to a phone or a referral.

   When a message is ambiguous, **leave the stage unchanged** and note
   "unclear inbound — needs a human read" rather than guessing upward. A
   missed reply costs one follow-up; a fabricated one costs credibility with
   a prospect who never wrote.
3. Read the reply and set that contact's **Status** (pipeline stage):
   - Any genuine reply that isn't a rejection → `Interested: 50%`.
   - Explicit "not interested" / "no thanks" / unsubscribe / "remove me" →
     `Not Interested: 0%`.
   - Only escalate beyond `Interested: 50%` when the content clearly warrants
     it: strong buying signals / wants a proposal → `Red-Hots: 75%`; verbal
     or written yes on terms → `Agreements: 90%`; signed deal → `Signed: 100%`.
     When unsure, stay at `Interested: 50%` and let the user advance it.
   - Auto-replies / out-of-office / bounces are **not** replies — leave the
     stage unchanged (note the bounce if the address is dead).
4. Update the row's `Next Step` and `Notes` accordingly (e.g., "Replied 7/9 —
   wants pricing; send proposal"). Leave the user-filled `Potential Revenue`
   column untouched unless the reply gives you a concrete number.
5. **Turn what they asked for into a task.** If the reply commits Tyler to
   anything — send pricing, call Tuesday, meet on the 2nd, wait for the new
   events chair — append a line to that row's `Notes` in this exact form:

   `TODO: send the Gold Partner pricing sheet`

   One `TODO:` per action, present tense, starting with a verb. The dashboard
   reads these straight off the tracker and shows them as an unticked checkbox
   on the company card, so anything a prospect asked for becomes visible work.
   **Remove a `TODO:` line once the thread shows it's done** — a later reply
   thanking Tyler for the pricing means the "send pricing" task is finished.
   That is how the checklist stays true as a conversation goes back and forth.
6. **Log a concrete number if they give one.** If the reply names a figure they
   committed to, write it into `Potential Revenue` (that column is otherwise
   Tyler's alone) and add `TODO: confirm what they bought in the dashboard`.
7. Commit + push so the Google Sheet reflects the new stages (Step 8).

The pipeline stages and their sheet colors are defined once in
`tools/build_live_tracker_xlsx.py` (`STAGES`): Interested 50% = light yellow,
Red-Hots 75% = pink, Agreements 90% = light blue, Signed 100% = light green,
Not Interested 0% = light orange. Fresh prospects stay `New` until they reply.

## Step 1 — ZoomInfo lookups (get exact filter values)

Use `mcp__ZoomInfo__lookup` first — never guess filter values:
- `metro-regions` with fuzzyMatch on the city
- `industries` with fuzzyMatch on the industry
- `states` for the state

## Step 2 — Find companies

**Market sweep:** `mcp__ZoomInfo__search_companies` with the lookup values.
Prefer `employeeRangeMin: 10`, sort by `-revenue`, pageSize 25. Unless the
user sets a count, take the **top ~10 companies** per run so drafts stay
high quality.

**Account dive:** `search_companies` by companyName (+ state) to get the
ZoomInfo company ID.

Then `mcp__ZoomInfo__enrich_companies` (batches of ≤10) with requiredFields
including: `name, website, revenue, employeeCount, primaryIndustry, city,
state, departmentBudgets, employeeCountByDepartment, businessModel,
foundedYear, locationCount`. The **marketing department budget** from
`departmentBudgets` is a core ranking signal.
Optionally `mcp__ZoomInfo__enrich_company_signals` (INTENT/NEWS/SCOOP) on the
top candidates for hooks and spend signals.

## Step 3 — Pull decision-maker contacts

`mcp__ZoomInfo__search_contacts` per company (companyId filter), sorted by
`-contactAccuracyScore`, `requiredFields: "email"`. **Cast wide — reach every
useful contact, not just top brass.** Pull people at ANY level whose role
could buy, influence, or champion a partnership:
- Marketing, brand, creative, digital
- Events, sponsorship, partnerships, community, PR / communications
- Sales leadership and business development
- **Local site leadership** — branch / store / office / site / plant managers,
  General Managers, territory / district / regional managers, market leaders
- Owners, founders, and C-level / VP / GM / President

Search these via `department`/`jobFunction` (e.g. Marketing, Sales) and
`jobTitle` (e.g. `"Marketing OR Brand OR Events OR Sponsorship OR Partnerships
OR Community OR Communications OR Sales OR Owner OR President OR General
Manager OR Branch Manager OR Store Manager OR Territory Manager OR District
Manager OR Regional Manager"`). Include managers and individual contributors,
not only Director+.

### Location filter — find the person who can actually say yes
Drive-time is the product, so the buyer is usually whoever runs the local site,
not the corporate CxO in another state. Whenever a company is HQ'd outside the
target market, re-run the search with:

```
locationSearchType: "Person",  state: "North Carolina"
```

(`PersonOrHQ` and the default both let out-of-state HQ staff flood the results;
`Person` returns only people actually based in the state.) This is what surfaces
the Raleigh branch manager instead of the Phoenix CEO, and it works even at huge
employers — a 43,000-person manufacturer will still return a handful of NC names.

Rules of thumb:
- **Proximity outranks seniority.** Between a local manager and a more senior
  out-of-state exec, lead outreach with the local one and treat the exec as a
  secondary/parallel touch.
- **Don't cut people for being below Director.** Local budget holders are often
  Manager or Non-Manager level — a "Special Events Planner" or "Program Manager,
  Culture & Events" is exactly who books an outing.
- If the state filter returns nothing, the company has no local presence: fall
  back to national marketing/sponsorship roles and pitch brand exposure rather
  than hospitality (see the tier-4–6 note in `config/autopilot.md`).

**Go deep — map the buying committee, not one contact.** Aim for the fullest
useful set per company (at a big employer that's often 5–12 people across the
functions above; at a small local business it may be 1–3). More names per
company is a feature: mid-level marketing/events/community people are
**champions** — an email to them often gets forwarded internally to whoever
owns partnerships, which lands warmer than a cold email straight to the CxO.
So pull the whole committee, top to mid-level.

Skip only genuinely irrelevant roles (IT, HR/recruiting, accounting/finance
back-office, engineering, legal, warehouse/logistics) **unless** that person
is the owner/GM. Priority order: marketing/events/sponsorship titles → owners/
execs → sales/BD → other useful functions.
`mcp__ZoomInfo__enrich_contacts` (batches of ≤10) for verified email, phone,
jobTitle, managementLevel.

Credit guardrail: pull everyone plausibly useful, but don't enrich obviously
irrelevant roles.

**Person lookup mode:** `search_contacts` by name (+company), then
`mcp__ZoomInfo__contact_research` for background and `enrich_contacts` for
verified contact info.

## Step 4 — Web research for ad-spend signals + hooks

For each company (WebSearch, 1–2 searches each):
- `"<Company>" <city> sponsor OR sponsorship OR advertising` — existing local
  ad/sponsorship activity (spend signal AND hook material)
- Recent news: awards, expansions, new locations, anniversaries (hooks)

Log what you find in one short phrase per company for the tracker's
"Ad Spend Signals" column.

### Step 4b — Re-score the warm book on the same news sweep
New companies get scored from scratch in Step 5. **Companies already in the
tracker go stale**, so every run also refreshes the ones that matter most.

1. Pick the re-score set (cheap — no ZoomInfo credits, just search):
   - every company at `Interested: 50%` or better, plus every `Re-approach: 25%`
   - any Rank A company not re-checked in ~30 days
   - cap it at ~15 companies per run so this stays a few minutes of work
2. For each: `mcp__ZoomInfo__enrich_news` when the company has a ZoomInfo ID
   (no credit cost for news), else one WebSearch:
   `"<Company>" news 2026 sponsorship OR expansion OR hiring OR acquisition`
3. Apply the **news adjustments table in `scoring.md`** — capped at ±12 points
   per run, only on news you actually found and can cite.
4. Write the result back into the row: new `Score`, re-banded `Rank`, a refreshed
   `Why This Rank`, and a `Notes` line in exactly this shape —
   `SCORE 68→81 2026-07-28: named title sponsor of the Durham Bulls season`
   The dashboard parses that line to show the movement and the reason on the
   card, so a rank change is never unexplained.
5. If the news changes what to sell, update the recommended package reasoning
   too (a company that just opened a Triangle office may jump from Gold to
   Premier). Never change `Potential Revenue` — that column is Tyler's.
6. **No news found = no change.** Leave the score alone and don't write a
   `SCORE` line. A stale score beats an invented one.

## Step 5 — Score and rank

Apply `scoring.md` exactly (even blend: spend 35 / size 35 / fit 30).
Record numeric score, A/B/C rank, and a one-line "Why This Rank".

## Step 6 — Update the tracker

1. Append new rows to `tracker/prospects.csv` — **one row per contact**,
   never dropping existing rows. Skip contacts already in the tracker
   (match on email). New prospects start with `Status = New` and a blank
   `Potential Revenue` (the user fills that column in). Columns are, in order:
   Date Added, Rank, Score, Company, Industry, City, State, Website, Revenue,
   Employees, Marketing Budget, Ad Spend Signals, Why This Rank, Contact Name,
   Contact Title, Contact Email, Contact Phone, ZoomInfo Company ID,
   Draft Created, **Status**, Next Step, Notes, **Potential Revenue**.
   The **Status** column doubles as the pipeline stage — see Step 0 for the
   values (`New` → `Interested: 50%` → `Red-Hots: 75%` → `Agreements: 90%` →
   `Signed: 100%`, or `Not Interested: 0%`).
2. Commit and push (Step 8). **That's all** — the user's ONE permanent
   Google Sheet ("Finley Golf Club — Sales Tracker") pulls this CSV live
   from GitHub raw via IMPORTDATA, so pushing the CSV updates the sheet
   automatically (refreshes ~hourly and on open). NEVER create a new
   Google Sheet per run.
   - The sheet was built from `tools/build_live_tracker_xlsx.py`. Only
     rebuild + re-import it if the raw CSV URL changes (branch rename/merge)
     or columns change.
   - If the tracker ever exceeds ~295 rows, bump MAX_ROWS in that script
     and rebuild so formatting covers the new rows.

## Step 6b — Refresh the dashboard UI

Regenerate `dashboard/index.html` from the full tracker (one company object
per company, contacts nested; group industries into Dental / Auto / Sports &
Outdoor for the filter) and republish the Artifact to the SAME URL by passing
`url: https://claude.ai/code/artifact/f240ef95-2416-4396-9824-ac0af39e86c2`.
It's the user's shareable, supervisor-facing view — keep the KPI strip, rank
badges, pipeline-stage/draft pills, and contact copy-buttons accurate.
Self-contained (no external calls), so it works regardless of connection state.

## Step 7 — Gmail drafts

Draft to **every useful contact** pulled at A and B companies — the full
committee, not just the top name (C-rank companies only if the user asks). The
lower/mid-level champions matter: their email should make it easy and natural
to forward internally. For a non-executive contact (marketing/events/community/
mid-level), use the **champion / forward-up variant** in `config/voice.md` —
same personalized hook, but a close that invites a hand-off (e.g. "if
partnerships sit with someone else on your team, even a quick pointer would
help"). For owners/execs, the direct ask is fine.

1. Pick the industry template from `templates/`; fall back to `generic.md`.
2. Fill merge fields. `{{Hook}}` must be a real, specific fact from Step 2/4
   research — if nothing real was found, open with a market-specific line
   instead, never a fabricated claim.
3. Keep it under 120 words and follow `config/voice.md` for tone/style.
   **No signature block** — end after the ask; Gmail appends Tyler's own
   signature automatically (see `config/voice.md`).
4. **Proofread every email before creating the draft** (drafts are what the
   user sends, so this is the last quality gate). Check each one against:
   - No unfilled merge fields left (`{{FirstName}}`, `{{Company}}`,
     `{{City}}`, `{{Hook}}` all resolved — search the body for `{{`).
   - `{{FirstName}}` is the contact's actual first name; `{{Company}}` and
     `{{City}}` match the tracker row.
   - The hook is factually true per Step 2/4 research — no invented awards,
     sponsorships, or numbers.
   - Spelling/grammar clean, tone professional, under 120 words.
   - No signature block in the body (Gmail appends Tyler's); the email ends
     cleanly on the ask, no name/title/contact typed out.
   Fix anything that fails before drafting. If a hook can't be verified,
   replace it with a market-specific line rather than shipping a guess.
5. `mcp__Gmail__create_draft` — to: the contact's verified email, subject
   per `config/voice.md` (specific-hook style, not the template's placeholder).
   **Drafts only. Never send.**
6. Mark `Draft Created = Y` in the tracker row.

If a contact has no verified email, still log them (Draft Created = N,
note "no email — phone only").

**If Gmail is unreachable** (connection errors): write the finished drafts
to `outbox/YYYY-MM-DD-<batch>-drafts.md` (To/Subject/Body per entry),
commit it, and tell the user. At the START of every run, check `outbox/`
— if files exist, create those Gmail drafts first, set Draft Created = Y
in the tracker, and delete the file. Same for tracker rows marked
"Email pending - enrich next run": enrich them and create their drafts.

## Step 8 — Commit and report

1. `git add tracker/ config/ && git commit` (message:
   `Add <n> prospects — <market/industry>`) and push the designated branch.
2. Report to the user: count by rank, the top 3 A-prospects with the "why",
   the Google Sheet link, and how many drafts are waiting in Gmail.

## Guardrails

- ZoomInfo credits are real money: batch enrichments, don't enrich companies
  that obviously won't score above C, and don't re-enrich contacts already
  in the tracker.
- Respect compliance: business contacts only, no bulk scraping, drafts are
  individually personalized (not bulk spam).
- If ZoomInfo returns nothing for a market/industry combo, widen one filter
  at a time (drop employee minimum, widen metro to state) and say so.
