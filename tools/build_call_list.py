#!/usr/bin/env python3
"""Build the dashboard's call list: follow-ups that email cannot deliver.

WHY A SEPARATE PANEL
--------------------
Every other view in SalesFlow assumes the next action is an email. For 31
contacts across 11 companies that assumption is simply false — their mail
servers refuse outside senders, or the address on file is dead. They sat
invisible in the pipeline as `New` rows that no follow-up run would ever touch,
because every run correctly skips them.

Invisible is the problem. A prospect nobody can email is not a dead prospect,
it is a prospect who needs a phone call, and the dashboard should say so out
loud rather than leaving them to rot in a status nobody queries.

THE DISTINCTION THAT MATTERS ON THIS SCREEN
-------------------------------------------
  BLOCKED — the mail server refuses outside senders outright. Anderson
            Automotive bounced 9 of 9, Crossroads Ford 6 of 6. Re-pulling the
            address from ZoomInfo changes NOTHING; it will bounce identically.
            Phone or referral is the only channel.
  STALE   — our data is old and the address no longer resolves. This one IS
            fixable with a fresh pull, and the phone number is usually still
            good. Worth re-sourcing before writing the account off.

Collapsing those two into "bad email" would send someone re-pulling six
companies for whom re-pulling is futile, and would let two fixable ones sit
uncorrected. Hence they are coloured and labelled differently.

USAGE
  python3 tools/build_call_list.py            # -> dashboard/calls.json + index.html
  python3 tools/build_call_list.py --print    # report only, writes nothing
"""
import csv, re, json, sys, datetime, collections, os

CSV, OUT, DASH = "tracker/prospects.csv", "dashboard/calls.json", "dashboard/index.html"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_addresses import verdict

DUE_DAYS = 7
# Companies known to refuse outside mail outright, matched by NAME rather than
# by domain. Anderson owns anderson-auto.net and andersonautomotive.com as well
# as andersonautomotivegroup.com; matching the domain alone lets the other two
# back in and they bounce identically. Crossroads runs a per-dealership domain
# (crossroadsmitsubishilumberton.com and friends) with the same result.
BLOCKED_COMPANY = re.compile(r"anderson|crossroads|\bRSM\b", re.I)
# A note saying SERVER BLOCK is authoritative even when the domain has no
# bounce history yet — someone recorded it after reading the rejection.
BLOCKED_NOTE = re.compile(r"SERVER BLOCK", re.I)


def build(today=None):
    today = today or datetime.date.today()
    dom = json.load(open("dashboard/inbox.json")).get("domains", {})
    rows = list(csv.reader(open(CSV)))
    hdr = rows[0]
    ix = {k: n for n, k in enumerate(hdr)}
    byco = collections.defaultdict(list)

    for r in rows[1:]:
        if len(r) < len(hdr):
            continue
        if r[ix["Draft Created"]].strip().upper() != "Y":
            continue
        if not r[ix["Status"]].strip().startswith("New"):
            continue
        email = r[ix["Contact Email"]].strip().lower()
        d = email.split("@")[-1]
        notes = r[ix["Notes"]] + " " + r[ix["Next Step"]]
        try:
            age = (today - datetime.date.fromisoformat(r[ix["Date Added"]].strip())).days
        except ValueError:
            continue
        if age < DUE_DAYS:
            continue

        st = dom.get(d, {})
        if (st.get("blocked", 0) or BLOCKED_COMPANY.search(r[ix["Company"]])
                or BLOCKED_NOTE.search(notes)):
            kind = "blocked"
        elif st.get("stale", 0) or verdict(notes, today)[0] == "BLOCK":
            kind = "stale"
        else:
            continue          # reachable by email — not a call

        byco[r[ix["Company"]]].append({
            "name": r[ix["Contact Name"]], "title": r[ix["Contact Title"]],
            "phone": r[ix["Contact Phone"]].strip(), "email": email,
            "age": age, "kind": kind,
        })

    out = []
    for co, people in byco.items():
        # A company is only "re-pullable" if NONE of its contacts is hard-blocked.
        kind = "blocked" if any(p["kind"] == "blocked" for p in people) else "stale"
        row0 = next(r for r in rows[1:] if len(r) >= len(hdr) and r[ix["Company"]] == co)
        out.append({
            "company": co, "city": row0[ix["City"]], "state": row0[ix["State"]],
            "rank": row0[ix["Rank"]], "score": row0[ix["Score"]],
            "industry": row0[ix["Industry"]], "kind": kind,
            "contacts": sorted(people, key=lambda p: (not p["phone"], p["name"])),
        })
    out.sort(key=lambda c: (c["kind"] != "stale", -len(c["contacts"])))
    return {"generated": today.isoformat(), "companies": out,
            "contacts": sum(len(c["contacts"]) for c in out),
            "withPhone": sum(1 for c in out for p in c["contacts"] if p["phone"])}


def inject(payload):
    lit = "const CALLS = " + json.dumps(payload, ensure_ascii=False) + ";\n"
    html = open(DASH).read()
    new, n = re.subn(r"const CALLS = \{.*?\};\n", lambda m: lit, html, count=1, flags=re.S)
    if not n:
        # First run: anchor it next to the other generated literals.
        anchor = "const NEWS_GENERATED="
        if anchor not in new:
            print(f"FAILED: no place to put the literal in {DASH}; nothing written.")
            return 1
        i = new.index(anchor)
        new = new[:i] + lit + new[i:]
    open(DASH, "w").write(new)
    return 0


def main():
    p = build()
    print(f"{p['contacts']} contacts / {len(p['companies'])} companies "
          f"({p['withPhone']} with a phone number)")
    for c in p["companies"]:
        print(f"  [{c['kind']:<7}] {c['company'][:32]:<32} {len(c['contacts'])}")
    if "--print" in sys.argv:
        return
    os.makedirs("dashboard", exist_ok=True)
    json.dump(p, open(OUT, "w"), indent=1)
    rc = inject(p)
    print(f"wrote {OUT}" + ("" if rc else f" and injected into {DASH}"))


if __name__ == "__main__":
    main()
