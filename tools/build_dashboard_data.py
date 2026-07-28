#!/usr/bin/env python3
"""Regenerate the dashboard's DATA array from tracker/prospects.csv.

Keeps the rich, ZoomInfo-enriched entries already embedded in the dashboard
(signal / why / revenue / budget) and layers every other company from the
tracker on top as a lighter card. Never invents a score or a dollar figure for
a company we haven't actually researched.
"""
import csv, json, re, sys, collections

DASH="dashboard/index.html"
TRACK="tracker/prospects.csv"

def existing_data(html):
    s=html.index("const DATA = [")
    e=html.index("\n];",s)+3
    return s,e,html[s:e]

def money(s):
    if not s: return 0.0
    m=re.search(r'([\d.]+)\s*([MBK]?)', s.replace(",","").replace("$",""), re.I)
    if not m: return 0.0
    v=float(m.group(1)); u=(m.group(2) or "").upper()
    return v*1000 if u=="B" else (v/1000 if u=="K" else v)

STAGE={"Signed: 100%":"signed","Agreements: 90%":"verbal","Red-Hots: 75%":"redhot",
       "Interested: 50%":"interested","Re-approach: 25%":"prospect","Not Interested: 0%":"lost"}

html=open(DASH).read()
s,e,block=existing_data(html)
rich={}
for m in re.finditer(r'\{name:"((?:[^"\\]|\\.)*)"', block):
    rich[m.group(1)]=True

# ---- group tracker by company ----
rows=list(csv.reader(open(TRACK)))
hdr,body=rows[0],rows[1:]
cos=collections.OrderedDict()
for r in body:
    if len(r)<23: continue
    name=r[3].strip()
    if not name: continue
    c=cos.setdefault(name,{"name":name,"ind":r[4].strip(),"city":r[5].strip(),
        "web":r[7].strip().replace("www.",""),"rev":r[8].strip(),"emp":r[9].strip(),
        "budget":r[10].strip(),"signal":r[11].strip(),"why":r[12].strip(),
        "rank":r[1].strip(),"score":r[2].strip(),"status":r[19].strip(),
        "notes":r[21].strip(),"pot":r[22].strip(),"contacts":[]})
    if r[13].strip():
        c["contacts"].append({"n":r[13].strip(),"t":r[14].strip(),
            "e":r[16].strip() if "@" in r[15] else (r[15].strip() or None),
            "p":r[16].strip() if "@" not in r[16] and r[16].strip() else None,
            "d":r[18].strip().upper()=="Y"})
    # strongest status wins for the company
    order=["","New","Re-approach: 25%","Interested: 50%","Red-Hots: 75%","Agreements: 90%","Signed: 100%"]
    if r[19].strip() in order and order.index(r[19].strip())>order.index(c["status"] if c["status"] in order else ""):
        c["status"]=r[19].strip()

print(f"tracker companies: {len(cos)}  (rich/enriched already in dashboard: {len(rich)})")
imported=[c for n,c in cos.items() if n not in rich]
print(f"to add as new cards: {len(imported)}")
st=collections.Counter(c["status"] for c in cos.values())
for k,v in st.most_common(): print(f"   {v:>4}  {k or '(blank)'}")
json.dump({"companies":list(cos.values()),"rich":list(rich)},open("/tmp/claude-0/-home-user-ClaudeCode/3dd1bda5-ad54-5e57-ae74-cbe9fdce4115/scratchpad/dashdata.json","w"))

# ---------- emit the new DATA array ----------
def js(v): return json.dumps(v, ensure_ascii=False)

STAGEMAP={"Signed: 100%":"signed","Agreements: 90%":"verbal","Red-Hots: 75%":"redhot",
          "Interested: 50%":"interested"}

lines=[]
for name,c in cos.items():
    if name in rich: continue      # keep the enriched card already in the file
    revn=money(c["rev"]); budn=money(c["budget"])
    try: emp=int(re.sub(r'\D','',c["emp"]) or 0)
    except: emp=0
    contacts=[{"n":x["n"],"t":x["t"],"e":x["e"],"p":x["p"],"d":x["d"]} for x in c["contacts"]]
    o={"name":name,"rank":(c["rank"] or "U"),"score":(int(c["score"]) if c["score"].isdigit() else None),
       "ind":c["ind"] or "Unclassified","city":c["city"],"web":c["web"],
       "rev":c["rev"] or "—","revNum":revn,"budget":c["budget"] or "—","budNum":budn,"emp":emp,
       "signal":c["signal"] or "Imported from the FGC Master SalesTracker — not yet researched.",
       "why":c["why"] or "Imported from your existing book; needs enrichment to score.",
       "contacts":contacts}
    if c["status"] in STAGEMAP: o["stage"]=STAGEMAP[c["status"]]
    if c["status"]=="Re-approach: 25%": o["reapproach"]=True
    if c["status"]=="Not Interested: 0%": o["dead"]=True
    if c["notes"]: o["tnotes"]=c["notes"][:300]
    if c["pot"]: o["pot"]=c["pot"]
    if not contacts:
        o["research"]="No contact on file — find the owner/decision-maker."
        o["researchPhone"]=None
    lines.append("  "+js(o))

html=open(DASH).read()
s,e,block=existing_data(html)
# keep existing rich entries, append the new ones before the closing bracket
newblock=block[:-3].rstrip().rstrip(",")+",\n"+",\n".join(lines)+"\n];"
open(DASH,"w").write(html[:s]+newblock+html[e:])
print(f"\nwrote {len(lines)} new company cards into the dashboard")
