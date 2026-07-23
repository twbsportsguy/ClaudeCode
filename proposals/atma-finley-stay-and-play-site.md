# Stay-and-Play Website — ATMA Hotel Group × Finley Golf Club

**What it would take to build a site like tobaccoroadtravel.com**

Prepared by Tyler Baity, Senior Manager | Business Development & Operations
Finley Golf Club — Home of Carolina Golf · Chapel Hill, NC
twbaity@alumni.unc.edu · (336) 225-6396 · [Schedule a meeting](https://calendar.app.google/M9bXpDQ4sib6ekjq9)

---

## 1. The concept in one line

A co-branded **"Stay & Play" golf-travel site** that packages **ATMA's
Triangle-area hotels** (Sheraton Chapel Hill, Courtyard by Marriott, Hampton
Inn & Suites, Holiday Inn Express, and the wider NC portfolio) with **rounds at
Finley Golf Club and the Carolina Golf network** — so a visitor lands in one
place, sees "hotel + golf" bundles, and requests to book.

It captures golf-travel demand that today leaks to Pinehurst/Sandhills and
turns it into **room nights for ATMA and tee times for Finley.** The website is
the storefront; the real product is the partnership behind it.

---

## 2. What tobaccoroadtravel.com actually is (so we scope the right thing)

The single most important thing to understand before quoting a build: **Tobacco
Road Travel is not a real-time e-commerce site.** It is a **lead-and-quote
("concierge") website.** Visitors browse packages and submit a *quote request*;
a small team responds with a custom itinerary and takes payment offline. That
model is dramatically cheaper and faster to build than a live booking engine —
and it's the right starting point for us.

Broken into buildable parts, the reference site is:

| Component | What it does | Must-have for v1? |
|---|---|---|
| **Home / hero** | Value prop, "the Sandhills' preferred golf trips," CTA to build a package | Yes |
| **Packages** | Curated bundles (e.g. "3 rounds / 2 nights"), each with its own detail page, courses, hotel, and price-from | Yes |
| **Lodging pages** | One page per hotel/cabin with photos + amenities | Yes (start with 2–3) |
| **Course pages** | One page per golf course featured | Nice-to-have v1 |
| **Quote / "Build your package" form** | The real conversion engine — capture dates, group size, preferences | **Yes — this is the point** |
| **Travel guide / area info** | Downloadable PDF + things-to-do content | Later |
| **Tee-time booking** | Handled by a *third-party* engine on a separate subdomain (`go.`) | Later / optional |
| **About / contact** | Trust + phone number | Yes |

Technically it's a **WordPress site** (the page URLs expose `/wp-content/`),
which tells us the whole thing is achievable on off-the-shelf tooling — no
custom platform required.

---

## 3. Three ways to build it (recommendation first)

### ✅ Option A — WordPress + travel theme + quote forms  *(recommended for v1)*
Mirrors exactly how Tobacco Road is built. A designer/developer stands up a
polished template, we load hotels + packages as content, and a form plugin
(Gravity Forms / Fluent Forms) drives quote requests into an inbox and CRM.

- **Pros:** Fastest, cheapest, easy for non-developers to update, proven model.
- **Cons:** Quote-and-respond (not instant online booking) — but that's how the
  reference site works too.
- **Best when:** We want to be live this season and validate demand.

### Option B — Custom-built marketing site (Next.js / React)
A bespoke, higher-polish site. Worth it only if ATMA wants a distinctive,
brand-forward experience beyond what a theme allows.

- **Pros:** Full design control, fast, great for photography-heavy storytelling.
- **Cons:** 2–3× the cost of Option A; every content change needs a developer
  unless we add a CMS.

### Option C — White-label golf-package / booking platform
Several vendors sell stay-and-play engines with **live pricing and online
payment** (the "go." experience). Fastest path to *real-time* booking.

- **Pros:** Actual e-commerce checkout, inventory management built in.
- **Cons:** Monthly SaaS fees + revenue share; requires firm room-block and
  tee-sheet allocations up front. Overkill until demand is proven.

**Recommendation:** Launch on **Option A** as a quote-request site this season.
Layer in **Option C's** live booking only once volume justifies it.

Who does the work is a separate lever: a **local agency/freelancer** ($$),
or a **DIY/AI-assisted build** we drive ourselves ($, more of our time). For a
client-facing brand like ATMA's, a professional designer on the visuals is
money well spent even if we assemble the rest.

---

## 4. What it actually takes

### Effort & timeline (Option A, v1)
- **MVP (landing page + 2–3 packages + quote form + 2 hotels):** ~2–4 weeks
  once content and photos are in hand.
- **Full v1 (all hotels, course pages, gallery, travel guide, polished design):**
  ~6–10 weeks.

### Rough budget (directional — for scoping the conversation, not a quote)
| Item | One-time | Ongoing |
|---|---|---|
| Design + build (freelancer/small agency, Option A) | ~$4k–$12k | — |
| Domain + hosting + form/CRM plugins | ~$100–$400 | ~$40–$120 / mo |
| Professional photography (if new shots needed) | ~$1k–$4k | — |
| Live booking platform (Option C, *if/when added*) | setup varies | SaaS + rev-share |
| Ongoing content updates / seasonal package refreshes | — | few hrs/mo |

*(Custom build, Option B, typically runs ~$15k–$40k+.)*

### What we'd need to gather
- **From ATMA:** hotel list + descriptions/amenities, professional photos, the
  room rates or room-block allowances we can package, and who owns fulfillment.
- **From Finley / Carolina Golf:** course info + photography, tee-time
  availability and green-fee/package rates, which partner courses to include.
- **Jointly:** the actual package definitions and pricing, cancellation terms,
  and one shared inbox/CRM to catch and work the quote requests.

### Who runs it after launch
A quote-request site needs **one person who answers the leads** and turns them
into booked stays + tee times. That operational owner matters more than any
feature on the page.

---

## 5. The real work isn't the website

The site is a few weeks of design and content. The engine is the **commercial
agreement** between ATMA and Finley:

- How is revenue split on a bundled "hotel + golf" sale?
- What room-night blocks and tee-time inventory does each side commit?
- Who owns the customer and the booking record?
- What are the cancellation / no-show terms?

Nail those and the website is the easy part. That's exactly the kind of
partnership Finley builds — and why pairing ATMA's rooms with Carolina Golf's
courses is a package neither side can offer alone.

---

## 6. Suggested phasing

1. **Phase 1 — Prove demand (this season):** WordPress quote-request site,
   home + 2–3 flagship packages + quote form + 2 hotels + Finley. Point paid
   social / local search at it.
2. **Phase 2 — Full storefront:** all ATMA properties, course pages, photo
   galleries, downloadable travel guide, refined design.
3. **Phase 3 — Live booking (only if volume warrants):** add a stay-and-play
   engine with real-time pricing and online payment.

---

## 7. Recommended next steps

1. **30-minute scoping call** with ATMA to agree on v1 scope and the 2–3
   flagship packages.
2. **Confirm the commercial terms** (revenue share, room blocks, tee-time
   allocation) — the actual gating item.
3. **Gather content & photography** from both sides.
4. **Engage a designer/developer** for the Option A build; target a v1 launch
   ahead of peak golf-travel season.

I'm glad to lead the Finley side of this and help coordinate the build.

— Tyler

---

### Sources / references
- Tobacco Road Golf & Travel — https://www.tobaccoroadtravel.com/ (structure, package/lodging pages, quote-request model)
- ATMA Hotel Group portfolio — https://atmahotelgroup.com/portfolio/
