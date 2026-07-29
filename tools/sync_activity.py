#!/usr/bin/env python3
"""Work out which drafts actually got sent, update the tracker, show today.

A draft sitting in Gmail and an email that reached a prospect are different
facts, and only Tyler can turn the first into the second. Until now nothing
closed that loop: the tracker said "Draft Created: Y" forever, so a contact
looked worked whether or not anything ever left the outbox, and follow-up runs
had no way to tell the difference.

This reads the sent mail, matches it to tracker rows by recipient, and reports
the day: what went out, what bounced back, what replied, what is still waiting
in drafts.

  python3 tools/sync_activity.py threads.json [--drafts drafts.json]
                                 [--csv tracker/prospects.csv]
                                 [--date YYYY-MM-DD] [--apply]

Without --apply it prints the changes it would make. With --apply it writes
**only mechanical facts** — that a message was sent, and that an address is
dead. It will never move a pipeline stage: whether a reply means "interested"
is a judgement call, and a wrong one is expensive (see the Blackwood note in
scoring.md). Stage changes stay with analyze_inbox.py's proposals and a human.
"""
import sys, csv, json, re, datetime, collections
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from analyze_inbox import load_threads, classify, campaign, OURS

TRACK = "tracker/prospects.csv"
SENT_TAG = "SENT"


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def main():
    src    = sys.argv[1]
    track  = arg("--csv", TRACK)
    day    = arg("--date", datetime.date.today().isoformat())
    apply_ = "--apply" in sys.argv
    dpath  = arg("--drafts")

    rows = list(csv.reader(open(track)))
    hdr, data = rows[0], rows[1:]
    by_email = {}
    for r in data:
        if len(r) > 15 and "@" in r[15]:
            by_email.setdefault(r[15].strip().lower(), []).append(r)
        for a in re.findall(r"DEAD-EMAIL:\s*([\w.+-]+@[\w.-]+)", r[21] if len(r) > 21 else ""):
            by_email.setdefault(a.lower(), []).append(r)

    sent, inbound = [], []
    for th in load_threads(src):
        msgs = th.get("messages") or []
        th_camp = campaign("\n".join(
            f"{m.get('subject','')}\n{m.get('snippet','')}\n{m.get('plaintextBody','')}"
            for m in msgs))
        to_all, subj_all = [], []
        for m in msgs:
            if SENT_TAG in set(m.get("labelIds") or []) or (m.get("sender") or "").lower() in OURS:
                to_all.extend(a.lower() for a in (m.get("toRecipients") or []))
                if m.get("subject"): subj_all.append(m["subject"])
        for m in msgs:
            d = (m.get("date") or "")[:10]
            if SENT_TAG in set(m.get("labelIds") or []):
                for a in (m.get("toRecipients") or []):
                    sent.append({"date": d, "to": a.lower().strip(),
                                 "subject": m.get("subject") or "", "campaign": th_camp})
            else:
                kind, extra = classify(m, to_all, subj_all)
                if kind == "ours": continue
                inbound.append({"date": d, "kind": kind,
                                "from": (m.get("sender") or "").lower(),
                                "address": extra.get("failed") or (m.get("sender") or "").lower(),
                                "subject": m.get("subject") or "", "campaign": th_camp})

    pending = []
    if dpath:
        for d in json.load(open(dpath)):
            if d["subject"].startswith("[VOID") or not d.get("toRecipients"): continue
            pending.append(d["toRecipients"][0].lower())
    sent_addrs = {s["to"] for s in sent}
    dead = {i["address"] for i in inbound if i["kind"] == "bounce-hard"}

    # ---------------------------------------------------------------- today
    t_sent  = [s for s in sent if s["date"] == day]
    t_in    = [i for i in inbound if i["date"] == day]
    t_bounce= [i for i in t_in if i["kind"].startswith("bounce")]
    t_reply = [i for i in t_in if i["kind"].startswith("reply-")]
    t_auto  = [i for i in t_in if i["kind"] in ("auto-ooo", "departed")]

    print("=" * 72)
    print(f"ACTIVITY — {day}")
    print("=" * 72)
    # Count addresses, not messages: a bounce can arrive for a send whose own
    # copy isn't in the dump, and subtracting one count from the other then
    # reports negative deliveries.
    t_to = {s["to"] for s in t_sent}
    delivered = len(t_to - dead)
    print(f"  sent            {len(t_to):>4}")
    print(f"  delivered       {delivered:>4}"
          + (f"   ({delivered/len(t_to)*100:.0f}% of sent)" if t_to else ""))
    print(f"  bounced         {len(t_bounce):>4}")
    print(f"  replies         {len(t_reply):>4}")
    print(f"  auto/departed   {len(t_auto):>4}")
    print(f"  still in drafts {len([p for p in pending if p not in sent_addrs]):>4}"
          if dpath else "  still in drafts   n/a (pass --drafts)")

    if t_sent:
        print(f"\n{'-'*72}\nSENT TODAY\n{'-'*72}")
        for s in sorted(t_sent, key=lambda x: x["to"]):
            rs = by_email.get(s["to"])
            who = f"{rs[0][3]} / {rs[0][13]}" if rs else "(not in tracker)"
            mark = "  BOUNCED" if s["to"] in dead else ""
            print(f"  {s['to']:44} {who}{mark}")

    if t_reply:
        print(f"\n{'-'*72}\nREPLIES TODAY — read these before anything else\n{'-'*72}")
        for i in t_reply:
            print(f"  {i['kind'][6:]:9} {i['from']:40} {i['subject'][:40]}")

    still = [p for p in pending if p not in sent_addrs]
    if dpath and still:
        print(f"\n{'-'*72}\nSTILL WAITING IN DRAFTS ({len(still)})\n{'-'*72}")
        for p in sorted(still):
            rs = by_email.get(p)
            print(f"  {p:44} {rs[0][3] if rs else '(not in tracker)'}")

    # ------------------------------------------------------- tracker updates
    changes = []
    for r in data:
        if len(r) < 22: continue
        e = r[15].strip().lower()
        if not e or "@" not in e: continue
        mine = [s for s in sent if s["to"] == e]
        if mine and "SENT " not in r[21]:
            last = max(x["date"] for x in mine)
            changes.append((r, "sent", last, e))
        if e in dead and "BOUNCED" not in r[21]:
            # Carry the address in the record. Reading `e` in the apply loop
            # below picks up whatever the last row of this loop left behind,
            # which stamped every bounced row with one unrelated address.
            changes.append((r, "bounce", day, e))

    print(f"\n{'-'*72}\nTRACKER UPDATES ({'applying' if apply_ else 'dry run'})\n{'-'*72}")
    if not changes: print("  nothing to change")
    for r, what, when, addr in changes:
        if what == "sent":
            print(f"  SENT    {r[3]:32} {r[13][:24]:26} {when}")
            if apply_:
                r[18] = "Y"
                r[21] = (r[21] + " | " if r[21].strip() else "") + f"SENT {when}"
                if not r[20].strip() or r[20].startswith("Send draft"):
                    r[20] = f"Sent {when} — follow up if no reply by " + (
                        datetime.date.fromisoformat(when) + datetime.timedelta(days=5)).isoformat()
        else:
            print(f"  BOUNCE  {r[3]:32} {r[13][:24]:26} address dead")
            if apply_:
                # Keep the dead address on the row as DEAD-EMAIL. Clearing the
                # Contact Email is what stops future runs drafting into a void,
                # but doing only that made the next analyze_inbox run unable to
                # match the bounce back to a company — the tool blinded itself
                # to its own findings. Both readers index this tag as well.
                r[21] = (r[21] + " | " if r[21].strip() else "") + \
                        f"BOUNCED {when} — address dead, do not re-draft (DEAD-EMAIL: {addr})"
                r[20] = "Address dead — re-source this contact before any further outreach"
                r[15] = ""

    if apply_ and changes:
        csv.writer(open(track, "w", newline="")).writerows([hdr] + data)
        print(f"\n  wrote {len(changes)} change(s) to {track}")
    elif changes:
        print(f"\n  re-run with --apply to write these {len(changes)} change(s)")

    print("\n  NB: stages are never changed here. Whether a reply means "
          "'interested'\n      is a judgement call — analyze_inbox.py proposes, a human decides.")

    # Embedded by build_dashboard_data.py — the page is a self-contained
    # artifact and cannot fetch anything at view time.
    import os
    os.makedirs("dashboard", exist_ok=True)
    named = lambda a: (by_email.get(a) or [[""]*23])[0]
    json.dump({
        "date": day,
        "sent": len(t_to), "delivered": delivered, "bounced": len(t_bounce),
        "replies": len(t_reply), "auto": len(t_auto),
        "pending": len(still) if dpath else None,
        "sentList": [{"e": a, "co": named(a)[3], "who": named(a)[13],
                      "dead": a in dead} for a in sorted(t_to)],
        "pendingList": [{"e": p, "co": named(p)[3]} for p in sorted(still)][:60],
        "history": sorted(collections.Counter(s["date"] for s in sent).items())[-30:],
    }, open("dashboard/activity.json", "w"), indent=1)
    print("  wrote dashboard/activity.json")


if __name__ == "__main__":
    main()
