#!/usr/bin/env python3
"""Prepare the inbox dump for analyze_inbox.py at the lowest possible token cost.

READ THIS FIRST — WHY THIS DOES NOT FETCH
-----------------------------------------
The obvious design is a script that calls Gmail and writes threads.json, so the
results never touch the model's context. That was tried on 2026-08-02 and it is
not possible here:

  * no Google credentials in the environment (no ADC, no ~/.config/gcloud, no
    service account, nothing in /run/secrets)
  * `googleapiclient` is not installed
  * the Gmail MCP endpoint answers 405 to an unauthenticated request, and its
    OAuth is held by the Claude Code harness, not by this container.
    CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR is Claude Code's own auth, not
    Gmail's.

So Gmail can only be reached from the assistant's tool loop. Results WILL land
in context; that part is fixed. What was avoidable — and what actually tripled
the cost of the 2026-08-02 run — is the assistant then re-emitting those results
as pretty-printed JSON. This tool removes that second copy three ways:

  1. `--queries` is the single source of truth for the sweep. The queries were
     previously duplicated across SKILL.md and two Routine prompts, drifting
     apart. The bounce and auto-reply sweeps are now bounded to 30 days; they
     were unbounded and re-pulled threads back to November 2025 on every run,
     whose classification had not changed since November 2025.
  2. `--ingest` accepts a terse TSV — one line per message — instead of indented
     JSON with full bodies. Same information, roughly a fifth of the tokens to
     write out.
  3. A ledger at tracker/inbox-seen.jsonl remembers every thread already
     classified. A thread is only re-ingested if its message count changed,
     i.e. something actually happened on it. On a daily refresh this is where
     most of the saving comes from: yesterday's 200 settled threads cost
     nothing today.

USAGE
  python3 tools/fetch_inbox.py --queries              # print the sweep to run
  python3 tools/fetch_inbox.py --ingest dump.tsv      # -> threads.json (+ledger)
  python3 tools/fetch_inbox.py --ingest dump.tsv --all   # ignore the ledger
  python3 tools/fetch_inbox.py --stats

TSV COLUMNS (tab-separated, no header, one line per MESSAGE):
  threadId  msgId  dateISO  sender  toRecipients  labelIds  subject  snippet

  toRecipients and labelIds are comma-separated. subject and snippet may be
  empty. Tabs inside a snippet must be stripped by the writer.
"""
import sys, os, json, datetime

LEDGER = "tracker/inbox-seen.jsonl"   # legacy: thread -> message COUNT only
CORPUS = "tracker/inbox-corpus.jsonl" # thread -> the messages themselves
OUT    = "threads.json"

# WHY THE CORPUS EXISTS (bug found 2026-08-05)
# -------------------------------------------
# The ledger above saves tokens by not re-FETCHING settled threads, which is
# correct and worth keeping. The mistake was writing only the survivors to
# threads.json, because analyze_inbox.py:346 does a plain json.dump over
# dashboard/inbox.json — a full overwrite, not a merge. So a refresh that
# legitimately found 9 new threads rebuilt the entire dashboard from those 9
# and dropped dashboard/inbox.json from 188 messages to 88.
#
# Fetching incrementally and REPORTING incrementally are different things. The
# saving is in the first; the bug was in the second. So the corpus keeps every
# message ever ingested on disk and threads.json is always the complete union.
# Emitting the full set costs nothing in tokens — it never enters anyone's
# context, it goes straight to a local file that local scripts read.

# The sweep. Bounded where bounding is safe and unbounded where it is not.
#
# Bounces and auto-replies arrive within about 48 hours of a send, so 30 days is
# already generous for them and cuts the dump by more than half. REPLIES are
# deliberately left at 60 days: a prospect answering five weeks later is exactly
# the kind of thing this pipeline exists to catch, and narrowing that one would
# be a real loss rather than a saving.
QUERIES = [
    ("sent",     "in:sent after:{since}",
     "THREAD_VIEW_METADATA_ONLY",
     "Paginate to the end. Never omit: sync_activity.py counts the sends it is "
     "handed, and a dump without this reported a 55-send morning as '7 sent, 0 "
     "delivered' on 2026-07-29."),
    ("bounces",  'newer_than:30d (from:mailer-daemon OR from:postmaster OR '
                 'subject:"Delivery Status Notification" OR subject:"Undeliverable" '
                 'OR subject:"Returned mail")',
     "THREAD_VIEW_MINIMAL",
     "30d bound added 2026-08-02. A bounce older than a month has already been "
     "classified and its verdict cannot change."),
    ("autoreply", 'newer_than:30d (subject:"Automatic reply" OR subject:"Out of Office" '
                  'OR "no longer with")',
     "THREAD_VIEW_MINIMAL",
     "30d bound added 2026-08-02, same reasoning. Read the body of any hit: the "
     "delegate or replacement address is the whole value."),
    ("replies",  "in:inbox newer_than:60d -category:promotions -category:updates",
     "THREAD_VIEW_MINIMAL",
     "Deliberately NOT narrowed to 30d. A late reply is the point of the sweep."),
]


def print_queries(since):
    print("Run these with mcp__Gmail__search_threads, then write ONE tsv of all "
          "results and pass it to --ingest.\n")
    for name, q, view, why in QUERIES:
        print(f"[{name}]  view={view}")
        print(f"  query: {q.format(since=since)}")
        print(f"  note:  {why}\n")
    print("Emit the TSV as: threadId<TAB>msgId<TAB>date<TAB>sender<TAB>to<TAB>"
          "labels<TAB>subject<TAB>snippet")
    print("Only include threads NOT already settled — run --stats to see the "
          "ledger, and skip any threadId in it whose message count is unchanged.")


def load_corpus():
    """thread id -> list of message dicts, for every thread ever ingested."""
    corpus = {}
    if os.path.exists(CORPUS):
        for line in open(CORPUS):
            line = line.strip()
            if line:
                r = json.loads(line)
                corpus[r["thread"]] = r.get("msgs", [])
    return corpus


def load_ledger():
    """Legacy count-only ledger. Still read so an existing install knows which
    threads it has already seen, but it cannot rebuild threads.json on its own
    — it never stored the messages. See migrate note in ingest()."""
    seen = {}
    if os.path.exists(LEDGER):
        for line in open(LEDGER):
            line = line.strip()
            if line:
                r = json.loads(line)
                seen[r["thread"]] = r.get("msgs", 0)
    return seen


def save_corpus(corpus):
    os.makedirs(os.path.dirname(CORPUS), exist_ok=True)
    with open(CORPUS, "w") as fh:
        for tid, msgs in sorted(corpus.items()):
            fh.write(json.dumps({"thread": tid, "msgs": msgs}) + "\n")


def ingest(path, use_ledger=True):
    corpus = load_corpus()
    # The ledger is ALWAYS loaded, even under --all. --all means "re-ingest
    # these threads rather than trusting the skip test"; it must never mean
    # "forget every thread not in today's dump". Loading it only when
    # use_ledger was true meant a --all run against a two-thread dump rewrote
    # the 126-thread ledger with two lines. Caught on 2026-08-05 by doing
    # exactly that; the file was tracked, so git had the original.
    ledger = load_ledger()
    seen = dict(ledger)
    skip = ledger if use_ledger else {}
    # A thread already in the corpus counts as seen even if the legacy ledger
    # was never written, so the two stay consistent as the old file ages out.
    for tid, msgs in corpus.items():
        seen.setdefault(tid, len(msgs))
    threads, order = {}, []
    for ln in open(path):
        ln = ln.rstrip("\n")
        if not ln.strip(): continue
        parts = ln.split("\t")
        # Tolerate short rows rather than dying mid-dump; a missing snippet is
        # not worth losing the whole sweep over.
        parts += [""] * (8 - len(parts))
        tid, mid, date, sender, to, labels, subject, snippet = parts[:8]
        if tid not in threads:
            threads[tid] = []
            order.append(tid)
        threads[tid].append({
            "id": mid, "date": date, "sender": sender,
            "toRecipients": [a for a in to.split(",") if a],
            "labelIds": [l for l in labels.split(",") if l],
            "subject": subject, "snippet": snippet,
        })

    changed, unchanged = 0, 0
    for tid in order:
        msgs = threads[tid]
        if skip.get(tid) == len(msgs) and tid in corpus:
            unchanged += 1
            continue
        corpus[tid] = msgs          # new thread, or one that gained a message
        changed += 1

    # threads.json is the COMPLETE picture, always. analyze_inbox.py overwrites
    # dashboard/inbox.json wholesale from this file, so handing it a partial set
    # silently deletes history — that is exactly what happened on 2026-08-05.
    allthreads = [{"id": t, "messages": m} for t, m in corpus.items()]
    json.dump({"threads": allthreads}, open(OUT, "w"), indent=1)
    save_corpus(corpus)

    # Legacy ledger kept in step so an older checkout still skips correctly.
    for tid, msgs in corpus.items():
        seen[tid] = len(msgs)
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "w") as fh:
        for t, n in sorted(seen.items()):
            fh.write(json.dumps({"thread": t, "msgs": n}) + "\n")

    msgs_total = sum(len(m) for m in corpus.values())
    print(f"dump held {len(order)} threads, "
          f"{sum(len(v) for v in threads.values())} messages")
    print(f"  {changed} new or changed, {unchanged} unchanged and reused from corpus")
    print(f"  -> {OUT}: {len(allthreads)} threads / {msgs_total} messages (COMPLETE set)")
    if not changed:
        print("  nothing changed since the last sweep — dashboard rebuild optional")

    # The pre-2026-08-05 install has a count-only ledger and no corpus, so the
    # first run after this fix knows which threads it has seen but not what was
    # in them. Say so loudly rather than quietly emitting a short file.
    missing = [t for t in seen if t not in corpus]
    if missing:
        print(f"\n  WARNING: {len(missing)} thread(s) are in the legacy ledger but "
              f"have no stored messages.\n"
              f"  threads.json is incomplete by that many. Re-run the sweep once "
              f"with --all to\n  seed the corpus in full; after that this warning "
              f"goes away for good.")


def main():
    a = sys.argv[1:]
    if "--stats" in a:
        seen, corpus = load_ledger(), load_corpus()
        print(f"{LEDGER}: {len(seen)} threads settled")
        print(f"{CORPUS}: {len(corpus)} threads / "
              f"{sum(len(m) for m in corpus.values())} messages stored")
        missing = [t for t in seen if t not in corpus]
        if missing:
            print(f"  {len(missing)} settled thread(s) have no stored messages — "
                  f"run one sweep with --all to seed the corpus")
        return
    if "--ingest" in a:
        ingest(a[a.index("--ingest") + 1], use_ledger="--all" not in a)
        return
    since = (a[a.index("--since") + 1] if "--since" in a
             else datetime.date.today().strftime("%Y/%m/%d"))
    print_queries(since)


if __name__ == "__main__":
    main()
