"""Split legacy tracker rows that pack several contacts into one cell.

The old spreadsheet stored whole buying committees as comma-joined (and
sometimes slash-joined) name/email/phone strings. That breaks the one-row-per-
contact rule and hides the contacts from the dashboard, which counts a packed
row as a single contact.

Splitting blind is unsafe: equal name/email counts do NOT prove the two lists
line up. So every pair must pass a name<->email affinity check before the row
is split. Anything that fails is left untouched and reported for human review.
"""
import csv, re, sys

TRACKER="tracker/prospects.csv"
APPLY = "--apply" in sys.argv

def tokens(s):
    """Split on comma and slash, drop empties, strip trailing/leading junk."""
    if not s: return []
    parts=re.split(r"[,/]", s)
    return [p.strip(" \t;") for p in parts if p.strip(" \t;")]

def strip_title(name):
    """The old sheet appended titles two ways:
         'Kim Florek (Dir of Mkting)'  and  'Michael Spohn - CEO'
    Pull the title out so it lands in Contact Title and stops corrupting the
    name<->email match (otherwise 'CEO' gets treated as the surname)."""
    m=re.match(r"^(.*?)\s*\((.+?)\)\s*$", name)
    if m: return m.group(1).strip(), m.group(2).strip()
    m=re.match(r"^(.*?)\s+[-\u2013]\s+(.+)$", name)
    if m: return m.group(1).strip(), m.group(2).strip()
    return name.strip(), ""

def affinity(name, email):
    """True when the email's local part plausibly belongs to this person."""
    if "@" not in email or "." not in email.split("@")[-1]:
        return False                        # not an address at all (e.g. "INSTAGRAM")
    local=email.split("@")[0].lower()
    alnum=re.sub(r"[^a-z]", "", local)
    words=[w for w in re.split(r"[^A-Za-z]+", strip_title(name)[0].lower()) if len(w)>1]
    if not words or not alnum: return False
    first, last = words[0], words[-1]
    if first in alnum or last in alnum: return True
    # initial-style handles: jsmith / johns / smt (Sherry M Toler) / wao
    if alnum.startswith(first[0]) and last[:4] in alnum: return True
    if alnum.startswith(first[:4]) and alnum.endswith(last[0]): return True
    if len(alnum)<=4 and alnum.startswith(first[0]) and alnum.endswith(last[0]): return True
    # nickname handles: joe@ for Joseph, dan@ for Daniel
    if len(alnum)>=3 and first.startswith(alnum): return True
    return False

def domain_outlier(emails):
    """Flag a row where one address sits on a near-miss of the shared domain --
    almost always a typo in the old sheet (woodandsmith vs wardandsmith)."""
    doms=[e.split("@")[-1].lower() for e in emails if "@" in e]
    if len(doms)<3: return None
    top=max(set(doms), key=doms.count)
    if doms.count(top)<len(doms)-1: return None
    for d in doms:
        if d!=top and len(d)>4 and abs(len(d)-len(top))<=3:
            a,b=set(d),set(top)
            if len(a&b)/max(len(a|b),1) > 0.7:
                return f"{d} looks like a typo of {top}"
    return None

rows=list(csv.DictReader(open(TRACKER)))
fields=list(rows[0].keys())

out=[]; split_rows=0; new_contacts=0; flagged=[]
for r in rows:
    names, emails = tokens(r["Contact Name"]), tokens(r["Contact Email"])
    if len(emails) < 2:                     # nothing packed
        out.append(r); continue
    phones=tokens(r["Contact Phone"])
    titles=tokens(r["Contact Title"])

    reason=domain_outlier(emails)
    if reason: pass
    elif len(names)!=len(emails):
        reason=f"{len(names)} names vs {len(emails)} emails"
    else:
        bad=[f"{n} -> {e}" for n,e in zip(names,emails) if not affinity(n,e)]
        # tolerate one unverifiable pair (nicknames, maiden names) but no more
        if len(bad)>1:
            reason=f"{len(bad)}/{len(names)} pairs failed the name<->email check: "+"; ".join(bad[:3])

    if reason:
        flagged.append((r["Company"], r["Status"], reason, r["Contact Name"], r["Contact Email"]))
        out.append(r); continue

    for i,(n,e) in enumerate(zip(names,emails)):
        clean_name, inline_title = strip_title(n)
        nr=dict(r)
        nr["Contact Name"]=clean_name
        nr["Contact Email"]=e
        nr["Contact Title"]=inline_title or (titles[i] if i<len(titles) else (titles[0] if len(titles)==1 else ""))
        nr["Contact Phone"]=phones[i] if i<len(phones) else ""
        if i>0:
            # Potential Revenue is a per-company figure Tyler owns; keep it on the
            # first row only so splitting doesn't multiply the forecast.
            nr["Potential Revenue"]=""
            nr["Notes"]=(r["Notes"]+" | ").lstrip(" |")+"split from packed legacy row 2026-07-28"
        out.append(nr)
    split_rows+=1; new_contacts+=len(emails)-1

print(f"packed rows split : {split_rows}  (+{new_contacts} new contact rows)")
print(f"left for review   : {len(flagged)}")
print(f"tracker rows      : {len(rows)} -> {len(out)}")

if APPLY:
    with open(TRACKER,"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(out)
    print("WROTE tracker/prospects.csv")

print("\n=== needs your eyes ===")
for c,st,why,n,e in flagged:
    print(f"\n{c}  [{st}]\n  why: {why}\n  names : {n[:150]}\n  emails: {e[:150]}")
