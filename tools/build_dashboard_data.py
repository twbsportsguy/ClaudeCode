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

def clean_note(s):
    """Tidy a tracker Notes cell for display. Drops the bookkeeping prefixes and
    suffixes the importers added ('[old tracker | rep TB]', the split marker) so
    the card shows what the prospect actually said, not our plumbing."""
    s=(s or "").strip()
    s=re.sub(r"\s*\|\s*split from packed legacy row [\d-]+\s*$","",s)
    s=re.sub(r"^\[(?:old tracker|legacy)\s*\|\s*rep\s*([^\]]*)\]\s*","",s)
    return s.strip(" |")

html=open(DASH).read()
s,e,block=existing_data(html)
# hand-authored, ZoomInfo-enriched cards look like {name:"X"  (no quoted key).
# Anything we generated ourselves looks like {"name": "X" — drop and rebuild those
# so re-running this script is idempotent.
rich={}
for m in re.finditer(r'\{name:"((?:[^"\\]|\\.)*)"', block):
    rich[m.group(1)]=True
keep_lines=[]
depth=0
for ln in block.split("\n"):
    if ln.strip().startswith('{"name":'): continue   # previously generated — regenerate
    keep_lines.append(ln)
block="\n".join(keep_lines)

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
        "notes":clean_note(r[21]),"pot":r[22].strip(),"dead":False,"later":False,"contacts":[]})
    if r[13].strip():
        # r[15] is Contact Email, r[16] is Contact Phone. The original ternary had
        # these inverted, so any contact WITH an address rendered their phone
        # number in the email slot (and the copy-email button copied a phone).
        email, phone = r[15].strip(), r[16].strip()
        c["contacts"].append({"n":r[13].strip(),"t":r[14].strip(),
            "e":email if "@" in email else None,
            "p":phone if phone and "@" not in phone else None,
            "d":r[18].strip().upper()=="Y",
            "tn":clean_note(r[21]),"st":r[19].strip()})
    # A "no" and a "re-approach" are sticky facts about the company, not stages to
    # be outranked. Track them on their own axis, otherwise a later `New` contact
    # row silently promotes a dead account back into the active book.
    if r[19].strip()=="Not Interested: 0%": c["dead"]=True
    if r[19].strip()=="Re-approach: 25%":   c["later"]=True
    # strongest live status wins for the company
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
    # Splitting the packed legacy rows copied one shared note onto every contact.
    # Show a note that everybody shares once, at company level; only attach a note
    # to a contact when it is genuinely theirs.
    cnotes=[x.get("tn","") for x in c["contacts"]]
    shared = cnotes[0] if cnotes and len(set(cnotes))==1 else ""
    contacts=[]
    for x in c["contacts"]:
        o={"n":x["n"],"t":x["t"],"e":x["e"],"p":x["p"],"d":x["d"]}
        if x.get("tn") and x["tn"]!=shared: o["tn"]=x["tn"][:400]
        if x.get("st"): o["st"]=x["st"]
        contacts.append(o)
    conote = shared or c["notes"]
    o={"name":name,"rank":(c["rank"] or "U"),"score":(int(c["score"]) if c["score"].isdigit() else None),
       "ind":c["ind"] or "Unclassified","city":c["city"],"web":c["web"],
       "rev":c["rev"] or "—","revNum":revn,"budget":c["budget"] or "—","budNum":budn,"emp":emp,
       "signal":c["signal"] or "Imported from the FGC Master SalesTracker — not yet researched.",
       "why":c["why"] or "Imported from your existing book; needs enrichment to score.",
       "contacts":contacts}
    if c["status"] in STAGEMAP: o["stage"]=STAGEMAP[c["status"]]
    if c["later"]: o["reapproach"]=True
    if c["dead"]:  o["dead"]=True
    if conote: o["tnotes"]=conote[:600]
    o["tstatus"]="Not Interested: 0%" if c["dead"] else ("Re-approach: 25%" if c["later"] else c["status"])
    if not o["tstatus"]: del o["tstatus"]
    if c["pot"]: o["pot"]=c["pot"]
    if not contacts:
        o["research"]="No contact on file — find the owner/decision-maker."
        o["researchPhone"]=None
    lines.append("  "+js(o))

# NB: reuse the already-filtered `block` from above — re-reading the file here
# would silently restore the generated cards we just stripped.
newblock=block.rstrip().rstrip("];").rstrip().rstrip(",")+",\n"+",\n".join(lines)+"\n];"
open(DASH,"w").write(html[:s]+newblock+html[e:])
print(f"\nwrote {len(lines)} new company cards into the dashboard")
