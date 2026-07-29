#!/usr/bin/env python3
"""Check drafts against config/voice.md before Tyler reads them.

Usage: dump the Gmail drafts to JSON (list of {subject, toRecipients,
plaintextBody}) and run:  python3 tools/audit_drafts.py drafts.json

Flags a draft when it takes the blame, reuses a banned stock phrase, runs
outside the 120-170 word budget, forgets to close on "Best,", or prints a
signature block that Gmail would then duplicate on send.
"""

import sys, re, json
BAN=["that's on us","that's on me","my fault","i dropped the thread",
     "does two jobs at once","in front of thousands of engaged locals",
     "a built-in way to entertain clients and reward your team","under one agreement",
     "caught my attention","leverage","activation","synergy","best-in-class",
     "practically neighbors","right up the road","in our backyard","just down the road",
     "rattling around","kick it around","steal 15 minutes","exclusive"]
drafts=json.load(open(sys.argv[1]))
rows=[]
for d in drafts:
    if d["subject"].startswith("[VOID") or "ATMA" in d["subject"]: continue
    b=d["plaintextBody"].replace("\r","")
    words=len(re.findall(r"\S+",b))
    paras=len([p for p in b.split("\n\n") if p.strip()])
    hits=[w for w in BAN if w in b.lower()]
    sig = "SIG!" if re.search(r"Tyler Baity|336\) 225|calendar\.app",b) else "-"
    em=b.count("—")
    rows.append((d["toRecipients"][0].split("@")[1][:22], words, paras, b.strip().endswith("Best,"),
                 sig, em, ",".join(hits) or "-", d["subject"][:42]))
print(f"{'domain':24}{'wds':>4}{'par':>4}{'Best,':>7}{'sig':>5}{'em—':>5}  {'banned':22} subject")
for r in sorted(rows):
    print(f"{r[0]:24}{r[1]:>4}{r[2]:>4}{str(r[3]):>7}{r[4]:>5}{r[5]:>5}  {r[6][:22]:22} {r[7]}")
print(f"\n{len(rows)} live drafts audited")
bad=[r for r in rows if r[6]!='-' or not r[3] or r[4]!='-' or not (110<=r[1]<=180)]
print("FLAGGED:",len(bad))
for r in bad: print("  ",r)
