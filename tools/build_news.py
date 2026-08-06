#!/usr/bin/env python3
"""Keep the dashboard's news block fresh instead of frozen.

THE BUG THIS FIXES
------------------
`dashboard/index.html` carried a hand-written `const NEWS={...}` literal. Nothing
read or wrote it, so it never changed: 10 companies against 1,243 tracker rows,
newest headline 2026-07-18, oldest 2023-02-08. Tyler noticed on 2026-08-05 that
the headlines never moved. They never could.

Worse than being stale, it *looked* current — there was no date on the block, so
a three-week-old lead story read exactly like this morning's. So this tool
stamps a `generated` date into the payload and the page shows it. A stale block
should look stale.

WHY THIS DOES NOT FETCH (same constraint as tools/fetch_inbox.py)
----------------------------------------------------------------
News comes from ZoomInfo (`enrich_news`, `search_scoops`) and the web, both of
which are MCP/tool-loop calls. A local script has no credentials for either.
So the assistant fetches in its tool loop and hands the results here as a terse
TSV; this tool does the merging, dedup, rotation and injection — none of which
should cost a single token.

ROTATION, NOT REFETCH-EVERYTHING
--------------------------------
Pulling news for every company every run would be enormous and pointless — most
companies have no news most weeks. `--targets` returns only the companies worth
asking about, prioritised so the ones in a live conversation are never stale:

  1. live pipeline (Interested / Red-Hots / Agreements / Signed) — you are
     talking to these people; walking into a call ignorant of their news is the
     expensive failure
  2. A-rank prospects
  3. anything already drafted to
  4. everything else

Within a band, longest-since-fetched first. Companies fetched inside --max-age
days are skipped entirely.

USAGE
  python3 tools/build_news.py --targets [--limit 25] [--max-age 21]
  python3 tools/build_news.py --ingest news.tsv
  python3 tools/build_news.py --inject          # -> news.json + index.html
  python3 tools/build_news.py --stats

TSV COLUMNS (tab-separated, no header, one line per ITEM):
  company  date(YYYY-MM-DD)  title  source  url  tag  [person]

  `tag` must be one of: Hiring Funding Exec M&A Product Milestone Partnership
  Marketing Expansion Risk   (anything else renders with a generic icon)
  `person` is optional — set it to a contact's exact name to star the item as
  "Your contact" on their card.
"""
import csv, json, os, re, sys, datetime, collections

CSV     = "tracker/prospects.csv"
CORPUS  = "tracker/news-corpus.jsonl"
FETCHED = "tracker/news-fetched.json"
OUT     = "dashboard/news.json"
DASH    = "dashboard/index.html"

TAGS = {"Hiring", "Funding", "Exec", "M&A", "Product", "Milestone",
        "Partnership", "Marketing", "Expansion", "Risk"}

# Statuses that mean a live conversation. These companies must never carry
# stale news — Tyler may be on a call with them.
LIVE = re.compile(r"Interested:\s*50|Red-Hots|Agreements|Signed", re.I)
DEAD = re.compile(r"Not Interested", re.I)


def load_corpus():
    items = []
    if os.path.exists(CORPUS):
        for line in open(CORPUS):
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def load_fetched():
    if os.path.exists(FETCHED):
        try:
            return json.load(open(FETCHED))
        except ValueError:
            pass
    return {}


def companies():
    """-> {name: (band, rank, status)} , band 0 = most urgent."""
    out = {}
    rows = list(csv.reader(open(CSV)))
    hdr = rows[0]
    ix = {k: n for n, k in enumerate(hdr)}
    for r in rows[1:]:
        if len(r) < len(hdr):
            continue
        name = r[ix["Company"]].strip()
        if not name:
            continue
        status = r[ix["Status"]]
        rank = r[ix["Rank"]].strip().upper()
        drafted = r[ix["Draft Created"]].strip().upper() == "Y"
        if DEAD.search(status):
            band = 9                      # ruled out: never spend a lookup
        elif LIVE.search(status):
            band = 0
        elif rank == "A":
            band = 1
        elif drafted:
            band = 2
        else:
            band = 3
        prev = out.get(name)
        if prev is None or band < prev[0]:
            out[name] = (band, rank, status)
    return out


def targets(limit, max_age):
    today = datetime.date.today()
    fetched = load_fetched()
    rows = []
    for name, (band, rank, status) in companies().items():
        if band == 9:
            continue
        f = fetched.get(name)
        age = None
        if f:
            try:
                age = (today - datetime.date.fromisoformat(f)).days
            except ValueError:
                age = None
        if age is not None and age < max_age:
            continue                       # fresh enough, skip
        rows.append((band, -(age if age is not None else 9999), name, rank,
                     status, age))
    rows.sort(key=lambda r: (r[0], r[1]))
    label = {0: "LIVE CONVERSATION", 1: "A-rank", 2: "already drafted",
             3: "not yet worked"}
    print(f"Pull news for these {min(limit, len(rows))} companies "
          f"({len(rows)} are due, showing the most urgent).\n")
    print("Use mcp__ZoomInfo__enrich_news / search_scoops, plus a web search "
          "for sponsorship,\nevent or partnership spend. Then write ONE TSV:")
    print("  company<TAB>date<TAB>title<TAB>source<TAB>url<TAB>tag[<TAB>person]")
    print(f"  tag must be one of: {' '.join(sorted(TAGS))}\n")
    for band, _, name, rank, status, age in rows[:limit]:
        seen = "never fetched" if age is None else f"{age}d since last fetch"
        print(f"  [{label[band]:<17}] {name}   ({rank or '-'}, {seen})")
    if not rows:
        print("  nothing due — every company was fetched within "
              f"{max_age} days.")
    print("\nCompanies with NO news found must still be recorded, so they are "
          "not\nre-queried tomorrow. Pass them as a line with an empty title:"
          "\n  Acme Corp<TAB><TAB><TAB><TAB><TAB>")


def ingest(path):
    corpus = load_corpus()
    # Dedup key: a URL is the strongest identity; fall back to company+title
    # because press-release aggregators reprint the same story on new URLs.
    seen = {(i["company"], i.get("u") or i.get("t", "")) for i in corpus}
    fetched = load_fetched()
    today = datetime.date.today().isoformat()

    added = empty = bad = 0
    for ln in open(path):
        ln = ln.rstrip("\n")
        if not ln.strip():
            continue
        p = ln.split("\t")
        p += [""] * (7 - len(p))
        company, d, t, s, u, tag, person = [x.strip() for x in p[:7]]
        if not company:
            continue
        fetched[company] = today          # record the lookup either way
        if not t:
            empty += 1                    # "checked, found nothing"
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            print(f"  skipped (bad date {d!r}): {company} — {t[:50]}")
            bad += 1
            continue
        if tag and tag not in TAGS:
            print(f"  note: tag {tag!r} is not one of the known tags, it will "
                  f"render with a generic icon ({company})")
        key = (company, u or t)
        if key in seen:
            continue
        seen.add(key)
        corpus.append({"company": company, "d": d, "t": t, "s": s, "u": u,
                       "tag": tag or "Milestone",
                       **({"person": person} if person else {}),
                       "first_seen": today})
        added += 1

    with open(CORPUS, "w") as fh:
        for i in sorted(corpus, key=lambda x: (x["company"], x["d"]),
                        reverse=True):
            fh.write(json.dumps(i) + "\n")
    json.dump(fetched, open(FETCHED, "w"), indent=1, sort_keys=True)

    print(f"ingested: {added} new item(s), {empty} company/companies checked "
          f"with no news, {bad} skipped")
    print(f"  corpus now {len(corpus)} items across "
          f"{len(set(i['company'] for i in corpus))} companies")
    print(f"  {len(fetched)} companies have a recorded fetch date")


def build_payload():
    by = collections.defaultdict(list)
    for i in load_corpus():
        item = {k: i[k] for k in ("d", "t", "s", "u", "tag") if k in i}
        if "person" in i:
            item["person"] = i["person"]
        by[i["company"]].append(item)
    for k in by:
        by[k].sort(key=lambda x: x["d"], reverse=True)
    return dict(sorted(by.items()))


def inject():
    payload = build_payload()
    today = datetime.date.today().isoformat()
    os.makedirs("dashboard", exist_ok=True)
    json.dump({"generated": today, "news": payload}, open(OUT, "w"), indent=1)

    html = open(DASH).read()
    # Same technique build_dashboard_data.py uses for INBOX/INSIGHTS: replace
    # the inlined literal. The page is a self-contained artifact under a strict
    # CSP, so it cannot fetch news.json at runtime — the data has to be baked in.
    lit = "const NEWS=" + json.dumps(payload, ensure_ascii=False) + ";\n"
    new, n = re.subn(r"const NEWS=\{.*?\};\n", lambda m: lit, html,
                     count=1, flags=re.S)
    if not n:
        print(f"FAILED: no `const NEWS={{...}};` literal found in {DASH}. "
              f"Nothing written — the dashboard is unchanged.")
        return 1
    # Stamp the refresh date so a stale block looks stale. This is the whole
    # reason the old one went unnoticed for weeks.
    new, m = re.subn(r'const NEWS_GENERATED="[^"]*";\n',
                     lambda _: f'const NEWS_GENERATED="{today}";\n', new,
                     count=1)
    if not m:
        new = new.replace(lit, lit + f'const NEWS_GENERATED="{today}";\n', 1)
    open(DASH, "w").write(new)

    items = sum(len(v) for v in payload.values())
    print(f"wrote {OUT} and injected into {DASH}")
    print(f"  {items} items across {len(payload)} companies, generated {today}")
    return 0


def stats():
    corpus, fetched = load_corpus(), load_fetched()
    total = len(companies())
    print(f"corpus  : {len(corpus)} items / "
          f"{len(set(i['company'] for i in corpus))} companies")
    print(f"coverage: {len(fetched)}/{total} companies ever looked up "
          f"({100*len(fetched)/total if total else 0:.1f}%)")
    if corpus:
        ds = sorted(i["d"] for i in corpus)
        print(f"headlines: {ds[0]} -> {ds[-1]}")
    if os.path.exists(OUT):
        print(f"{OUT} generated {json.load(open(OUT)).get('generated','?')}")
    else:
        print(f"{OUT} does not exist yet — run --inject")


def main():
    a = sys.argv[1:]
    def opt(flag, default, cast=int):
        return cast(a[a.index(flag) + 1]) if flag in a else default
    if "--stats" in a:
        return stats()
    if "--ingest" in a:
        return ingest(a[a.index("--ingest") + 1])
    if "--inject" in a:
        return sys.exit(inject())
    targets(opt("--limit", 25), opt("--max-age", 21))


if __name__ == "__main__":
    main()
