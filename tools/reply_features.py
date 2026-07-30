#!/usr/bin/env python3
"""Work out which email features actually earn replies, and write them down.

`analyze_inbox.py` answers "what came back". `analyze_conversations.py` answers
"what are prospects saying". This answers the one that changes the next email:
**of everything we varied, what correlates with getting answered at all?**

The output is not a report for its own sake. It writes `config/what-works.md`,
which `.claude/skills/prospect/SKILL.md` Step 7 reads before drafting and
`tools/audit_drafts.py` enforces afterwards. That is the whole point: a finding
here becomes a constraint on the next batch without anyone remembering to
apply it.

  python3 tools/reply_features.py sweep.json [more.json ...]
        [--drafts drafts.json ...] [--csv tracker/prospects.csv]
        [--corpus tracker/email-corpus.jsonl] [--write]

`--write` is what updates `config/what-works.md`, the corpus, and the
dashboard feed. Without it, nothing on disk changes.

WHAT IT WILL NOT DO
-------------------
It will not invent a rule from three replies. Every claim is gated on sample
size and on Fisher's exact test with a Benjamini-Hochberg correction, because
roughly thirty features are tested at once and at p<0.10 you would otherwise
manufacture three confident lies per run. Features that fail the gate are
printed as "watching" with their current counts, so the evidence accumulates
in the open rather than being silently discarded.

It also separates COPY features (what we wrote — changeable) from AUDIENCE
features (who we wrote to — not a writing lesson). A copy feature that only
looks good because it was used on the industry that always replies is worse
than useless, so any surviving copy rule is re-tested inside the audience
strata and marked "confounded" if the effect disappears.

THE BODY PROBLEM
----------------
Gmail thread search returns a ~180-character snippet, not the body. Subject and
opening line are therefore always analysable; word count, CTA shape and the
rest are only analysable for messages whose full text we have. So every full
body this tool ever sees — from a drafts dump or an enriched thread — is
appended to `tracker/email-corpus.jsonl` and reused forever after. Tier 2
coverage grows on its own as runs accumulate; nothing needs re-fetching.
"""
import sys, os, re, json, csv, math, html, collections, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_inbox import load_threads, classify, campaign, OURS

TRACK  = "tracker/prospects.csv"
CORPUS = "tracker/email-corpus.jsonl"
GUIDE  = "config/what-works.md"
FEED   = "dashboard/reply-features.json"

MIN_N   = 12    # per arm, before a feature value is allowed a verdict
ALPHA   = 0.10  # raw Fisher p
FDR_Q   = 0.20  # Benjamini-Hochberg; exploratory, and labelled as such


# ------------------------------------------------------------------ stats
def wilson(k, n, z=1.645):
    """90% Wilson score interval. Normal-approximation intervals put the
    lower bound below zero at these sample sizes, which reads as certainty
    where there is none."""
    if not n: return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def fisher(a, b, c, d):
    """Two-sided Fisher's exact test on [[a,b],[c,d]].

    Exact rather than chi-square because half these cells are single digits,
    which is exactly where the chi-square approximation reports significance
    that is not there.
    """
    n = a + b + c + d
    if not n: return 1.0
    row1, col1 = a + b, a + c
    def prob(x):
        return (math.comb(row1, x) * math.comb(n - row1, col1 - x)) / math.comb(n, col1)
    obs = prob(a)
    lo, hi = max(0, col1 - (n - row1)), min(row1, col1)
    # Sum every table at least as extreme as the observed one. The 1e-9 slack
    # keeps floating-point error from dropping the observed table itself.
    return min(1.0, sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= obs * (1 + 1e-9)))


def bh(pvals, q=FDR_Q):
    """Benjamini-Hochberg. Returns the p-value threshold that holds the false
    discovery rate at q, or 0 if nothing survives."""
    if not pvals: return 0.0
    s = sorted(pvals)
    m, thresh = len(s), 0.0
    for i, p in enumerate(s, 1):
        if p <= i / m * q: thresh = p
    return thresh


# --------------------------------------------------------------- features
GREETING = re.compile(r"^\s*(hi|hello|hey|good (?:morning|afternoon|evening))\b", re.I)
DAYS     = re.compile(r"\b(monday|tuesday|wednesday|thursday|friday)\b", re.I)


def clean(s):
    """Snippets arrive HTML-escaped (`We&#39;re`), and an unescaped apostrophe
    silently breaks every regex below that contains one."""
    return html.unescape(s or "").replace("’", "'").replace("\r", "")


def strip_greeting(text):
    t = clean(text).lstrip()
    t = re.sub(r"^(hi|hello|hey|good (?:morning|afternoon|evening))[\s,]+[A-Z][a-z]+[\s,-]*", "", t, flags=re.I)
    t = re.sub(r"^[A-Z][a-z]+,\s*", "", t)
    return t.strip()


def bucket(v, edges, labels):
    for e, l in zip(edges, labels):
        if v < e: return l
    return labels[-1]


def subject_features(subj, company):
    s = clean(subj)
    w = len(s.split())
    f = {
        "subj_words":       bucket(w, [5, 8], ["1-4", "5-7", "8+"]),
        "subj_names_finley": "yes" if re.search(r"finley|carolina's home course", s, re.I) else "no",
        "subj_em_dash":     "yes" if "—" in s else "no",
        "subj_question":    "yes" if s.rstrip().endswith("?") else "no",
    }
    if company:
        # Only the distinctive part of the name counts. "Group", "Inc" and
        # "Company" appear in half the subjects for reasons unrelated to
        # personalisation.
        key = re.sub(r"\b(inc|llc|corp|corporation|company|co|group|holdings|the|of|and)\b", " ",
                     company, flags=re.I).split()
        f["subj_names_company"] = "yes" if any(len(k) > 3 and k.lower() in s.lower() for k in key) else "no"
    return f


def opening_features(body_or_snippet, company):
    t = strip_greeting(body_or_snippet)
    first = re.split(r"(?<=[.?!])\s", t)[0] if t else ""
    head = " ".join(t.split()[:14]).lower()
    f = {
        "greeting":       "hi-firstname" if GREETING.match(clean(body_or_snippet)) else "bare-name",
        "open_question":  "yes" if first.rstrip().endswith("?") else "no",
        "open_first_sentence": bucket(len(first.split()), [12, 22], ["short", "medium", "long"]),
        # An opening about them outperforms an opening about us in every study
        # of cold email ever run; worth checking whether it holds here.
        "open_about":     "us" if re.match(r"(i |we |my |our |finley)", head) else "them",
    }
    if company:
        key = [k for k in re.sub(r"\b(inc|llc|corp|corporation|company|co|group|holdings|the|of|and)\b",
                                 " ", company, flags=re.I).split() if len(k) > 3]
        f["open_names_them"] = "yes" if ("your" in head or any(k.lower() in head for k in key)) else "no"
    return f


def body_features(body):
    """Tier 2. Only computable when the full text is known."""
    b = clean(body)
    words = re.findall(r"\S+", b)
    n = len(words)
    paras = [p for p in b.split("\n\n") if p.strip()]
    you = len(re.findall(r"\b(you|your|yours)\b", b, re.I))
    we  = len(re.findall(r"\b(we|our|ours|us|i|my)\b", b, re.I))
    return {
        "body_words":    bucket(n, [110, 140, 170], ["<110", "110-139", "140-169", "170+"]),
        "body_paras":    bucket(len(paras), [5, 7], ["<5", "5-6", "7+"]),
        "you_we_ratio":  bucket(you / max(we, 1), [0.8, 1.4], ["we-heavy", "balanced", "you-heavy"]),
        "three_options": "yes" if re.search(r"could (?:mean|be)\b.*\bor\b", b, re.I | re.S) else "no",
        "names_days":    "yes" if DAYS.search(b) else "no",
        "cta_minutes":   "yes" if re.search(r"\b\d+ minutes\b", b, re.I) else "no",
        "cta_shape":     ("question" if re.search(r"(worth|would|is)[^.?!]*\?", b, re.I)
                          else "statement"),
        "mentions_tiers": "yes" if re.search(r"fixed (?:sponsorship )?tiers|rather than.*tiers", b, re.I) else "no",
        "drive_time":    "yes" if re.search(r"\bminutes (?:from|away)|drive|chapel hill\b", b, re.I) else "no",
        "dental_angle":  "yes" if re.search(r"dental school|prospective dental", b, re.I) else "no",
        "em_dashes":     bucket(b.count("—"), [1, 3], ["0", "1-2", "3+"]),
    }


SENIORITY = [
    (r"owner|founder|principal|partner\b", "owner"),
    (r"\b(ceo|cfo|coo|cmo|chief|president)\b", "c-level"),
    (r"\bvp\b|vice president", "vp"),
    (r"general manager|\bgm\b", "gm"),
    (r"director|head of", "director"),
    (r"manager|supervisor|lead\b", "manager"),
]


def audience_features(row):
    """Who we wrote to. Reported alongside the copy features because it is
    genuinely useful targeting information — but never mixed into the writing
    rules, because "email dealerships" is not a lesson about how to write."""
    if not row: return {}
    title = (row[14] if len(row) > 14 else "") or ""
    sen = next((l for p, l in SENIORITY if re.search(p, title, re.I)), "other")
    try: emp = int(re.sub(r"\D", "", row[9] or "0") or 0)
    except ValueError: emp = 0
    city = (row[5] or "").lower()
    return {
        "aud_industry":   (row[4] or "unknown")[:26],
        "aud_rank":       (row[1] or "?").strip()[:1],
        "aud_seniority":  sen,
        "aud_employees":  bucket(emp, [50, 250, 1000], ["<50", "50-249", "250-999", "1000+"]),
        "aud_triangle":   "yes" if any(c in city for c in
                          ("chapel hill", "raleigh", "durham", "cary", "carrboro",
                           "morrisville", "apex", "hillsborough")) else "no",
    }


COPY_PREFIX = ("subj_", "open_", "body_", "you_we", "three_", "names_days",
               "cta_", "mentions_", "drive_", "dental_", "em_dashes", "greeting")


def is_copy(feat):
    return feat.startswith(COPY_PREFIX)


# ------------------------------------------------------------------ build
MATURITY = 3     # days an email needs before "no reply" means anything
BLAST_N  = 6     # recipients sharing one subject before it is a mail merge


def attempts(threads, by_email, corpus, today=None):
    """One record per outbound email that had a chance to be answered.

    A thread, not a message, is the unit: the reply belongs to the thread, and
    counting per message would credit a reply to Tyler's own follow-up as well
    as to the original. Bounced sends are dropped entirely — an email that
    never arrived cannot teach us anything about what earns an answer, and
    leaving it in the denominator makes every feature look worse in proportion
    to how stale its contact list was.
    """
    today = today or datetime.date.today()
    out = []
    for th in threads:
        msgs = sorted(th.get("messages") or [], key=lambda m: m.get("date") or "")
        camp = campaign("\n".join(f"{m.get('subject','')}\n{m.get('snippet','')}\n"
                                  f"{m.get('plaintextBody','')}" for m in msgs))
        sent_to, sent_subj = [], []
        for m in msgs:
            if "SENT" in set(m.get("labelIds") or []) or (m.get("sender") or "").lower() in OURS:
                sent_to.extend(a.lower() for a in (m.get("toRecipients") or []))
                if m.get("subject"):
                    sent_subj.append(re.sub(r"^re:\s*", "", m["subject"], flags=re.I))

        first = next((m for m in msgs if "SENT" in set(m.get("labelIds") or [])
                      or (m.get("sender") or "").lower() in OURS), None)
        if not first or not (first.get("toRecipients") or []): continue
        addr = first["toRecipients"][0].lower()
        row  = by_email.get(addr)
        # sync_activity.py indexes each address to a LIST of rows; this tool
        # indexes it to one row, and a row is itself a list. Unwrapping on
        # `isinstance(row, list)` therefore grabbed the row's first CELL and
        # then read characters out of the date string — company came back as
        # "6". Only unwrap when the first element is itself a row.
        if row and isinstance(row[0], list): row = row[0]

        # Tyler's inbox carries his day job and two other campaigns. Only mail
        # we can tie to a campaign or to a tracker row is outreach.
        if camp == "unknown" and not row: continue

        kinds = [classify(m, sent_to, sent_subj)[0] for m in msgs if m is not first]
        if any(k == "bounce-hard" for k in kinds): continue
        reps = [k for k in kinds if k.startswith("reply-")]

        mid  = first.get("id") or f"{addr}:{(first.get('date') or '')[:10]}"
        body = corpus.get(mid, {}).get("body") or first.get("plaintextBody") or ""
        d = first.get("date") or ""
        try:
            # Gmail stamps UTC; Tyler and every prospect here are Eastern, so a
            # 7am send would otherwise file itself under "pre-dawn".
            dt = datetime.datetime.fromisoformat(d.replace("Z", "+00:00")) - datetime.timedelta(hours=4)
        except ValueError:
            dt = None

        # An email sent yesterday has not failed to get a reply; it has not yet
        # had the chance. Counting it as a miss drags every rate down in
        # proportion to how recently that feature was introduced — which is
        # exactly backwards, since new features are always the newest sends.
        try:
            age = (today - datetime.date.fromisoformat(d[:10])).days
        except ValueError:
            age = 999

        out.append({
            "id": mid, "date": d[:10], "to": addr, "campaign": camp,
            "subject": clean(first.get("subject")),
            "body": clean(body), "snippet": clean(first.get("snippet")),
            "company": row[3] if row else "", "row": row,
            "first_touch": msgs[0] is first,
            "age": age, "mature": age >= MATURITY,
            "replied": bool(reps),
            "sentiment": (("positive" if any(k == "reply-positive" for k in reps) else
                           "referral" if any(k == "reply-referral" for k in reps) else
                           "negative" if any(k == "reply-negative" for k in reps) else "neutral")
                          if reps else ""),
            "dow": dt.strftime("%a") if dt else "?",
            "hour": (bucket(dt.hour, [9, 12, 15], ["before-9", "9-12", "12-3", "after-3"])
                     if dt else "?"),
        })
    return out


def cohorts(acts):
    """Split the corpus into things that are not comparable to each other.

    Mixing these is not a rounding error, it inverts the answer. Run blind on
    2026-07-30 this tool reported "naming Finley in the subject lifts replies
    from 0% to 97%" — which was really "renewal emails to companies that are
    already partners get answered, and cold emails to strangers mostly don't".
    Both cohorts named Finley. Only one of them was cold.

      blast     one subject mail-merged to BLAST_N+ recipients. Here these are
                the annual renewal blasts to the existing partner book, so
                their reply rate says nothing about prospecting.
      warm      the prospect wrote first, or we are mid-thread with them.
      cold      in the tracker, first touch, individually written. The only
                cohort a drafting rule may be learned from.
      untracked no tracker row — Tyler's day job and event logistics.
    """
    subj = collections.Counter(
        re.sub(r"^re:\s*", "", a["subject"], flags=re.I).strip().lower() for a in acts)
    for a in acts:
        key = re.sub(r"^re:\s*", "", a["subject"], flags=re.I).strip().lower()
        a["blast_size"] = subj[key]
        if not a["row"]:                             a["cohort"] = "untracked"
        elif subj[key] >= BLAST_N:                   a["cohort"] = "blast"
        elif not a["first_touch"] or key != a["subject"].strip().lower():
            a["cohort"] = "warm"
        else:                                        a["cohort"] = "cold"
    return acts


def usable(a):
    """Reject records that carry no observable copy.

    The 2026-07-29 dump contained 48 sends stamped with an identical timestamp,
    no subject and no snippet. Whatever produced them, they describe no email —
    and because they never reply, leaving them in hands every feature they lack
    a free 0% arm to beat.
    """
    return bool(a["subject"].strip()) and bool((a["body"] or a["snippet"]).strip())


def featurize(a):
    f = {}
    f.update(subject_features(a["subject"], a["company"]))
    f.update(opening_features(a["body"] or a["snippet"], a["company"]))
    if a["body"]:
        f.update(body_features(a["body"]))
    f.update(audience_features(a["row"]))
    f["send_dow"]  = a["dow"]
    f["send_hour"] = a["hour"]
    return f


# ------------------------------------------------------------------- main
def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def load_corpus(path):
    c = {}
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line:
                r = json.loads(line)
                c[r["id"]] = r
    return c


def main():
    srcs = [a for a in sys.argv[1:] if a.endswith(".json") and
            sys.argv[sys.argv.index(a) - 1] not in ("--csv", "--corpus")]
    track   = arg("--csv", TRACK)
    cpath   = arg("--corpus", CORPUS)
    write   = "--write" in sys.argv
    dpaths  = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--drafts"]
    srcs    = [s for s in srcs if s not in dpaths]

    rows = list(csv.reader(open(track)))
    by_email = {}
    for r in rows[1:]:
        if len(r) > 15 and "@" in r[15]:
            by_email.setdefault(r[15].strip().lower(), r)
        for a in re.findall(r"DEAD-EMAIL:\s*([\w.+-]+@[\w.-]+)", r[21] if len(r) > 21 else ""):
            by_email.setdefault(a.lower(), r)

    corpus = load_corpus(cpath)

    threads = []
    for s in srcs: threads.extend(load_threads(s))

    # Any full body we are handed gets banked, whether it came from a thread
    # dump or a drafts dump, so the next run starts with more than this one had.
    for th in threads:
        for m in th.get("messages") or []:
            if m.get("plaintextBody") and ("SENT" in set(m.get("labelIds") or [])
                                           or (m.get("sender") or "").lower() in OURS):
                corpus[m["id"]] = {"id": m["id"], "date": (m.get("date") or "")[:10],
                                   "to": (m.get("toRecipients") or [""])[0].lower(),
                                   "subject": m.get("subject", ""),
                                   "body": m["plaintextBody"], "src": "sent"}
    for dp in dpaths:
        for d in json.load(open(dp)):
            if not d.get("plaintextBody"): continue
            key = d.get("id") or f"draft:{(d.get('toRecipients') or [''])[0]}"
            corpus[key] = {"id": key, "date": (d.get("date") or "")[:10],
                           "to": (d.get("toRecipients") or [""])[0].lower(),
                           "subject": d.get("subject", ""),
                           "body": d["plaintextBody"], "src": "draft"}
    # Drafts are keyed by draft id, sends by message id — the same email under
    # two names. Re-index bodies by recipient so a banked draft body attaches to
    # its send once Tyler hits send.
    by_to = {(v["to"], re.sub(r"^re:\s*", "", v.get("subject", ""), flags=re.I).strip().lower()): v
             for v in corpus.values() if v.get("body")}

    acts = cohorts(attempts(threads, by_email, corpus))
    for a in acts:
        # Match a banked body to a send on recipient AND subject. Recipient
        # alone attaches a still-pending draft to an older send — and a draft
        # is pending precisely because that person has not replied, so it would
        # feed every body feature a guaranteed non-replier.
        if not a["body"]:
            k = (a["to"], re.sub(r"^re:\s*", "", a["subject"], flags=re.I).strip().lower())
            if k in by_to: a["body"] = clean(by_to[k]["body"])

    W = print
    W("=" * 76); W("REPLY-FEATURE ANALYSIS"); W("=" * 76)

    # ---- cohorts, before any statistics. These are not comparable to each
    # other and the whole analysis is wrong if they are pooled.
    W(f"\n  {'cohort':22}{'n':>5}{'mature':>8}{'replied':>9}{'rate':>7}")
    for name in ("cold", "warm", "blast", "untracked"):
        g = [a for a in acts if a["cohort"] == name and a["campaign"] != "bass-classic"]
        m = [a for a in g if a["mature"]]
        r = sum(a["replied"] for a in m)
        W(f"  {name:22}{len(g):>5}{len(m):>8}{r:>9}{(r/len(m) if m else 0):>7.0%}")
    bc = [a for a in acts if a["campaign"] == "bass-classic"]
    W(f"  {'bass-classic (held)':22}{len(bc):>5}{'-':>8}{'-':>9}{'-':>7}")

    dropped = [a for a in acts if not usable(a)]
    part = [a for a in acts if a["cohort"] == "cold" and a["campaign"] != "bass-classic"
            and usable(a)]
    fresh = [a for a in part if not a["mature"]]
    part  = [a for a in part if a["mature"]]

    if dropped:
        W(f"\n  dropped {len(dropped)} record(s) with no subject or body text "
          f"(nothing to measure)")
    if fresh:
        W(f"  holding {len(fresh)} send(s) under {MATURITY} days old — too fresh "
          f"for silence to mean no")

    tot, rep = len(part), sum(a["replied"] for a in part)
    base = rep / tot if tot else 0
    lo, hi = wilson(rep, tot)
    W(f"\n  LEARNING FROM: {tot} mature cold 1:1 emails, {rep} answered "
      f"= {base:.0%}  (90% CI {lo:.0%}-{hi:.0%})")
    W(f"  full body known for {sum(1 for a in part if a['body'])}/{tot} "
      f"— tier-2 features are limited to those")
    sent_c = collections.Counter(a["sentiment"] for a in part if a["replied"])
    if sent_c:
        W("  of the replies: " + ", ".join(f"{k} {v}" for k, v in sent_c.most_common()))

    # A cold prospecting rate this high means warm mail is still mixed in.
    # Published cold-email benchmarks sit in the 1-10% band; renewal mail to an
    # existing book sits near 100%, and the gap between them is what this guard
    # is watching for.
    suspect = tot >= 20 and base > 0.35
    if suspect:
        W(f"\n  !! {base:.0%} is not a cold-outreach reply rate. The cohort still")
        W("     contains warm or renewal mail. Rules will not be written; fix the")
        W("     input or pass --force if you are certain.")

    # ---- tabulate
    table = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for a in part:
        for feat, val in featurize(a).items():
            cell = table[feat][val]
            cell[0] += 1
            cell[1] += a["replied"]

    tests = []
    for feat, vals in table.items():
        # A feature with one observed value varied nothing and can prove nothing.
        if len(vals) < 2: continue
        fn = sum(v[0] for v in vals.values())
        fr = sum(v[1] for v in vals.values())
        for val, (n, k) in vals.items():
            other_n, other_k = fn - n, fr - k
            if n < MIN_N or other_n < MIN_N:
                tests.append(dict(feat=feat, val=val, n=n, k=k, rate=k / n if n else 0,
                                  p=1.0, lift=0, verdict="watching",
                                  ci=wilson(k, n), base=other_k / other_n if other_n else 0))
                continue
            p = fisher(k, n - k, other_k, other_n - other_k)
            r0 = other_k / other_n
            tests.append(dict(feat=feat, val=val, n=n, k=k, rate=k / n, p=p,
                              lift=(k / n) - r0, verdict="", ci=wilson(k, n), base=r0))

    live = [t for t in tests if t["verdict"] != "watching"]
    cut = bh([t["p"] for t in live])
    for t in live:
        if t["p"] <= cut and abs(t["lift"]) >= 0.05:
            t["verdict"] = "WORKS" if t["lift"] > 0 else "HURTS"
        elif t["p"] <= ALPHA and abs(t["lift"]) >= 0.05:
            t["verdict"] = "suggestive"
        else:
            t["verdict"] = "no effect"

    # ---- confounding: does a copy effect survive inside the industry it was
    # mostly used on? If the whole effect is "we used this phrasing on car
    # dealers and car dealers reply", it is a targeting fact wearing a
    # writing-rule costume.
    for t in [x for x in live if x["verdict"] in ("WORKS", "HURTS") and is_copy(x["feat"])]:
        strat, kept = collections.defaultdict(lambda: [0, 0, 0, 0]), []
        for a in part:
            f = featurize(a)
            if t["feat"] not in f: continue
            g = f.get("aud_industry", "unknown")
            hit = f[t["feat"]] == t["val"]
            s = strat[g]
            s[0 if hit else 2] += 1
            s[1 if hit else 3] += a["replied"]
        for g, (n1, k1, n0, k0) in strat.items():
            if n1 >= 6 and n0 >= 6: kept.append((k1 / n1) - (k0 / n0))
        t["strata"] = len(kept)
        # Effect must point the same way in most strata where it can be seen.
        agree = sum(1 for d in kept if (d > 0) == (t["lift"] > 0))
        t["confounded"] = bool(kept) and agree <= len(kept) / 2

    # ---- report
    order = {"WORKS": 0, "HURTS": 1, "suggestive": 2, "no effect": 3, "watching": 4}
    for section, keep in (("COPY — what we wrote (these become drafting rules)", is_copy),
                          ("AUDIENCE — who we wrote to (targeting, not writing)",
                           lambda f: f.startswith("aud_")),
                          ("TIMING", lambda f: f.startswith("send_"))):
        W(f"\n{'-'*76}\n{section}\n{'-'*76}")
        W(f"  {'feature = value':44}{'n':>4}{'rep':>5}{'rate':>7}{'vs':>7}  verdict")
        sel = sorted([t for t in tests if keep(t["feat"])],
                     key=lambda t: (order[t["verdict"]], -abs(t["lift"]), t["feat"]))
        for t in sel:
            if t["verdict"] == "watching" and t["n"] < 5: continue
            mark = " (confounded)" if t.get("confounded") else ""
            v = "—" if t["verdict"] == "watching" else f"{t['lift']:+.0%}"
            W(f"  {t['feat']+' = '+str(t['val']):44}{t['n']:>4}{t['k']:>5}"
              f"{t['rate']:>7.0%}{v:>7}  {t['verdict']}{mark}")

    # ---- what the batch still in flight will be able to answer.
    # A feature only becomes answerable if the batch actually varied it. Sending
    # 89 emails that all do the same thing measures nothing about that thing, and
    # it is far cheaper to notice that now than after waiting a week for replies.
    if fresh:
        W(f"\n{'-'*76}\nIN FLIGHT — {len(fresh)} email(s) awaiting a verdict "
          f"(readable from {min(a['date'] for a in fresh)} + {MATURITY}d)\n{'-'*76}")
        spread = collections.defaultdict(collections.Counter)
        for a in fresh:
            for feat, val in featurize(a).items():
                if is_copy(feat): spread[feat][val] += 1
        W("  these comparisons are live — both arms are populated:")
        answerable = 0
        for feat, c in sorted(spread.items()):
            if len(c) < 2: continue
            small = min(c.values())
            if small < MIN_N: continue
            answerable += 1
            W(f"    {feat:24} " + "  ".join(f"{v}={n}" for v, n in c.most_common()))
        if not answerable:
            W("    none — every draft in this batch made the same choices, so no")
            W("    copy feature can be tested against it")
        # A feature seen on only a handful of records is not "never varied" —
        # its body simply is not banked yet. Saying otherwise sends you off to
        # vary something that is in fact already varied.
        thin  = [f for f, c in sorted(spread.items())
                 if sum(c.values()) < len(fresh) / 2]
        stuck = [f for f, c in sorted(spread.items())
                 if len(c) < 2 and sum(c.values()) >= len(fresh) / 2]
        if stuck:
            W(f"\n  never varied, so unanswerable from this batch:\n"
              f"    {', '.join(stuck)}")
        if thin:
            W(f"\n  body not banked for most of this batch, so untestable "
              f"until it is:\n    {', '.join(thin)}")

    rules = [t for t in live if t["verdict"] in ("WORKS", "HURTS")
             and is_copy(t["feat"]) and not t.get("confounded")]
    W(f"\n{'-'*76}\nRULES EARNED ({len(rules)})\n{'-'*76}")
    if not rules:
        W("  None yet. Nothing cleared the sample-size and multiple-comparison")
        W("  gates, which at this corpus size is the expected and correct answer.")
        W("  The 'watching' rows above are the evidence accumulating; re-run after")
        W("  the next few batches land.")
    for t in sorted(rules, key=lambda t: -abs(t["lift"])):
        W(f"  {t['feat']} = {t['val']}: {t['rate']:.0%} vs {t['base']:.0%} "
          f"(n={t['n']}, p={t['p']:.3f})")

    if suspect and "--force" not in sys.argv:
        rules = []
        W("\n  (rules suppressed by the cold-rate guard)")

    if write:
        write_guide(rules, tests, part, base, tot, rep, fresh)
        with open(cpath, "w") as fh:
            for v in corpus.values(): fh.write(json.dumps(v) + "\n")
        os.makedirs(os.path.dirname(FEED), exist_ok=True)
        spread = collections.defaultdict(collections.Counter)
        for a in fresh:
            for feat, val in featurize(a).items():
                if is_copy(feat): spread[feat][val] += 1
        json.dump({"generated": datetime.date.today().isoformat(),
                   "sent": tot, "replied": rep, "baseline": base,
                   "bodies_known": sum(1 for a in part if a["body"]),
                   "maturity_days": MATURITY,
                   "cohorts": {name: {
                       "n": len([a for a in acts if a["cohort"] == name
                                 and a["campaign"] != "bass-classic"]),
                       "replied": sum(a["replied"] for a in acts
                                      if a["cohort"] == name and a["mature"]
                                      and a["campaign"] != "bass-classic")}
                       for name in ("cold", "warm", "blast", "untracked")},
                   "inflight": {"n": len(fresh),
                                "since": min((a["date"] for a in fresh), default=""),
                                "spread": {f: dict(c) for f, c in spread.items()}},
                   "tests": [{k: v for k, v in t.items() if k != "ci"} | {"ci": list(t["ci"])}
                             for t in tests],
                   "rules": [f"{t['feat']}={t['val']}" for t in rules]},
                  open(FEED, "w"), indent=1)
        W(f"\nWrote {GUIDE}, {cpath} ({len(corpus)} bodies banked), {FEED}")
    else:
        W("\n(dry run — pass --write to update config/what-works.md and the corpus)")


PHRASING = {
    "subj_names_finley":  ("name Finley in the subject", "leave Finley out of the subject"),
    "subj_names_company": ("name the prospect's company in the subject", "keep the company out of the subject"),
    "subj_em_dash":       ("use an em dash in the subject", "avoid em dashes in the subject"),
    "subj_question":      ("end the subject with a question", "avoid question-mark subjects"),
    "subj_words":         ("keep the subject to {v} words", "avoid {v}-word subjects"),
    "greeting":           ("open with a {v} greeting", "avoid the {v} greeting"),
    "open_question":      ("open on a question", "avoid opening on a question"),
    "open_about":         ("open about {v}", "avoid opening about {v}"),
    "open_names_them":    ("name them in the first line", "avoid naming them in the first line"),
    "open_first_sentence": ("keep the first sentence {v}", "avoid a {v} first sentence"),
    "body_words":         ("hold the body at {v} words", "avoid bodies at {v} words"),
    "body_paras":         ("use {v} paragraphs", "avoid {v} paragraphs"),
    "you_we_ratio":       ("write {v}", "avoid writing {v}"),
    "three_options":      ("offer three concrete uses", "drop the three-option list"),
    "names_days":         ("name specific days in the ask", "leave days out of the ask"),
    "cta_minutes":        ("put a minute count on the ask", "drop the minute count"),
    "cta_shape":          ("close with a {v}", "avoid closing with a {v}"),
    "mentions_tiers":     ("say the packages aren't fixed tiers", "drop the fixed-tiers line"),
    "drive_time":         ("mention the drive time", "drop the drive-time line"),
    "dental_angle":       ("keep the dental-school line", "drop the dental-school line"),
    "em_dashes":          ("use {v} em dashes", "avoid {v} em dashes"),
}


def phrase(t):
    pos, neg = PHRASING.get(t["feat"], ("{f} = {v}", "not {f} = {v}"))
    s = (pos if t["verdict"] == "WORKS" else neg)
    if t["verdict"] == "WORKS" and t["val"] in ("no", "us"):
        s = neg   # "WORKS when the value is 'no'" is a rule to NOT do the thing
    return s.format(v=t["val"], f=t["feat"])


def write_guide(rules, tests, acts, base, tot, rep, fresh=()):
    """Generate config/what-works.md.

    Machine-written and machine-overwritten every run, which is why it carries
    a loud header: an edit made here by hand disappears at the next run, and
    the place to encode a human judgement is config/voice.md.
    """
    today = datetime.date.today().isoformat()
    L = [
        "# What actually earns replies",
        "",
        "<!-- GENERATED by tools/reply_features.py — DO NOT EDIT BY HAND. -->",
        "<!-- Hand edits are overwritten on the next run. Human judgement calls -->",
        "<!-- belong in config/voice.md, which outranks this file. -->",
        "",
    ]
    if tot < 20:
        # Printing "100% baseline (n=1)" as the headline invites exactly the
        # over-reading this file exists to prevent.
        L += [f"Regenerated {today}. **The cold book is too young to have taught "
              f"us anything yet** — {tot} cold 1:1 email"
              f"{'' if tot == 1 else 's'} has come of age"
              + (f", with {len(fresh)} more still awaiting a verdict."
                 if fresh else ".") + " Nothing below is a rule yet.", ""]
    else:
        L += [f"Regenerated {today} from {tot} mature cold 1:1 emails, {rep} of "
              f"which were answered — a **{base:.0%} baseline**"
              + (f" ({len(fresh)} more still in flight)." if fresh else ".") +
              " A rule below means that feature beat the baseline by enough, on "
              "enough emails, to survive Fisher's exact test with a "
              "Benjamini-Hochberg correction across every feature tested at once.",
              ""]
    L += ["## Rules — apply these when drafting (SKILL.md Step 7)", ""]
    if not rules:
        L += [
            "**None yet.** Nothing has cleared the evidence bar, which at this "
            "corpus size is the honest answer rather than a failure. Draft to "
            "`config/voice.md` as usual.",
            "",
            "This section fills itself in as batches land. It stays empty rather "
            "than shipping a rule built on four replies, because a false rule "
            "propagates into every future email and is far more expensive than "
            "no rule at all.",
            "",
        ]
    else:
        for t in sorted(rules, key=lambda t: -abs(t["lift"])):
            L.append(f"- **{phrase(t).capitalize()}.** {t['rate']:.0%} reply rate vs "
                     f"{t['base']:.0%} without it (n={t['n']}, p={t['p']:.3f}"
                     f"{', holds across '+str(t['strata'])+' industries' if t.get('strata') else ''}).")
        L.append("")

    if fresh:
        spread = collections.defaultdict(collections.Counter)
        for a in fresh:
            for feat, val in featurize(a).items():
                if is_copy(feat): spread[feat][val] += 1
        live = {f: c for f, c in spread.items()
                if len(c) > 1 and min(c.values()) >= MIN_N}
        L += ["## In flight — what the current batch will be able to answer", "",
              f"{len(fresh)} email(s) sent within the last {MATURITY} days. "
              "Silence from them means nothing yet.", ""]
        if live:
            L.append("These comparisons have both arms populated, so they will "
                     "resolve once the batch matures:")
            L.append("")
            for f, c in sorted(live.items()):
                L.append(f"- `{f}` — " + ", ".join(f"{v} ({n})" for v, n in c.most_common()))
        else:
            L.append("No copy feature is varied enough in this batch to be "
                     "testable. If that persists, vary something on purpose.")
        thin = [f for f, c in sorted(spread.items())
                if sum(c.values()) < len(fresh) / 2]
        flat = [f for f, c in sorted(spread.items())
                if len(c) < 2 and sum(c.values()) >= len(fresh) / 2]
        if flat:
            L += ["", "Never varied, so unanswerable from this batch: "
                      + ", ".join(f"`{f}`" for f in flat) + "."]
        if thin:
            L += ["", "Body text is not banked for most of this batch, so these "
                      "stay untestable until it is: "
                      + ", ".join(f"`{f}`" for f in thin) + "."]
        L.append("")

    L += ["## Watching — not proven, do not act on yet", ""]
    watch = [t for t in tests if is_copy(t["feat"]) and t["verdict"] in ("suggestive", "watching")
             and t["n"] >= 5]
    watch.sort(key=lambda t: (t["verdict"] != "suggestive", -t["n"]))
    for t in watch[:14]:
        tag = "suggestive" if t["verdict"] == "suggestive" else "thin"
        L.append(f"- `{t['feat']} = {t['val']}` — {t['k']}/{t['n']} replied "
                 f"({t['rate']:.0%}) · {tag}")
    L += ["", "## Targeting, not writing", "",
          "These describe who answers, not how to write to them. They belong in "
          "`config/autopilot.md`'s rotation, not in a draft.", ""]
    aud = [t for t in tests if t["feat"].startswith("aud_")
           and t["verdict"] in ("WORKS", "HURTS", "suggestive")]
    for t in sorted(aud, key=lambda t: -abs(t["lift"]))[:10]:
        L.append(f"- `{t['feat']} = {t['val']}` — {t['rate']:.0%} vs {t['base']:.0%} "
                 f"(n={t['n']}) · {t['verdict']}")
    L += ["", "---", "",
          f"Corpus: {sum(1 for a in acts if a['body'])} of {tot} emails have full "
          "bodies banked in `tracker/email-corpus.jsonl`; the rest contribute "
          "subject, opening line and timing only. Body-level rules get sharper "
          "as that number climbs.", ""]
    os.makedirs(os.path.dirname(GUIDE), exist_ok=True)
    open(GUIDE, "w").write("\n".join(L))


if __name__ == "__main__":
    main()
