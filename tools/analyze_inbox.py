#!/usr/bin/env python3
"""Classify everything that came back from an outreach send.

`analyze_conversations.py` answers "what are prospects telling us" from replies
already written into the tracker. This answers the question one step earlier:
of everything sitting in the inbox, what is actually a reply at all?

Most inbound mail after a send is not a reply. It is a bounce, an
out-of-office, a departure notice, a newsletter from a company we happen to
have pitched, or Tyler's own sent mail showing up in the thread. Each of those
means something different for the tracker, and three of them are worth more
than the replies:

  * a hard bounce means the address is dead and every future draft to it is
    wasted
  * a departure notice usually names the replacement, which is a better contact
    than the one that bounced
  * an out-of-office usually names a delegate, and gives a date to follow up on

Input is the JSON that `mcp__Gmail__search_threads` returns (one or more
responses concatenated into a list of threads), optionally enriched with
`plaintextBody` from `get_thread`. Nothing here talks to Gmail itself — the
agent fetches, this classifies, so a run is reproducible and reviewable.

  python3 tools/analyze_inbox.py inbox.json [--csv tracker/prospects.csv]

Writes dashboard/inbox.json and prints a report. It proposes tracker changes;
it does not make them. The tracker is append-only and a misfiled rejection is
far more expensive than a manual edit.
"""
import sys, os, re, json, csv, collections, datetime

TRACK = "tracker/prospects.csv"
OUT   = "dashboard/inbox.json"
OURS  = {"twbaity@alumni.unc.edu", "tbaity@playersnext.com",
         "jhawkins@playersnext.com", "mlehmann@playersnext.com"}

# ---------------------------------------------------------------- campaigns
# The same two inboxes carried several campaigns. A "no" to one is not a "no"
# to another, so every message gets tagged and the youth-sports book is
# excluded outright (see SKILL.md Step 0).
CAMPAIGNS = [
    ("finley-partnership", r"finley golf club \| proud partnership|proud partners?hip|"
                           r"finley golf club|carolina golf|night on the range|old well patron|heels club"),
    ("bass-classic",       r"finley bass classic"),
    ("youth-sports",       r"what's next for youth sports|playersnext foundation|"
                           r"athletes and families of youth sports"),
]
def campaign(text):
    for name, pat in CAMPAIGNS:
        if re.search(pat, text, re.I): return name
    return "unknown"

# ---------------------------------------------------------------- bounces
BOUNCE_SENDER = re.compile(r"mailer-daemon|postmaster|no-?reply.*(?:mail|delivery)", re.I)
BOUNCE_SUBJ   = re.compile(r"undeliverable|delivery status notification|returned mail|"
                           r"delivery has failed|undelivered mail|mail delivery (?:failed|subsystem)", re.I)
# Every provider words this differently; order is irrelevant, all are tried.
FAILED_ADDR = [
    r"delivery has failed to these recipients or groups:\s*(\S+@\S+)",
    r"wasn'?t delivered to (\S+@\S+)",
    r"problem delivering your message to (\S+@\S+)",
    r"your message to (\S+@\S+) couldn'?t be delivered",
    r"permanent fatal errors\s*-+\s*<(\S+@\S+)>",
    r"the following recipient\(?s?\)? failed:?\s*(\S+@\S+)",
    r"<(\S+@\S+)>:\s*(?:host|Recipient address rejected)",
]
# 5.x.x is permanent (dead address); 4.x.x is temporary (retry later).
SMTP = re.compile(r"\b([45])\.\d{1,3}\.\d{1,3}\b")
SMTP_BASIC = re.compile(r"\b([45])\d\d[\s-]")

def bounce_detail(text, thread_sent_to):
    for pat in FAILED_ADDR:
        m = re.search(pat, text, re.I)
        if m: addr = m.group(1).strip(" <>.,;"); break
    else:
        # No address in the notice. The bounce sits in the same thread as the
        # message that failed, so the sent message's recipient IS the address.
        addr = thread_sent_to[0] if thread_sent_to else ""
    m = SMTP.search(text) or SMTP_BASIC.search(text)
    cls = m.group(1) if m else ""
    kind = "hard" if cls == "5" else "soft" if cls == "4" else "unknown"
    reason = ("address not found" if re.search(r"couldn'?t be found|address not found|"
                                               r"recipient unknown|user unknown|no such user|"
                                               r"does not exist|wasn'?t found", text, re.I)
              else "mailbox full" if re.search(r"mailbox (?:is )?full|quota", text, re.I)
              else "blocked / rejected" if re.search(r"blocked|rejected|policy|spam|denied", text, re.I)
              else "unspecified")
    # An "address not found" is permanent regardless of whether a code parsed.
    if kind == "unknown" and reason == "address not found": kind = "hard"
    return addr.lower(), kind, reason

# ---------------------------------------------------------------- auto-replies
DEPARTED = re.compile(r"no longer (?:with|at|employed|works?|in-house|being monitored)|"
                      r"has left the (?:company|firm|organi[sz]ation)|is no longer", re.I)
OOO = re.compile(r"automatic reply|auto-?reply|out of (?:the )?office|"
                 r"currently (?:out|away|travel)|on pto|on leave|on vacation|"
                 r"limited access to email", re.I)
# The delegate named in an OOO or departure notice — often a better contact
# than the one we wrote to. Anchor on the address and look *backwards* for the
# name: anchoring on the name instead lets it eat the local part, so
# "contact Curtis.Driver@..." yields name "Curtis", address "driver@...".
EMAIL = re.compile(r"(?<![\w.+-])([\w.+-]+@[\w-]+\.[\w.]+\w)")
NAME_BEFORE = re.compile(r"([A-Z][A-Za-z'\-]+(?: [A-Z][A-Za-z'\-]+){0,2})"
                         r"\s*(?:\bat\b|\bon\b|,|:|-|\()?\s*$")
RETURN_DATE = re.compile(r"return(?:ing|s)?(?:\s+to\s+(?:the\s+)?office)?"
                         r"(?:\s+on)?\s+((?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day,?\s+)?"
                         r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}"
                         r"|\d{1,2}/\d{1,2}(?:/\d{2,4})?)", re.I)

def delegates(text, exclude):
    out = []
    for m in EMAIL.finditer(text):
        addr = m.group(1).lower().strip(".,;")
        if addr in exclude or addr in OURS: continue
        if any(addr == d["email"] for d in out): continue
        # Prefer a name written before the address; otherwise reconstruct one
        # from the local part, which is how most of these are formatted anyway.
        nm = NAME_BEFORE.search(text[max(0, m.start() - 60):m.start()])
        name = nm.group(1) if nm else ""
        if name.lower() in ("contact", "email", "reach", "to", "at", "please", "assistance"):
            name = ""
        if not name and re.match(r"^[a-z]+[._][a-z]+$", addr.split("@")[0]):
            name = " ".join(p.capitalize() for p in re.split(r"[._]", addr.split("@")[0]))
        out.append({"name": name.strip(), "email": addr})
    return out[:3]

# ---------------------------------------------------------------- broadcasts
ROLE = re.compile(r"^(no-?reply|donotreply|do-?not-?reply|marketing|newsletter|news|"
                  r"updates?|notifications?|info|hello|team|events?|support|sales|"
                  r"contact|admin|mail|email|automated)@", re.I)
BULK = re.compile(r"unsubscribe|view (?:this )?in browser|manage your preferences|"
                  r"you are receiving this|email preferences|privacy policy\s*\|", re.I)

# ---------------------------------------------------------------- replies
POSITIVE = re.compile(r"\b(?:interested|sounds good|let'?s (?:talk|chat|connect|set)|"
                      r"happy to|would love|send (?:me |over )?(?:more|the|details|info)|"
                      r"call (?:works|sounds)|available|schedule|calendar|"
                      r"tell me more|great to hear|yes\b)", re.I)
NEGATIVE = re.compile(r"\b(?:not interested|no thank|we'?ll pass|i'?ll pass|not a (?:good )?fit|"
                      r"unable to|can'?t commit|outside of what|no budget|budget is|"
                      r"already (?:have|committed|work with)|remove me|unsubscribe|"
                      r"stop emailing|take me off|decline)", re.I)
REFERRAL = re.compile(r"(?:reach out to|contact|talk to|speak (?:with|to)|forwarded (?:this )?to|"
                      r"passing (?:this|you) (?:on|along)|best person|handles (?:this|our))", re.I)

def classify(msg, thread_sent_to, sent_subjects):
    sender  = (msg.get("sender") or "").lower()
    subject = msg.get("subject") or ""
    body    = msg.get("plaintextBody") or msg.get("snippet") or ""
    text    = f"{subject}\n{body}"
    labels  = set(msg.get("labelIds") or [])

    if "SENT" in labels or any(o in sender for o in OURS):
        return "ours", {}
    if BOUNCE_SENDER.search(sender) or BOUNCE_SUBJ.search(subject):
        addr, kind, reason = bounce_detail(text, thread_sent_to)
        return f"bounce-{kind}", {"failed": addr, "reason": reason}
    if DEPARTED.search(body):
        return "departed", {"replacements": delegates(body, {sender})}
    if OOO.search(subject) or OOO.search(body[:300]):
        m = RETURN_DATE.search(body)
        return "auto-ooo", {"returns": (m.group(2) if m else ""),
                            "delegates": delegates(body, {sender})}
    if ROLE.match(sender) or BULK.search(body) or {"CATEGORY_PROMOTIONS"} & labels:
        return "broadcast", {}
    # A real reply must be on one of our threads, not merely from a domain we
    # happen to have pitched (SKILL.md Step 0, condition (a)).
    on_thread = bool(thread_sent_to) or any(
        subject.lower().lstrip().startswith("re:") and s.lower() in subject.lower()
        for s in sent_subjects)
    if not on_thread:
        return "unsolicited", {}
    if NEGATIVE.search(body):  return "reply-negative", {}
    if POSITIVE.search(body):  return "reply-positive", {}
    if REFERRAL.search(body):  return "reply-referral", {}
    return "reply-neutral", {}


def load_threads(path):
    raw = json.load(open(path))
    if isinstance(raw, dict): raw = [raw]
    threads = []
    for blob in raw:
        threads.extend(blob["threads"] if isinstance(blob, dict) and "threads" in blob else [blob])
    return threads


def main():
    src = sys.argv[1]
    track = TRACK
    if "--csv" in sys.argv: track = sys.argv[sys.argv.index("--csv") + 1]

    rows = list(csv.reader(open(track)))
    hdr, body_rows = rows[0], rows[1:]
    by_email = {}
    for r in body_rows:
        if len(r) > 15 and "@" in r[15]:
            by_email.setdefault(r[15].strip().lower(), r)
        # Addresses retired by sync_activity.py stay indexed via their DEAD-EMAIL
        # tag, so a bounce still resolves to a company on later runs.
        for a in re.findall(r"DEAD-EMAIL:\s*([\w.+-]+@[\w.-]+)", r[21] if len(r) > 21 else ""):
            by_email.setdefault(a.lower(), r)

    results, counts = [], collections.Counter()
    for th in load_threads(src):
        msgs = th.get("messages") or []
        # Campaign is a property of the thread, not the message. A bounce notice
        # says "Returned mail: see transcript" and names no campaign; the sent
        # message it is bouncing does. Reading it per-message loses every bounce.
        th_camp = campaign("\n".join(
            f"{m.get('subject','')}\n{m.get('snippet','')}\n{m.get('plaintextBody','')}"
            for m in msgs))
        sent_to, sent_subj = [], []
        for m in msgs:
            if "SENT" in set(m.get("labelIds") or []) or (m.get("sender") or "").lower() in OURS:
                sent_to.extend(a.lower() for a in (m.get("toRecipients") or []))
                if m.get("subject"): sent_subj.append(re.sub(r"^re:\s*", "", m["subject"], flags=re.I))
        for m in msgs:
            kind, extra = classify(m, sent_to, sent_subj)
            addr = extra.get("failed") or (m.get("sender") or "").lower()
            row  = by_email.get(addr)
            camp = th_camp
            # Tyler's inbox is also his work inbox. A message that matches no
            # campaign and no tracker row is his day job, not outreach — an
            # out-of-office from a professor is not a prospect signal.
            if not row and camp == "unknown" and kind != "ours":
                kind = "irrelevant"
            # The youth-sports book is a different offer with different answers;
            # importing it here would put false rejections on Finley cards.
            if camp == "youth-sports":
                kind = "other-campaign"
            counts[kind] += 1
            if kind in ("ours", "irrelevant", "other-campaign"): continue
            results.append({
                "kind": kind, "date": (m.get("date") or "")[:10],
                "from": m.get("sender"), "subject": m.get("subject"),
                "address": addr,
                "company": row[3] if row else "", "contact": row[13] if row else "",
                "status": row[19] if row and len(row) > 19 else "",
                "in_tracker": bool(row), "campaign": camp,
                **extra,
            })

    # ---- deliverability, by domain. One dead address is a typo; four at one
    # company means something systemic — and the two systemic causes need
    # opposite responses, so they are counted apart. "address not found" is our
    # data being stale: re-source the contacts. "access denied / rejected" is
    # their server refusing outside mail: the addresses may be perfectly good
    # and no amount of re-sourcing will help.
    dom = collections.defaultdict(lambda: {"sent": 0, "stale": 0, "blocked": 0, "soft": 0})
    for th in load_threads(src):
        for m in th.get("messages") or []:
            if "SENT" in set(m.get("labelIds") or []):
                for a in m.get("toRecipients") or []:
                    dom[a.split("@")[-1].lower()]["sent"] += 1
    for r in results:
        if r["kind"].startswith("bounce") and "@" in r["address"]:
            d = dom[r["address"].split("@")[-1]]
            # A bounce proves a send even when the sent copy isn't in the dump.
            if not d["sent"]: d["sent"] = 0
            key = ("soft" if r["kind"] == "bounce-soft"
                   else "stale" if r["reason"] == "address not found" else "blocked")
            d[key] += 1
    for d in dom.values():
        d["sent"] = max(d["sent"], d["stale"] + d["blocked"] + d["soft"])

    dead = [r for r in results if r["kind"] == "bounce-hard"]
    gone = [r for r in results if r["kind"] == "departed"]
    ooo  = [r for r in results if r["kind"] == "auto-ooo"]
    real = [r for r in results if r["kind"].startswith("reply-")]

    W = lambda s: print(s)
    W("=" * 72); W("INBOX ANALYSIS"); W("=" * 72)
    for k, n in counts.most_common(): W(f"  {k:16} {n:>4}")

    W(f"\n{'-'*72}\nDEAD ADDRESSES — {len(dead)} hard bounce(s). Stop drafting to these.\n{'-'*72}")
    for r in sorted(dead, key=lambda x: x["date"], reverse=True):
        tag = "" if r["in_tracker"] else "   [not in tracker]"
        W(f"  {r['date']}  {r['address']:44} {r['reason']}{tag}")
        if r["company"]: W(f"{'':14}{r['company']} — {r['contact']}")

    W(f"\n{'-'*72}\nCONTACT HAS LEFT — {len(gone)}. Replace the row, don't just kill it.\n{'-'*72}")
    for r in gone:
        W(f"  {r['date']}  {r['from']}")
        for d in r.get("replacements") or []:
            W(f"{'':14}-> {d['name'] or '(unnamed)'} <{d['email']}>")

    W(f"\n{'-'*72}\nOUT OF OFFICE — {len(ooo)}. Not a no; a date to come back on.\n{'-'*72}")
    for r in ooo:
        W(f"  {r['date']}  {r['from']:44} returns {r.get('returns') or '?'}")
        for d in r.get("delegates") or []:
            W(f"{'':14}delegate: {d['name'] or '(unnamed)'} <{d['email']}>")

    W(f"\n{'-'*72}\nREAL REPLIES — {len(real)}\n{'-'*72}")
    for r in sorted(real, key=lambda x: x["kind"]):
        W(f"  {r['kind'][6:]:9} {r['date']}  {r['from']:40} [{r['campaign']}]")
        W(f"{'':14}{(r['subject'] or '')[:70]}")

    W(f"\n{'-'*72}\nDELIVERABILITY BY DOMAIN\n{'-'*72}")
    W(f"  {'domain':34}{'sent':>5}{'stale':>6}{'blockd':>7}{'soft':>5}   diagnosis")
    for d, s in sorted(dom.items(), key=lambda kv: -(kv[1]["stale"] + kv[1]["blocked"])):
        if not (s["stale"] or s["blocked"] or s["soft"]): continue
        note = ("their server refuses outside mail — re-sourcing addresses won't help, "
                "find a phone or a referral" if s["blocked"] > s["stale"]
                else "our contact data is stale — re-pull this company from ZoomInfo")
        W(f"  {d:34}{s['sent']:>5}{s['stale']:>6}{s['blocked']:>7}{s['soft']:>5}   {note}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"generated": datetime.date.today().isoformat(),
               "counts": dict(counts), "messages": results,
               "domains": {k: v for k, v in dom.items()
                           if v["stale"] or v["blocked"] or v["soft"]}},
              open(OUT, "w"), indent=1)
    W(f"\nWrote {OUT} ({len(results)} inbound messages classified)")

    W(f"\n{'-'*72}\nPROPOSED TRACKER CHANGES (review before applying)\n{'-'*72}")
    for r in dead:
        if r["in_tracker"]:
            W(f"  {r['company']} / {r['contact']}: Notes += 'BOUNCED {r['date']} "
              f"({r['reason']}) — address dead'; clear Contact Email")
        else:
            W(f"  {r['address']}: hard bounce, no tracker row — nothing to update")
    for r in gone:
        for d in r.get("replacements") or []:
            W(f"  {r.get('company') or r['from']}: add contact {d['name']} <{d['email']}>, "
              f"retire {r['from']}")

if __name__ == "__main__":
    main()
