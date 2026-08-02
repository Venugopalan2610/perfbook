# Write-Ahead

> Never make a promise you cannot reconstruct.

Suppose `fsync()` returns `EIO` — a real hardware write failure,
correctly surfaced. We do the responsible thing: log it, and retry the
`fsync`. It returns `0`. Success.

The bytes it just claimed to have persisted were never written. This
isn't quite a lie — the kernel is telling the truth about the only
attempt it still has any record of. This was a real bug, discovered in
PostgreSQL in 2018, and once you understand why it happened, it changes
what "handle the error" is even allowed to mean.

## 4.1 Two Candidates and a Missing Number

Candidate one: an `fsync` error behaves like any other I/O error — log
it, back off, retry the call, eventually it succeeds or you escalate.
Candidate two: retrying does nothing at all, because there's nothing
left to retry.

This isn't a ratio we can compute our way out of; it's a question about
what the kernel does the moment writeback fails. Trace it through: a
dirty page fails to reach the device. The kernel reports the error to
whoever calls `fsync` next — but only once. Then it **marks the page
clean and drops it.** Not "clean because it succeeded." Clean because
the kernel gave up and stopped tracking it as pending. The data that
failed to write is simply gone from the page cache now. There's
nothing dirty left for a second `fsync` to flush, so it returns
success — honestly, from where it's sitting.

<div class="aside">
The fix that shipped in Linux 4.13 (`errseq_t`) made sure every open
file description sees the error at least once, instead of the first
caller silently consuming it for everyone. It didn't change the deeper
fact underneath: the page itself is still discarded after one failed
writeback. Retry-until-success was broken before the fix, and it's
still broken after it.
</div>

## 4.2 The Axioms

| Fact | What it means for us |
|---|---|
| A writeback failure marks the page clean and evicts it | The failed bytes are gone from the page cache, not "still pending" |
| The error surfaces to `fsync` **at most once per file description** (post-4.13) | A second caller, or a second call, can see success on a page that never made it to disk |
| The kernel has no concept of "our" data, only dirty pages | It can't retry on our behalf — it doesn't know what the bytes were for |

Put together: an `fsync` failure isn't a transient fault to retry. It's
a terminal event. The only sound response is to treat the data as lost
and recover it from somewhere the kernel didn't just erase.

<div class="rule" id="fsync-terminal">
<span class="rule-id">Rule 6 · fsync failure is not retryable</span>
Once `fsync` reports an error, the page behind it is already gone.
Retrying the same call can't recover it — only replaying from an
independent, already-durable source can.
</div>

## 4.3 Doing the Division

That "independent, already-durable source" has a name: the write-ahead
log. The pattern that survives this failure mode is narrow and
specific, and every clause in it is load-bearing:

```
1. write the record to the WAL          (userspace buffer)
2. fsync the WAL                        (the one barrier you pay for)
3. ACK the client                       ← the only line that matters
4. apply the change to the data pages   (lazily, async, whenever)
```

Steps 1–3 are the entire durability contract. Step 4 can happen a
second later, a minute later, or after a crash and a replay — because
if the crash happens before step 4 finishes, we don't need step 4's
result. We need the WAL, and we already made sure that one thing was
durable before telling anyone we were done.

The data pages, meanwhile, are allowed to be wrong, half-written, or
entirely missing at any given instant, because they're *derived*
state. The WAL is the only thing in this picture that can't be
reconstructed from anything else — which is exactly why it's the one
thing that gets the expensive, synchronous, ordered barrier from
chapter 3.

## 4.4 What This Rules Out

This rules out the natural instinct to spread `fsync` calls evenly
across "important" writes. Not all durable-looking writes are equally
irreplaceable. A data page is a cached, derivable projection of the
log. Losing an unflushed data page after a crash costs a replay.
Losing the log entry costs the fact itself — there's no second copy
anywhere, and no amount of retrying a broken `fsync` call brings it
back.

The same logic answers a question that looks unrelated at first: why
does PostgreSQL's torn-page protection (`full_page_writes`) source its
reference image from the **in-memory buffer pool**, and never by
re-reading the on-disk file it's trying to protect?

Because the disk file is the thing we don't trust. That's the whole
premise of needing this protection in the first place — a page write
that crashes partway through can leave a sector-level mix of old and
new bytes. If our "known good" reference came from reading that same
file back, we'd be verifying the disk against itself. The buffer pool
copy is the one version of the page our process actually validated;
it's the only candidate that isn't circular.

## 4.5 The Pictorial

```
 client request
        │
        ▼
 ┌──────────────┐   write()    ┌──────────────┐   fsync()    ┌──────────┐
 │  WAL record  │─────────────▶│  page cache  │─────────────▶│  device  │
 └──────────────┘              └──────────────┘              └──────────┘
                                                                        │
                                                         ACK client ◀───┘
                                                         (the only line
                                                           that matters)
        │
        ▼ (lazy, async, any time after the ACK)
 ┌──────────────┐
 │  data pages  │  ← derived. Can be rebuilt from the WAL.
 └──────────────┘     Never the thing we promised on.
```

<div class="aside">
Notice the ACK sits *between* the WAL's fsync and the data-page write,
not after both. That ordering is the whole design. Anything drawn to
the right of the ACK arrow is allowed to fail, restart, or simply be
slow.
</div>

<div class="challenges">

## Challenges

1. A junior engineer "fixes" the retry bug by calling `fsync` in a loop
   until it returns success three times in a row. Explain, from Rule 6,
   why this is no safer than calling it once.

2. Your WAL fsync succeeds and you ACK the client. The process then
   crashes before applying the change to data pages. Walk through
   recovery — where does the correct final state come from, and why
   doesn't it matter that step 4 never ran?

3. Suppose you moved the ACK to *after* the data pages are written
   instead of right after the WAL fsync. What does that change about
   your system's worst-case commit latency, and what do you gain for
   it?

4. `full_page_writes` doubles WAL volume right after every checkpoint.
   Using Rule 5 from the previous chapter, propose a way to reduce that
   cost without weakening the torn-page guarantee.

</div>

<div class="challenges" id="design-note">

## Design Note: Design for the Failure You Can't Retry

Most error-handling advice assumes failures are transient: back off,
retry, eventually the world cooperates. `fsync` breaks that assumption
quietly, which is worse than breaking it loudly — the retry *looks*
like it's working, because it returns success.

The deeper lesson generalizes past storage: any time a failure silently
discards the thing you were trying to protect, "retry the same
operation" isn't a recovery strategy — it's a way to convince yourself
you have one. The real fix is architectural: keep an independent,
already-durable copy of anything you can't afford to be wrong about,
made durable *before* you promise anyone it's safe.

Write-ahead logging isn't really a storage pattern, in the end. It's
what "design for the failure you can't retry" looks like once you draw
it out on paper.

</div>
