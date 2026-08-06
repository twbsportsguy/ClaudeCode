# Follow-ups — Tuesdays & Thursdays

Tue/Thu runs are for **follow-up emails to prospects who haven't replied** —
not new prospecting (new prospecting is Mon/Wed/Fri autopilot).

## Who is due a follow-up
Scan `tracker/prospects.csv` for any contact where ALL of these hold:
- an initial email went out (Draft Created = Y), AND
- Status is still `New` (no reply — anyone at `Interested: 50%`+ or
  `Not Interested: 0%` is done here), AND
- **the last touch was 7 or more calendar days ago**, AND
- fewer than 4 follow-ups have already been sent.

Never follow up with anyone at `Not Interested: 0%` or `Interested: 50%`+.

## Cadence — a flat 7 days (Tyler, 2026-08-05)

*"Follow up on all companies that haven't replied within 7 days."*

Every unreplied contact gets chased **every 7 calendar days** from its last
touch, up to FU4. This replaced a 4/7/10 **business**-day ladder that stretched
to roughly five weeks for three touches and left most of the book untouched.

- **FU1** — 7 days after the initial email
- **FU2** — 7 days after FU1
- **FU3** — 7 days after FU2
- **FU4 (final)** — 7 days after FU3, then stop: set Next Step to
  "Call / pause" and leave Status `New`

Never send two touches to one contact in the same week. Coverage is the point —
**every** eligible contact gets chased on a given run, not a sample of them.

**The FU4 cap is a judgement call, not Tyler's instruction.** He asked for the
7-day rule and said nothing about when to stop. Four touches over a month is
already persistent; uncapped weekly mail to someone who has never answered
reads as automated and is the fastest way to get a domain filtered. Raise or
remove it if Tyler wants — but change it here, deliberately, not by drift.

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
Same gate as autopilot: **OPEN** (2026-07-28). Create follow-up Gmail drafts
directly — never send. If Gmail auth is unavailable, stage them in `outbox/`
and note it in the run summary.
