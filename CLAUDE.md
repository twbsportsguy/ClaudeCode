# Sales Prospecting Workspace

This repo powers a corporate-partnerships prospecting workflow. The user sells
**corporate partnerships** for a sports/golf property: marketing real estate
(signage/branding), rounds of golf, golf outings, event tickets, merch credit,
and hosted events.

## How the user works with this repo

The user gives any combination of: **city, state, industry, company, person**.
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

## Rules

- **Tracker is append-only source of truth.** Never drop existing rows when
  adding a batch. One row per contact.
- **Google Sheets can't be edited in place** with the available Drive tools —
  always regenerate the full sheet from `tracker/prospects.csv` and upload as
  a new "Sales Tracker" file (title includes the update date). Tell the user
  the old copy can be deleted.
- **Gmail drafts only, never send.** The user reviews and sends everything.
- **Decision-makers only** from ZoomInfo: C-level, VP, Director, Owner,
  President, GM. No managers or below unless the user asks.
- Commit tracker updates to this repo after every run so nothing is lost when
  the session container is reclaimed.
