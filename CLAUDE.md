# Sales Prospecting Workspace

This repo powers a corporate-partnerships prospecting workflow for Tyler Baity
(Senior Manager, Business Development & Operations at **Finley Golf Club —
Home of Carolina Golf**, Chapel Hill NC). He sells **corporate partnerships**:
marketing real estate (signage/branding), rounds of golf, golf outings, event
tickets, merch credit, and hosted events.

## How the user works with this repo

The user gives **any one or more** of: city, state, industry, company, person
— a single input alone is a complete request (default market: Chapel Hill /
Triangle, NC).
Run the `/prospect` skill (`.claude/skills/prospect/SKILL.md`) with those
inputs. It pulls companies/contacts from ZoomInfo, researches ad/marketing
spend on the web, scores prospects A/B/C, appends them to the master tracker,
republishes the tracker to Google Sheets, and creates one personalized Gmail
draft per decision-maker contact.

**Autopilot:** running `/prospect` with **no input** (or `auto`) makes it
choose its own targets via `config/autopilot.md` (dedupe + rotate + double
down on segments that are replying) and log the reasoning to
`tracker/autopilot-log.md`. A scheduled Routine fires this 2–3×/week. Email
voice is tuned in `config/voice.md`.

## Key files

| File | Purpose |
|------|---------|
| `.claude/skills/prospect/SKILL.md` | The end-to-end prospecting pipeline |
| `config/profile.md` | Seller identity + offer details used in every email |
| `scoring.md` | A/B/C ranking rubric (even blend: spend / size / fit) |
| `templates/*.md` | Catered outreach email templates per industry |
| `tracker/prospects.csv` | Master prospect data — source of truth for the Google Sheet |

## Rules

- **Tracker is append-only source of truth.** Never drop existing rows when
  adding a batch. One row per contact.
- **ONE permanent Google Sheet.** "Finley Golf Club — Sales Tracker" pulls
  `tracker/prospects.csv` live from GitHub raw (IMPORTDATA). Updating the
  tracker = append to CSV + push. Never create new sheets per run. The sheet
  originates from `tools/build_live_tracker_xlsx.py` (see the /prospect
  skill, Step 6, for when to rebuild).
- **Gmail drafts only, never send.** The user reviews and sends everything.
- **Proofread every email before creating its draft** — no unfilled merge
  fields, correct name/company/city, factually true hook, clean grammar, and
  the verbatim signature (SKILL.md Step 7).
- **Pipeline stages live in the Status column.** New prospects are `New`.
  Sync inbox replies (SKILL.md Step 0) into stages: any real reply →
  `Interested: 50%`; explicit no → `Not Interested: 0%`; advance to
  `Red-Hots: 75%` / `Agreements: 90%` / `Signed: 100%` only when the reply
  clearly warrants it. Stage colors are defined in
  `tools/build_live_tracker_xlsx.py`.
- **`Potential Revenue` is the user's column** — never overwrite it; only fill
  it from a concrete number the prospect gives.
- **Decision-makers only** from ZoomInfo: C-level, VP, Director, Owner,
  President, GM. No managers or below unless the user asks.
- Commit tracker updates to this repo after every run so nothing is lost when
  the session container is reclaimed.
