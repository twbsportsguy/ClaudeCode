---
name: prospect
description: End-to-end sales prospecting pipeline. Give it any combination of city, state, industry, company, or person — it pulls companies and decision-maker contacts from ZoomInfo, researches ad/marketing spend on the web, ranks prospects A/B/C, updates the master tracker + Google Sheet, and creates a personalized Gmail draft per contact.
---

# /prospect — Corporate Partnerships Prospecting Pipeline

Inputs (any combination, in any order): **city, state, industry, company, person**.

Decide the mode:
- **Market sweep** — city/state and/or industry given, no specific company →
  find the best target companies in that market.
- **Account dive** — a company named → research that company + its decision makers.
- **Person lookup** — a person named → find/enrich that contact and their company.

Read `config/profile.md`, `scoring.md`, and the relevant `templates/*.md`
before drafting anything. If `config/profile.md` still has bracketed
placeholders, ask the user for name/title/organization ONCE and update the file.

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

`mcp__ZoomInfo__search_contacts` per company (companyId filter) with
`managementLevel: "C Level Exec,VP Level Exec,Director"`, sorted by
`-contactAccuracyScore`, `requiredFields: "email"`. Also try
`jobTitle: "Owner OR President OR General Manager OR Principal"` for small
local firms where management level tagging is thin.

Take **all decision makers found, up to 3 per company** (marketing-titled
contacts first, then owner/C-level). Never include below-Director contacts.
`mcp__ZoomInfo__enrich_contacts` (batches of ≤10) for verified email, phone,
jobTitle, managementLevel.

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

## Step 5 — Score and rank

Apply `scoring.md` exactly (even blend: spend 35 / size 35 / fit 30).
Record numeric score, A/B/C rank, and a one-line "Why This Rank".

## Step 6 — Update the tracker

1. Append new rows to `tracker/prospects.csv` — **one row per contact**,
   never dropping existing rows. Skip contacts already in the tracker
   (match on email).
2. Regenerate the Google Sheet: read the FULL csv and upload via
   `mcp__Google_Drive__create_file` with `contentMimeType: "text/csv"`,
   title `Sales Tracker (updated YYYY-MM-DD)` (converts to a Google Sheet
   automatically). Drive tools can't edit cells in place — full regeneration
   is intentional. Tell the user the previous copy is superseded and can be
   deleted, and give them the new sheet link.

## Step 7 — Gmail drafts

For every A and B ranked contact (C only if the user asks):
1. Pick the industry template from `templates/`; fall back to `generic.md`.
2. Fill merge fields. `{{Hook}}` must be a real, specific fact from Step 2/4
   research — if nothing real was found, open with a market-specific line
   instead, never a fabricated claim.
3. Keep it under 120 words, seller signature from `config/profile.md`.
4. `mcp__Gmail__create_draft` — to: the contact's verified email, subject
   from the template. **Drafts only. Never send.**
5. Mark `Draft Created = Y` in the tracker row.

If a contact has no verified email, still log them (Draft Created = N,
note "no email — phone only").

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
