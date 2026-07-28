#!/usr/bin/env python3
"""Win/loss analysis over every reply recorded in the tracker.

Reads what prospects actually wrote back — the Notes column carries the reply
text from the legacy sheet and from each reply-sync run — and turns it into
answers to "what's working and what isn't":

  * reply and win rates by industry, so the book can be aimed
  * why people say no, in their own words, grouped into causes
  * which no's are really "not yet", and the month they told us to come back
  * what they ask for when they DO engage

Everything here is derived from recorded text. Nothing is inferred from a
company's size or industry alone — if there is no reply on file, the company
counts as "no reply", not as a loss.

Writes dashboard/insights.json, which build_dashboard_data.py embeds.
"""
import csv, re, json, collections, datetime

TRACK = "tracker/prospects.csv"
OUT   = "dashboard/insights.json"

STAGES = ["Signed: 100%", "Agreements: 90%", "Red-Hots: 75%",
          "Interested: 50%", "Re-approach: 25%", "Not Interested: 0%"]
WARM   = {"Signed: 100%", "Agreements: 90%", "Red-Hots: 75%", "Interested: 50%"}
LOST   = {"Not Interested: 0%", "Re-approach: 25%"}

def clean(s):
    s = re.sub(r"^\[(?:old tracker|legacy)\s*\|\s*rep\s*([^\]]*)\]\s*", "", (s or "").strip())
    s = re.sub(r"\s*\|\s*split from packed legacy row [\d-]+\s*$", "", s)
    s = re.sub(r"Committee expansion \d{4}-\d{2}-\d{2}[^|]*", "", s)
    s = re.sub(r"TODO:[^|\n]+|SCORE\s*\d+\s*(?:->|→)\s*\d+[^|\n]*", "", s, flags=re.I)
    return re.sub(r"\s{2,}", " ", s).strip(" |")

# A reply is text beyond the bare date/log stamps the reps left.
STAMP = re.compile(r"^(?:\d{1,2}/\d{1,2}/\d{2,4}|intro sent \d{1,2}/\d{1,2}|fu\d?\s*\d{0,2}/?\d{0,2}|\d{1,2}/\d{1,2})[\s,]*", re.I)
def reply_text(note):
    t = note
    prev = None
    while t != prev:                      # strip leading date/log stamps repeatedly
        prev = t
        t = STAMP.sub("", t).strip(" -–|")
    # Some logged replies are a single word ("Budget"), so keep anything
    # that is not purely a date stamp.
    return t if len(t) >= 5 else ""

# Why they said no — matched against the prospect's own words, most specific first.
REASONS = [
    ("Budget spent this cycle", r"out of (?:marketing )?budget|budget(?:s)? (?:already )?(?:used|tapped|allocated|spent)|already allocated|budget\b.*\b(?:used|gone)|2026 budget|out of budget"),
    ("Timing — come back later",  r"reach (?:back )?out in|next year|next semester|in the spring|future years|keep (?:your )?info|on file|keep on radar|reallocated in the spring|q[1-4] of next year|after the holidays|start of the new year|sometime next year"),
    ("Already committed elsewhere", r"set on partnerships|not exploring additional partnerships|already (?:have|work with)|events are booked"),
    ("Not a fit / wrong audience", r"not (?:really )?a (?:good )?fit|not in my wheelhouse|not in the golf space|aren.t a good fit|no interest|not interested|i.ll pass|not right now|not something we would be interested"),
    ("Policy forbids it",         r"expenses are not allowed|can not do|cannot do|does not advertise|department of war"),
    ("Too far to travel",         r"too far"),
    ("Rival allegiance",          r"nc state|anti-unc|cheating scandal"),
    ("Hard opt-out",              r"stop emailing|take me off|blocked me|unsubscribe|remove me"),
]

# What they ask for when they DO engage.
ASKS = [
    ("Wants pricing",            r"sent prices|pricing|terms of use|send along any details|any details you can share"),
    ("Wants a meeting or call",  r"meeting|hop on a call|call went well|schedule another call|connect after"),
    ("Reviewing internally",     r"look(?:ing)? into this internally|looking over internally|run (?:it )?up the flag|review this opportunity|internally|take a look"),
    ("Routing to someone else",  r"sent to|forwarded to|put us in touch|connecting us with|give her your contact|copying my partners|contact information"),
    ("Wants to donate in kind",  r"donat(?:e|ing) for raffles|raffles"),
    ("Golf-culture affinity",    r"golf nut|hosts golf tourney|golf tourney|frequent finley|rounds of golf|night on the range"),
]

MONTHS = {m.lower(): i for i, m in enumerate(
    ["January","February","March","April","May","June","July",
     "August","September","October","November","December"], 1)}
def come_back_when(t):
    """The window a prospect named for coming back, in their words."""
    low = t.lower()
    for name, num in MONTHS.items():
        if re.search(r"\b(?:in|reach out in|back in)\s+" + name + r"\b", low):
            return name.capitalize(), num
    if re.search(r"\b(?:the )?spring\b", low):        return "Spring", 3
    if re.search(r"\bq2\b", low):                     return "Q2", 4
    if re.search(r"\bq3\b", low):                     return "Q3", 7
    if re.search(r"\b2027\b", low):                   return "2027", 13
    if re.search(r"next semester|new exec|executive board", low): return "Next semester", 1
    if re.search(r"after the holidays|new year|next year", low):  return "New year", 1
    return None, None

def main():
    rows = list(csv.DictReader(open(TRACK)))
    cos = collections.OrderedDict()
    for r in rows:
        c = cos.setdefault(r["Company"], {"ind": "", "stages": set(), "notes": set(), "contacts": 0, "drafts": 0})
        if r["Industry"].strip(): c["ind"] = r["Industry"].strip()
        c["stages"].add(r["Status"].strip())
        n = clean(r["Notes"])
        if n: c["notes"].add(n)
        if "@" in r["Contact Email"]: c["contacts"] += 1
        if r["Draft Created"].strip().upper() == "Y": c["drafts"] += 1

    def stage_of(s):
        for k in STAGES:
            if k in s: return k
        return "New"

    def industry(raw):
        i = (raw or "").lower()
        if "greek" in i:                                    return "Greek organizations"
        if "unc group" in i or "school" in i:               return "UNC teams & schools"
        if "wealth" in i or "finance" in i:                 return "Wealth management & finance"
        if "law" in i:                                      return "Law firms"
        if "consult" in i or "account" in i:                return "Consulting & accounting"
        if "constr" in i or "engineer" in i or "arch" in i: return "Construction & engineering"
        if "wholesale" in i or "supply" in i or "dealer" in i or "rental" in i: return "Wholesale, supply & equipment"
        if "hospital" in i or "health" in i or "pharm" in i or "dental" in i:   return "Healthcare"
        if "local business" in i:                           return "Local businesses"
        if "market" in i or "advert" in i:                  return "Marketing & brands"
        if "real estate" in i:                              return "Real estate"
        if "travel" in i or "airline" in i:                 return "Auto & travel"
        return "Unclassified"

    by_ind = collections.defaultdict(lambda: {"n":0,"replied":0,"warm":0,"lost":0,"quotes":[]})
    reasons  = collections.defaultdict(list)
    asks     = collections.defaultdict(list)
    calendar = []
    replies_total = warm_total = lost_total = 0

    for name, c in cos.items():
        st  = stage_of(c["stages"])
        ind = industry(c["ind"])
        txt = " | ".join(sorted(c["notes"]))
        rep = reply_text(txt)
        b = by_ind[ind]; b["n"] += 1
        if rep:
            b["replied"] += 1; replies_total += 1
        if st in WARM: b["warm"] += 1; warm_total += 1
        if st in LOST: b["lost"] += 1; lost_total += 1
        if not rep: continue

        low = rep.lower()
        if st in LOST:
            for label, pat in REASONS:
                if re.search(pat, low):
                    reasons[label].append({"co": name, "ind": ind, "q": rep[:220], "stage": st})
                    break
        else:
            for label, pat in ASKS:
                if re.search(pat, low):
                    asks[label].append({"co": name, "ind": ind, "q": rep[:220]})
        when, order = come_back_when(rep)
        if when:
            calendar.append({"co": name, "ind": ind, "when": when, "order": order,
                             "stage": st, "q": rep[:200]})

    for ind, b in by_ind.items():
        b["replyRate"] = round(b["replied"] / b["n"] * 100) if b["n"] else 0
        # Win rate is measured against companies that actually answered — an
        # unanswered email is not a loss, and counting it as one would make
        # every industry look equally bad.
        answered = b["warm"] + b["lost"]
        b["winRate"] = round(b["warm"] / answered * 100) if answered else None
        b["answered"] = answered

    calendar.sort(key=lambda x: (x["order"], x["co"]))
    out = {
        "generated": datetime.date.today().isoformat(),
        "totals": {"companies": len(cos), "replied": replies_total,
                   "warm": warm_total, "lost": lost_total},
        "industries": [dict(name=k, **v) for k, v in
                       sorted(by_ind.items(), key=lambda kv: -kv[1]["replied"])],
        "reasons": [{"label": k, "n": len(v), "items": v}
                    for k, v in sorted(reasons.items(), key=lambda kv: -len(kv[1]))],
        "asks":    [{"label": k, "n": len(v), "items": v}
                    for k, v in sorted(asks.items(), key=lambda kv: -len(kv[1]))],
        "calendar": calendar,
    }
    json.dump(out, open(OUT, "w"), indent=1)

    t = out["totals"]
    print(f"{t['companies']} companies · {t['replied']} replied · {t['warm']} warm · {t['lost']} said no")
    print("\nby industry (reply rate / win rate among those who answered):")
    for i in [x for x in out["industries"] if x["name"] != "Unclassified"][:12]:
        wr = f"{i['winRate']}%" if i["winRate"] is not None else "—"
        print(f"  {i['name']:32} n={i['n']:>3}  replied {i['replied']:>3} ({i['replyRate']:>3}%)  won {i['warm']:>3}/{i['answered']:<3} {wr}")
    print("\nwhy they said no:")
    for r in out["reasons"]:
        print(f"  {r['n']:>3}  {r['label']}")
    print("\nwhat engaged prospects ask for:")
    for a in out["asks"]:
        print(f"  {a['n']:>3}  {a['label']}")
    print(f"\ncome-back calendar: {len(out['calendar'])} companies named a window")
    for c in out["calendar"][:14]:
        print(f"  {c['when']:14} {c['co'][:34]:34} {c['q'][:70]}")

if __name__ == "__main__":
    main()
