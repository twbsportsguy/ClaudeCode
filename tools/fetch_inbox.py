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

LEDGER = "tracker/inbox-seen.jsonl"
OUT    = "threads.json"

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


def load_ledger():
    seen = {}
    if os.path.exists(LEDGER):
        for line in open(LEDGER):
            line = line.strip()
            if line:
                r = json.loads(line)
                seen[r["thread"]] = r.get("msgs", 0)
    return seen


def ingest(path, use_ledger=True):
    seen = load_ledger() if use_ledger else {}
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

    fresh, skipped = [], 0
    for tid in order:
        msgs = threads[tid]
        if use_ledger and seen.get(tid) == len(msgs):
            skipped += 1
            continue
        fresh.append({"id": tid, "messages": msgs})

    json.dump({"threads": fresh}, open(OUT, "w"), indent=1)

    # Ledger is rewritten whole so a thread that gained a message updates its
    # count rather than accumulating duplicate lines.
    for tid in order:
        seen[tid] = len(threads[tid])
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "w") as fh:
        for t, n in sorted(seen.items()):
            fh.write(json.dumps({"thread": t, "msgs": n}) + "\n")

    print(f"ingested {len(order)} threads, {sum(len(v) for v in threads.values())} messages")
    print(f"  {len(fresh)} new or changed -> {OUT}")
    print(f"  {skipped} unchanged, skipped (ledger now holds {len(seen)} threads)")
    if not fresh:
        print("  nothing changed since the last sweep — no need to run analyze_inbox.py")


def main():
    a = sys.argv[1:]
    if "--stats" in a:
        seen = load_ledger()
        print(f"{LEDGER}: {len(seen)} threads settled")
        return
    if "--ingest" in a:
        ingest(a[a.index("--ingest") + 1], use_ledger="--all" not in a)
        return
    since = (a[a.index("--since") + 1] if "--since" in a
             else datetime.date.today().strftime("%Y/%m/%d"))
    print_queries(since)


if __name__ == "__main__":
    main()
