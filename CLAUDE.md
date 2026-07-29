# Sales Prospecting Workspace

This repo powers a corporate-partnerships prospecting workflow for Tyler Baity
(Senior Manager, Business Development & Operations at **Finley Golf Club —
Home of Carolina Golf**, Chapel Hill NC). He sells **corporate partnerships**:
marketing real estate (signage/branding), rounds of golf, golf outings, event
tickets, merch credit, and hosted events.

## How the user works with this repo

The user gives **any one or more** of: city, state, industry, company, person
— a single input alone is a complete request. **Coverage now expands in rings:
North Carolina (home) → Southeast → East Coast → nationwide.** Home base /
default market is the Triangle (Chapel Hill), and prospecting stays
home-weighted, but autopilot rotates outward through those rings — leading with
companies that have an NC/Triangle presence (HQ, office, or plausible travel
tie) so the Carolina-hospitality pitch still lands (see `config/autopilot.md`).
Run the `/prospect` skill (`.claude/skills/prospect/SKILL.md`) with those
inputs. It pulls companies/contacts from ZoomInfo, researches ad/marketing
spend on the web, scores prospects A/B/C, appends them to the master tracker,
republishes the tracker to Google Sheets, and creates one personalized Gmail
draft per decision-maker contact.

**Autopilot:** running `/prospect` with **no input** (or `auto`) makes it
choose its own targets via `config/autopilot.md` (dedupe + rotate + double
down on segments that are replying) and log the reasoning to
`tracker/autopilot-log.md`. Email voice is tuned in `config/voice.md`.
Weekly rhythm via scheduled Routines: **Mon/Wed/Fri = new prospecting**
(autopilot), **Tue/Thu = follow-ups** to non-repliers (`config/followups.md`).

## Key files

| File | Purpose |
|------|---------|
| `.claude/skills/prospect/SKILL.md` | The end-to-end prospecting pipeline |
| `config/profile.md` | Seller identity + offer details used in every email |
| `scoring.md` | A/B/C ranking rubric (even blend: spend / size / fit) |
| `templates/*.md` | Catered outreach email templates per industry |
| `tools/analyze_inbox.py` | Classifies everything that came back from a send — bounces, departures, out-of-offices, real replies — and reports deliverability by domain |
| `tracker/prospects.csv` | Master prospect data — source of truth for the Google Sheet |
| `dashboard/index.html` | Self-contained prospect dashboard (the shareable UI) — regenerated each run, republished to a fixed Artifact URL |

## Rules

- **Tracker is append-only source of truth.** Never drop existing rows when
  adding a batch. One row per contact.
- **ONE permanent Google Sheet.** "Finley Golf Club — Sales Tracker" pulls
  `tracker/prospects.csv` live from GitHub raw (IMPORTDATA). Updating the
  tracker = append to CSV + push. Never create new sheets per run. The sheet
  originates from `tools/build_live_tracker_xlsx.py` (see the /prospect
  skill, Step 6, for when to rebuild).
- **Gmail drafts only, never send.** The user reviews and sends everything.
- **Never ask for raffle or in-kind donations** (Tyler, 2026-07-28). Finley sells
  partnerships. This bans the *ask*, not the account — a company that offered
  gift cards is still a prospect, pitch them a partnership sized to their
  budget. See `config/voice.md`.
- **Respect the ruled-out list.** Companies Tyler has explicitly declined sit at
  `Not Interested: 0%` with "ruled out by Tyler" in Next Step. Never re-draft
  them, and never let a later `New` row resurrect one.
- **Proofread every email before creating its draft** — no unfilled merge
  fields, correct name/company/city, factually true hook, clean grammar, and
  the verbatim signature (SKILL.md Step 7).
- **Pipeline stages live in the Status column.** New prospects are `New`.
  `Re-approach: 25%` marks a prior no that was budget/timing/fit — legitimately
  re-contactable now that packages are fully customizable. `Not Interested: 0%`
  is permanent: never re-target those.
  Sync inbox replies (SKILL.md Step 0) into stages: any real reply →
  `Interested: 50%`; explicit no → `Not Interested: 0%`; advance to
  `Red-Hots: 75%` / `Agreements: 90%` / `Signed: 100%` only when the reply
  clearly warrants it. Stage colors are defined in
  `tools/build_live_tracker_xlsx.py`.
- **`Potential Revenue` is the user's column** — never overwrite it; only fill
  it from a concrete number the prospect gives.
- **The local employee often IS the decision-maker.** At a multi-site company
  the person who can say yes to an outing is usually the one running the local
  site, not the corporate CxO in another state — branch/store/office/site
  managers, GMs, territory/district/regional managers, market leaders, and
  local events/community staff all carry discretionary entertainment budget.
  So when a company is HQ'd out of state, filter ZoomInfo to
  `locationSearchType: Person` + the target state and work the people actually
  based here. **Proximity outranks seniority**: a Raleigh branch manager beats
  a Phoenix CEO, because drive-time is the product. Pull both when available,
  but lead the outreach with the local name. Do not filter these people out for
  being below Director — a "Special Events Planner" books outings.
- **Reach every useful contact, not just decision-makers.** Pull anyone who
  could buy, influence, or champion a partnership at any level — marketing/
  brand/creative, events, sponsorship/partnerships, community/PR, sales/BD,
  plus owners and C/VP/GM/President. Skip only clearly irrelevant back-office
  roles (IT, HR, accounting, engineering, legal, logistics) unless they're the
  owner/GM. One row per contact.
- Commit tracker updates to this repo after every run so nothing is lost when
  the session container is reclaimed.
