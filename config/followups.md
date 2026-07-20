# Follow-ups — Tuesdays & Thursdays

Tue/Thu runs are for **follow-up emails to prospects who haven't replied** —
not new prospecting (new prospecting is Mon/Wed/Fri autopilot).

## Who is due a follow-up
Scan `tracker/prospects.csv` for any contact where ALL of these hold:
- an initial email went out (Draft Created = Y), AND
- Status is still `New` (no reply — anyone at `Interested: 50%`+ or
  `Not Interested: 0%` is done here), AND
- enough time has passed since the last touch (cadence below), AND
- fewer than 3 follow-ups have already been sent.

Never follow up with anyone at `Not Interested: 0%` or `Interested: 50%`+.

## Cadence (business days after the last touch)
- **Follow-up 1:** ~4 business days after the initial email.
- **Follow-up 2:** ~7 business days after follow-up 1.
- **Follow-up 3 (final):** ~10 business days after follow-up 2 — then stop,
  set Next Step to "Call / pause" and leave Status `New`.
Snap to the current Tue/Thu run; never send two touches to one contact in the
same week.

## Tracking (no new columns)
Record each follow-up in the row's **Notes**: `FU1 2026-07-22`, `FU2 …`.
Derive "due" from Date Added + the most recent `FU#` date in Notes, and
update **Next Step** to the next planned touch.

## Writing the follow-up (follow config/voice.md)
- Short — 40–70 words; reply on the original thread when possible.
- Briefly reference the first note, add ONE new angle or proof point, keep the
  same 15-minute ask. Never guilt-trip. Vary wording across FU1/FU2/FU3.
- Signature verbatim from `config/profile.md`. Drafts only, never send.

## Draft gate
Same gate as autopilot: keep auto-drafting OFF until Tyler signs off on the
voice; until then stage finished follow-ups in `outbox/`.
