#!/usr/bin/env python3
"""Address-freshness gate. Cuts the bounce rate, which is what gets a sender flagged.

WHY THIS EXISTS
---------------
Two independent measures put this book's hard-bounce rate at ~14%:

  * 186 contacts drafted, 25 later flagged DEAD-EMAIL  -> 13.4%
  * 2026-07-29: 55 sent, 47 delivered, 8 bounced       -> 14.5%

Mailbox providers treat hard bounces as the signal that someone is mailing a
purchased list. Under 2-3% is healthy; over 5% is where throttling and domain
blocks begin. At ~14% the send volume barely matters — the list quality is what
gets the address filtered, and this book already carries 10 SERVER BLOCK
domains as proof.

None of that is inevitable. It is stale ZoomInfo records. ZoomInfo returns a
validation date and an accuracy score per contact; using them before drafting
is the single highest-value change available to deliverability.

THE HARD PART: 1,203 of 1,243 rows have no validation metadata at all
--------------------------------------------------------------------
Only 40 rows carry `validated <date>` / `accuracy <n>` in Notes. So a gate that
blocks anything unproven would block 97% of the book and stop the programme
dead. That is not a safety feature, it is an outage.

So the gate is three-state, not two:

  BLOCK  — positively known to be bad: accuracy < 85, or validated > 365d ago.
           These are the ones actually likely to bounce.
  WARN   — unknown, or validated 180-365d ago. Draft them, but they are the
           pool the bounce rate comes from, and the count is reported so the
           coverage problem stays visible instead of quietly persisting.
  PASS   — validated within 180d AND accuracy >= 85.

Coverage is the real fix. Every new ZoomInfo pull must write `validated <date>`
and `accuracy <n>` into Notes (SKILL.md Step 3). As coverage rises the WARN pool
shrinks and this gate gets sharper on its own.

USAGE
  python3 tools/check_addresses.py                       # coverage report
  python3 tools/check_addresses.py --csv tracker/bass-classic.csv
  python3 tools/check_addresses.py --blocklist           # addresses to not draft
"""
import csv, re, sys, datetime, collections

CSV = "tracker/prospects.csv"

# Validated within this many days counts as fresh.
FRESH_DAYS = 180
# Older than this and the record is presumed dead regardless of accuracy.
STALE_DAYS = 365
# ZoomInfo contact accuracy below this bounces often enough to skip.
MIN_ACCURACY = 85

VALIDATED = re.compile(r"validated\s+(\d{4}-\d{2}-\d{2})", re.I)
ACCURACY = re.compile(r"accuracy\s+(\d{1,3})", re.I)
DEAD = re.compile(r"DEAD-EMAIL|SERVER BLOCK", re.I)


def parse(notes):
    """-> (validated date or None, accuracy int or None)"""
    m, a = VALIDATED.search(notes or ""), ACCURACY.search(notes or "")
    d = None
    if m:
        try:
            d = datetime.date.fromisoformat(m.group(1))
        except ValueError:
            d = None
    return d, (int(a.group(1)) if a else None)


def verdict(notes, today=None):
    """-> ('BLOCK'|'WARN'|'PASS', reason)"""
    today = today or datetime.date.today()
    if DEAD.search(notes or ""):
        return "BLOCK", "already flagged DEAD-EMAIL or SERVER BLOCK"
    d, acc = parse(notes)
    if acc is not None and acc < MIN_ACCURACY:
        return "BLOCK", f"accuracy {acc} below {MIN_ACCURACY}"
    if d is not None:
        age = (today - d).days
        if age > STALE_DAYS:
            return "BLOCK", f"validated {age}d ago, over {STALE_DAYS}d"
        if age > FRESH_DAYS:
            return "WARN", f"validated {age}d ago"
        if acc is None:
            return "WARN", f"validated {age}d ago but no accuracy score"
        return "PASS", f"validated {age}d ago, accuracy {acc}"
    if acc is not None:
        return "WARN", f"accuracy {acc} but no validation date"
    return "WARN", "no validation metadata"


def load(path):
    rows = list(csv.reader(open(path)))
    hdr = rows[0]
    ix = {k: n for n, k in enumerate(hdr)}
    return hdr, ix, rows[1:]


def main():
    a = sys.argv[1:]
    path = a[a.index("--csv") + 1] if "--csv" in a else CSV
    hdr, ix, rows = load(path)
    today = datetime.date.today()

    counts = collections.Counter()
    reasons = collections.Counter()
    blocked = []
    for r in rows:
        if len(r) < len(hdr):
            continue
        notes = r[ix["Notes"]] + " " + r[ix["Next Step"]]
        email = r[ix["Contact Email"]].strip()
        v, why = verdict(notes, today)
        counts[v] += 1
        reasons[why.split(",")[0]] += 1
        if v == "BLOCK" and email:
            blocked.append((email, why))

    if "--blocklist" in a:
        for e, why in sorted(set(blocked)):
            print(f"{e}\t{why}")
        return

    tot = sum(counts.values())
    print(f"{path}: {tot} contacts\n")
    for k in ("PASS", "WARN", "BLOCK"):
        n = counts[k]
        print(f"  {k:6} {n:>5}  {100*n/tot if tot else 0:5.1f}%")
    print("\ntop reasons:")
    for why, n in reasons.most_common(8):
        print(f"  {n:>5}  {why}")

    cov = tot - reasons.get("no validation metadata", 0)
    print(f"\nvalidation coverage: {cov}/{tot} ({100*cov/tot if tot else 0:.1f}%)")
    if cov / tot < 0.5 if tot else False:
        print("  Coverage is the bottleneck, not the thresholds. Every new")
        print("  ZoomInfo pull must record `validated <date>` and `accuracy <n>`")
        print("  in Notes, or this gate stays mostly advisory.")


if __name__ == "__main__":
    main()
