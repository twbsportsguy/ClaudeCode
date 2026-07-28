#!/usr/bin/env python3
"""Import legacy FGC Google-Sheet trackers into tracker/prospects.csv.

Walks the flattened sheet export, tracking whichever stage section it is
inside, and emits one row per contact. Handles multi-contact cells, splits
'Not Interested' into genuine rejections vs. budget/timing objections vs.
rows that were never actually answered.
"""
import json,csv,re,sys,collections

STAGE_HDR=[(re.compile(r'(?i)^2026 clients$'),"Signed: 100%"),
           (re.compile(r'(?i)^2026 verbals \(90%\)$'),"Agreements: 90%"),
           (re.compile(r'(?i)^red hots \(75% chance\)$'),"Red-Hots: 75%"),
           (re.compile(r'(?i)^interested \(50%\)$'),"Interested: 50%"),
           (re.compile(r'(?i)^interested in future$'),"__FUTURE__"),
           (re.compile(r'(?i)^not interested$'),"__NI__"),
           (re.compile(r'(?i)^2026 prospects$'),"New")]
SKIP=re.compile(r'(?i)^(2026 sales|2026 verbals|2026 red hot & renewals|prospects|:-:)\s*$')
HARD=re.compile(r'(?i)stop emailing|take me off|blocked me|anti-unc|nc state grad|does not advertise|expenses are not allowed|department of war|not in the golf space|no interest|not interested|not a fit|that is not something|thanks,? but not|wheelhouse')
AMBER=re.compile(r'(?i)right now|at this time|atm\b|budget|i\'ll pass|next year|revisit|too expensive')
RECONTACT=re.compile(r'(?i)need new contact|retired|shared with management')

def cells(l): return [x.strip() for x in l.split("|")][1:-1]

def parse(path,label):
    t=json.load(open(path))["fileContent"].split("\n")
    stage="New"; out=[]
    for l in t:
        c=cells(l)
        if not c or not c[0]: continue
        first=c[0]
        hdr=next((s for p,s in STAGE_HDR if p.match(first)),None)
        if hdr: stage=hdr; continue
        if SKIP.match(first) or (len(c)>1 and c[1]=="Industry"): continue
        if len(first)<2: continue
        ind=c[1] if len(c)>1 else ""; rep=c[3] if len(c)>3 else ""
        kdm=c[4] if len(c)>4 else ""; em=c[5] if len(c)>5 else ""
        ph=c[6] if len(c)>6 else ""; rev=c[7] if len(c)>7 else ""
        note=" ".join(x for x in c[8:] if x).strip()
        st,nxt=stage,""
        if stage=="__FUTURE__":
            st="Interested: 50%"; nxt="Warm — asked for later; lead with the custom-build change"
        elif stage=="__NI__":
            body=re.sub(r'(intro sent|fu)\s*|\d{1,2}/\d{1,2}(/\d{2,4})?','',note).strip(' .-')
            if RECONTACT.search(note): st,nxt="New","Find a new contact — prior contact left or it was routed internally"
            elif not body: st,nxt="New","Never actually replied — re-approach with the custom-build angle"
            elif AMBER.search(note) and not re.search(r'(?i)stop emailing|take me off|blocked|anti-unc',note):
                st,nxt="Re-approach: 25%","Re-approach — prior no was budget/timing; lead with custom builds"
            elif HARD.search(note): st,nxt="Not Interested: 0%","DO NOT CONTACT — explicit no on record"
            else: st,nxt="Not Interested: 0%","DO NOT CONTACT — closed, reason unclear"
        elif stage=="New": nxt="From the legacy book — not yet worked"
        else: nxt="Warm from the legacy book — re-engage"
        names=[x.strip() for x in re.split(r'\s*/\s*',kdm)] if kdm else [""]
        mails=[x.strip() for x in re.split(r'[\s,]*/\s*|,\s*',em) if x.strip()] if em else [""]
        pairs=list(zip(names,mails)) if len(names)==len(mails) and len(names)>1 else [(kdm,em)]
        for nm,mail in pairs:
            out.append(["2026-07-28 (imported)","","",first,ind,"","","","","","","",
                f"Imported from {label}",nm,"",mail,ph,"","N",st,nxt,
                (f"[legacy | rep {rep}] {note}" if note else f"[legacy | rep {rep}]"),rev])
    return out

rows=[]
for path,label in [(sys.argv[1],"FGC Master SalesTracker"),(sys.argv[2],"FGC SalesTracker Segmented")]:
    r=parse(path,label); print(f"{label}: {len(r)} contact rows"); rows+=r

# dedupe internally, then against the live tracker
seen=set(); ded=[]
for r in rows:
    k=(r[3].strip().lower(), r[15].strip().lower())
    if k in seen: continue
    seen.add(k); ded.append(r)
ex=list(csv.reader(open("tracker/prospects.csv")))[1:]
have={(x[3].strip().lower(),x[15].strip().lower()) for x in ex if len(x)>15}
haveco={x[3].strip().lower() for x in ex if len(x)>3}
new=[r for r in ded if (r[3].strip().lower(),r[15].strip().lower()) not in have]
print(f"\nafter dedupe: {len(ded)}  |  new vs live tracker: {len(new)}")
newco={r[3].strip().lower() for r in new}-haveco
print(f"brand-new COMPANIES: {len(newco)}")
json.dump(new,open("/tmp/claude-0/-home-user-ClaudeCode/3dd1bda5-ad54-5e57-ae74-cbe9fdce4115/scratchpad/import2.json","w"))
print("\nstatus mix of the new rows:")
for k,v in collections.Counter(r[19] for r in new).most_common(): print(f"   {v:>4}  {k}")
