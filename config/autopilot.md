# Autopilot — autonomous target selection

When `/prospect` runs with **no input** (or input `auto`), don't ask for
keywords — choose the next targets here, act, and log why.

**Weekly rhythm:** Mon/Wed/Fri = new prospecting (this file). Tue/Thu =
follow-ups to non-repliers (`config/followups.md`), not new prospecting.

## Per-run budget
- **2 segments** per run (a segment = one industry × one market, where a market
  is an NC sub-market or, on outer-ring runs, a Southeast / East Coast metro).
- ~8–10 companies per segment (~15–20 companies total); pull the **full buying
  committee** per company — every useful contact, not just decision-makers
  (see SKILL.md Step 3). More contacts per company = more forward-up shots.
- Hard stop: don't enrich a 3rd segment in one run (ZoomInfo credit control).

## The universe
- **Core industries** (bread-and-butter): home services, healthcare, auto,
  legal/financial.
- **Expansion industries** (proven or promising): sports, hospitality &
  restaurants, commercial real estate, banking/wealth, insurance, med spa.
- **Coverage mandate: work outward by distance — saturate what's closest
  before expanding.** Drive-time is the product: the closer a prospect is, the
  easier the hospitality sell. So coverage is **gated, not weighted** — you do
  not open a farther tier until the nearer one is genuinely worked.

  | Tier | Territory | Open it when… |
  |------|-----------|---------------|
  | **1 — Triangle (home)** | Chapel Hill/Carrboro · Durham · Raleigh · Cary/Apex/Morrisville · Wake Forest/N. Raleigh · Hillsborough/Graham · Pittsboro | **always open** — the default for every run |
  | **2 — NC near-ring** (~1–2 hr) | Triad (Greensboro · Winston-Salem · High Point · Burlington) · Sandhills (Pinehurst/Southern Pines · Fayetteville) · Fayetteville corridor | Tier 1 saturated |
  | **3 — Rest of NC** (2–4 hr) | Charlotte metro · Coastal (Wilmington · Greenville · New Bern) · West (Asheville · Hickory · Boone) | Tiers 1–2 saturated |
  | **4 — Southeast** | SC · VA · GA · TN · northern FL | Tier 3 saturated |
  | **5 — East Coast** | DC/Baltimore · Philadelphia · NYC/NJ · Boston | Tier 4 saturated |
  | **6 — Nationwide** | national brands anywhere | Tier 5 saturated |

  **"Saturated" means:** every core industry in that tier has been swept at
  least once, and it holds ≥ 25 logged companies with no obviously untouched
  industry × sub-market pair left. Check `tracker/prospects.csv` before
  choosing — if you can still name an uncovered core industry in a nearer tier,
  **that** is the segment, not a farther one.

  **Always start each run at the lowest unsaturated tier.** Both of a run's two
  segments should normally come from that tier; only borrow from one tier
  farther when the current tier truly has nothing uncovered left.

  **On tiers 4–6, require a Carolinas tie** — HQ, a regional office, a plant,
  alumni leadership, or a travel/Stay-&-Play reason — so the Carolina-Golf
  hospitality pitch still lands. No cold national names without a tie.

  Note the current tier + why in `tracker/autopilot-log.md` each run.

## How to pick the 2 segments (priority order)
0. **Set the tier first.** Find the lowest unsaturated tier (see the coverage
   table). Both segments come from that tier unless it has nothing uncovered
   left. Never skip a nearer tier to chase a farther one.
1. **Dedupe first.** Load `tracker/prospects.csv`. Never re-pull a company
   already there (match on company name / ZoomInfo ID). Skip a segment that's
   already well-covered (≥6 companies logged in the last ~60 days).
2. **Double down on what's working.** If any industry has contacts at
   `Interested: 50%` or better in the tracker, make **one** of the two
   segments that industry in an uncovered sub-market — warm categories earn
   more at-bats.
3. **Breadth rotation within the tier.** Fill the other segment with the
   **least-recently-covered** core industry × sub-market *inside the current
   tier*, so the near territory fills in evenly before you move outward.
4. **Explore occasionally.** Roughly every 3rd–4th run, make one segment a
   new expansion industry we haven't tried, to find new veins (this is how
   "sports" got discovered).
5. **Never re-target** anyone marked `Not Interested: 0%`.

## Write down the reasoning (every run)
Before pulling data, append one line to `tracker/autopilot-log.md`:
`YYYY-MM-DD | seg1: <industry> / <submarket> · seg2: <industry> / <submarket> | why: <one sentence>`
Then run the normal pipeline (SKILL.md Steps 0–8) for both segments.

## Draft policy
Auto-create Gmail drafts for every A/B contact (**never send**), following
`config/voice.md`.
**Gate: OPEN** (Tyler signed off on the voice, 2026-07-28). Autopilot creates
Gmail drafts directly. They land in Gmail's Drafts folder for Tyler to review,
edit, and send — nothing is ever sent automatically. If Gmail auth is
unavailable at run time, fall back to staging finished drafts in `outbox/` and
say so in the run summary.

## Guardrails
- Stay home-weighted: most at-bats in NC, and on outer rings prefer a
  Carolinas tie (HQ/office/alumni/travel reason) so the pitch stays credible.
- If a segment returns nothing, widen one filter once (drop employee minimum /
  widen metro to state), then move on and note it.
- Respect the ZoomInfo credit rules in SKILL.md (batch enrichments; never
  re-enrich companies/contacts already in the tracker).
