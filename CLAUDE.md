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

## Key files

| File | Purpose |
|------|---------|
| `.claude/skills/prospect/SKILL.md` | The end-to-end prospecting pipeline |
| `config/profile.md` | Seller identity + offer details used in every email |
| `scoring.md` | A/B/C ranking rubric (even blend: spend / size / fit) |
| `templates/*.md` | Catered outreach email templates per industry |
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
- **Decision-makers only** from ZoomInfo: C-level, VP, Director, Owner,
  President, GM. No managers or below unless the user asks.
- Commit tracker updates to this repo after every run so nothing is lost when
  the session container is reclaimed.
