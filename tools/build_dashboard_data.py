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

TODO_RE  = re.compile(r"TODO:\s*([^|\n]+)", re.I)
# e.g. "SCORE 68->81 2026-07-28: named title sponsor of the Durham Bulls season"
SCORE_RE = re.compile(r"SCORE\s*(\d{1,3})\s*(?:->|→)\s*(\d{1,3})\s*(\d{4}-\d{2}-\d{2})?\s*:?\s*([^|\n]*)", re.I)

def pull_tasks(s):
    """Tasks the pipeline wrote from a real reply (SKILL.md Step 0)."""
    return [t.strip(" .;") for t in TODO_RE.findall(s or "") if t.strip()]

def pull_scorelog(s):
    """Score movements written by the news re-scoring pass (SKILL.md Step 4b)."""
    out=[]
    for a,b,d,why in SCORE_RE.findall(s or ""):
        out.append({"from":int(a),"to":int(b),"on":d or "","why":why.strip(" .;")})
    return out

def clean_note(s):
    """Tidy a tracker Notes cell for display. Drops the bookkeeping prefixes and
    suffixes the importers added ('[old tracker | rep TB]', the split marker) so
    the card shows what the prospect actually said, not our plumbing."""
    s=(s or "").strip()
    s=re.sub(r"\s*\|\s*split from packed legacy row [\d-]+\s*$","",s)
    s=re.sub(r"^\[(?:old tracker|legacy)\s*\|\s*rep\s*([^\]]*)\]\s*","",s)
    # TODO / SCORE lines are machine-readable channels rendered as their own UI,
    # so strip them from the prose note instead of showing them twice.
    s=TODO_RE.sub("",s); s=SCORE_RE.sub("",s)
    return re.sub(r"\s{2,}"," ",s).strip(" |")

# Win/loss insights are produced by tools/analyze_conversations.py and embedded
# here so the page stays self-contained (artifacts cannot fetch anything).
try:
    INSIGHTS=json.load(open("dashboard/insights.json"))
except Exception:
    INSIGHTS=None

def _load(p, d=None):
    try: return json.load(open(p))
    except Exception: return d

def _bassclassic():
    """The Bass Classic is a separate campaign on the same schema. It is summarised
    rather than merged: scoring.md gives 8 points for a Triangle HQ, so folding a
    national tackle book into the main pipeline would rank all of it C and skew
    every partnership number."""
    try: rows=list(csv.reader(open("tracker/bass-classic.csv")))[1:]
    except Exception: return None
    stages=collections.Counter(r[19].strip() for r in rows if len(r)>19)
    return {"n":len(rows),"stages":dict(stages),
            "hold":any("HOLD" in r[20] for r in rows if len(r)>20),
            "companies":[{"co":r[3],"who":r[13],"stage":r[19],
                          "next":r[20].replace("HOLD (no ask until 2027 offer defined) — ",""),
                          "note":r[21][:300]}
                         for r in rows if len(r)>21]}

# Everything the Inbox panel needs, in one embedded object.
INBOX_RAW=_load("dashboard/inbox.json", {})
ACTIVITY =_load("dashboard/activity.json", {})
INBOX={
  "generated": INBOX_RAW.get("generated",""),
  "counts":    INBOX_RAW.get("counts",{}),
  "domains":   INBOX_RAW.get("domains",{}),
  "activity":  ACTIVITY,
  "bass":      _bassclassic(),
  # What the replies have taught us about the copy itself (reply_features.py).
  "learn":     _load("dashboard/reply-features.json", {}),
}
for k, kinds in [("dead",("bounce-hard",)), ("soft",("bounce-soft",)),
                 ("gone",("departed",)), ("ooo",("auto-ooo",)),
                 ("replies",("reply-positive","reply-negative",
                             "reply-referral","reply-neutral"))]:
    INBOX[k]=[m for m in INBOX_RAW.get("messages",[]) if m["kind"] in kinds]

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
        "notes":clean_note(r[21]),"pot":r[22].strip(),"dead":False,"later":False,
        "tasks":[],"scorelog":[],"contacts":[]})
    for t in pull_tasks(r[21]):
        if t not in c["tasks"]: c["tasks"].append(t)
    for sl in pull_scorelog(r[21]):
        if sl not in c["scorelog"]: c["scorelog"].append(sl)
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
    if c["tasks"]:    o["tasks"]=c["tasks"][:8]
    if c["scorelog"]: o["scorelog"]=c["scorelog"][-3:]
    if c["pot"]: o["pot"]=c["pot"]
    if not contacts:
        o["research"]="No contact on file — find the owner/decision-maker."
        o["researchPhone"]=None
    lines.append("  "+js(o))

# NB: reuse the already-filtered `block` from above — re-reading the file here
# would silently restore the generated cards we just stripped.
newblock=block.rstrip().rstrip("];").rstrip().rstrip(",")+",\n"+",\n".join(lines)+"\n];"
html=html[:s]+newblock+html[e:]
if INSIGHTS is not None:
    # NB: lambda replacement — a plain string would let re.sub interpret the
    # backslashes that appear inside quoted reply text as escape sequences.
    _repl="const INSIGHTS = "+js(INSIGHTS)+";\n"
    html=re.sub(r"const INSIGHTS = \{.*?\};\n", lambda m:_repl, html, count=1, flags=re.S)
_ri="const INBOX = "+js(INBOX)+";\n"
html=re.sub(r"const INBOX = \{.*?\};\n", lambda m:_ri, html, count=1, flags=re.S)
open(DASH,"w").write(html)
print(f"\nwrote {len(lines)} new company cards into the dashboard")
