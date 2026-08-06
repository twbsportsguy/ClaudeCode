# Autopilot — autonomous target selection

When `/prospect` runs with **no input** (or input `auto`), don't ask for
keywords — choose the next targets here, act, and log why.

**Weekly rhythm:** Mon/Wed/Fri = new prospecting (this file). Tue/Thu =
follow-ups to non-repliers (`config/followups.md`), not new prospecting.

## Per-run budget — 50 drafts (Tyler, 2026-08-05)

Asked for 100/day, then asked what was actually safe and set it to **50**.

**The binding constraint is the bounce rate, not the daily count.** Two
independent measures put this book at ~14% hard bounces (186 drafted → 25
DEAD-EMAIL = 13.4%; 2026-07-29's 55 sent → 8 bounced = 14.5%). Healthy is under
2–3%; over 5% is where mailbox providers start throttling and blocking. At ~14%
the volume barely matters — the list quality is what gets an address flagged,
and this book already carries 10 SERVER BLOCK domains.

Compounding it: `twbaity@alumni.unc.edu` is a domain Tyler does not control. No
SPF/DKIM/DMARC to tune, no subdomain to warm, reputation shared with the whole
university, and a flag lands on his real professional identity. Volume beyond a
single well-behaved mailbox needs a Finley-owned domain, not a bigger number
here.

- **Target: 50 drafts per MWF run** (~150/week, matching a safe 30/day send rate
  across five weekdays). Raise toward 50/day sends only once bounces hold under
  3% for two to three weeks.
- **3–4 segments** per run. The old 2-segment cap was too tight; 4–6 was set
  briefly for the 100 target and is more than 50 needs.
- ~8–10 companies per segment, **full buying committee** per company (SKILL.md
  Step 3). At 3–4 contacts per company, ~15 companies reaches 50.
- Open segments until the target is met. A thin segment is a reason to open the
  next one, never a reason to end the run.

### Address freshness is part of the budget

Run `python3 tools/check_addresses.py` before drafting. Never draft to a
**BLOCK** address — accuracy below 85, validated over a year ago, or already
carrying DEAD-EMAIL / SERVER BLOCK. Find another contact at that company.

**Record validation metadata on every new pull.** ZoomInfo returns a validation
date and an accuracy score; write them into Notes as
`Accuracy <n>, validated <YYYY-MM-DD>`. Coverage is currently **6.2%** (77 of
1,243 rows), which is why the gate is mostly advisory — it sharpens on its own
as coverage rises, and that is the single highest-value change available to
deliverability.

### Honesty about the number

- **Commit every 10 drafts.** A run that dies at 30 must leave 30 drafts and a
  synced tracker, not nothing. Runs have died partway six times.
- **Report the real count**, not the target. Under-delivering is acceptable;
  pretending is not.
- **Depth is what gets cut, not honesty.** If research has to go shallower to
  reach volume, name the companies that got the shallow pass so they can be
  revisited. A draft with a fabricated hook is worse than no draft.
- ZoomInfo credit control still applies: if the subscription rate-limits, stop
  pulling and finish drafting what you already have.

## The universe
Derived from Tyler's actual book (397 companies imported from the FGC Master
SalesTracker) — not guesses. Counts are companies already logged.

- **Core industries** (the proven engine — most of the book):
  - **Greek organizations** (32) — UNC fraternities/sororities. A Finley-specific
    segment: high volume, price-sensitive, Night on the Range fits them.
  - **Wealth management / family offices** (32) and **law firms** (24) —
    relationship buyers; lead with hosted rounds, not signage.
  - **Construction** (28) and **wholesale supply** (22) — crews, subs and
    clients in one day; the 80-player outing is the natural pitch.
  - **Local businesses** (24) — awareness-first, smaller entry points.
- **Strong secondary:** tech (18), real estate (15), auto (10), dental (9),
  rental equipment (9), marketing agencies (8), manufacturing/dealers (8),
  finance (7), UNC groups & schools (6), electrical/HVAC (6), consulting/
  accounting (5).
- **Untested but promising:** hospitality & restaurants, insurance, med spa,
  healthcare beyond dental.
- Greek organizations and UNC groups only exist in the Triangle tier — don't
  look for them on outer rings.
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

  **Note (2026-07-28):** Tier 1 now holds ~397 companies from the imported
  book, so raw count no longer proves saturation. Judge by *industry ×
  sub-market* gaps instead — e.g. Greek orgs are well covered, but healthcare
  beyond dental, hospitality/restaurants and insurance are still untouched
  in the Triangle.

  **Always start each run at the lowest unsaturated tier.** Both of a run's two
  segments should normally come from that tier; only borrow from one tier
  farther when the current tier truly has nothing uncovered left.

  **On tiers 4–6, require a Carolinas tie** — HQ, a regional office, a plant,
  alumni leadership, or a travel/Stay-&-Play reason — so the Carolina-Golf
  hospitality pitch still lands. No cold national names without a tie.

  **A distant HQ is not a distant company.** Before writing off an out-of-state
  employer, check for local staff with
  `locationSearchType: "Person"` + `state: "North Carolina"` (SKILL.md Step 3).
  If it returns branch/store/territory managers or local events people, treat
  the account as **local** — those people hold the budget and can drive to
  Finley, so the normal hospitality pitch applies. Only when there are no NC
  people does it become a true outer-ring account, and then the pitch shifts
  from hospitality to brand exposure (aim at sponsorship / brand-partnership
  titles instead of site leadership).

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
