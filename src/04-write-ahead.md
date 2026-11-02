# Write-Ahead

> Never make a promise you cannot reconstruct.

<img class="chapter-illustration" src="img/illus-04-write-ahead.png" alt="A monk writing in a huge open ledger. Through the archway behind him a messenger waits with a horse, not yet permitted to leave.">

I want to show you a bug that is worse than a lie, because everybody
involved was telling the truth.

Suppose `fsync()` returns `EIO`. A real hardware write failure,
correctly detected, correctly surfaced. So we do the responsible thing:
we log it, and we retry the `fsync`.

<p class="quip">The most dangerous error message is the one that says everything is fine.</p>

It returns `0`. Success.

The bytes it just claimed to have persisted were never written, and
they never will be. The kernel is not lying to you. It is telling you
the honest truth about the only attempt it still has any record of.

This was a real bug, found by the PostgreSQL developers in 2018,[^lwn]
and once you see why it happened, it changes what the phrase "handle the error" is even
permitted to mean.

## 10.1 Two Candidates and a Missing Number

Before we decide what to do about that, we have to settle what actually
happened, and there are two readings of it that lead somewhere very
different.

The first: an `fsync` error behaves like any other I/O error. Log
it, back off, retry, and eventually it either succeeds or you escalate.

The second: retrying does nothing at all, because there is nothing
left to retry.

This is not a ratio we can divide our way out of. It is a question
about what the kernel does at the instant writeback fails, so let's
just trace it through, slowly, because the answer is stranger than it
looks.

A dirty page fails to reach the device. The kernel reports the error to
whoever calls `fsync` next, and it reports it once. Then it **marks the
page clean and drops it.**

Read that again. Not clean because it succeeded. Clean because the
kernel gave up and stopped tracking it as pending work. The data that
failed to write is now simply gone from the page cache. There is
nothing dirty left for a second `fsync` to flush.

<p class="quip">Nobody lied. The kernel answered exactly the question it was asked, which was not the question anybody meant.</p>

So the second call returns success. Honestly. From where it is
standing, there is genuinely nothing left to do.

<div class="aside">
Linux changed how these errors are reported, starting with version 4.13
and again in later versions, so that the error is harder to lose. It did
not change the deeper fact underneath. The PostgreSQL project's own
record of the episode puts it plainly for the newer kernels: "you still
only get the error once (so retrying fsync() is not OK)", and the failed
pages are "still thrown away".[^pgwiki] The fix made the error easier to
see. It did not make the data come back.
</div>

## 10.2 The Axioms

The division in this chapter is not about time. It is about copies.
At every step, count how many independent copies of the data exist
that could still bring it back. A recovery plan is only as good as that
count at its worst moment.

To count them we need three facts about kernel behaviour, none of which
you can reason your way to from first principles, and all three of which
have to be true at once for the bug above to happen. They are stable
facts about an interface, not about hardware, and the sources are
below.

| Fact | What it means for us |
|---|---|
| A writeback failure marks the page clean and evicts it | The failed bytes are gone from the page cache, not "still pending" |
| The error is reported **once**, not on every later call | A second call can see success on a page that never made it to disk |
| The kernel has no concept of "our" data, only dirty pages | It cannot retry on our behalf; it does not know what the bytes were for |

<p class="quip">A backup on the same disk is not a backup. Everybody agrees with this, and plenty of us keep one anyway.</p>

Now count. Before the failure there was one copy of the new bytes: the
dirty page in the page cache. The failed writeback threw it away. The
count is zero, and there is nothing a retry can retry *with*.

So you get something that sounds almost harsh: an
`fsync` failure is not a transient fault to be retried. It is a
terminal event. The only sound response is to treat that data as lost
and rebuild it from somewhere the kernel did not just erase.

<div class="rule" id="fsync-terminal">
<span class="rule-id">Rule 12 · Retrying is not recovery when the failure took the copy</span>
Count the independent copies at every step. When a failure destroys the
thing you would retry with, retrying succeeds at nothing; only an
independent copy made earlier can bring the data back. For `fsync`: an
error is final, so make the log durable before you promise anything.
</div>

## 10.3 Doing the Division

That "independent, already-durable source" has a name. It is the
write-ahead log, and the pattern that survives this failure mode is
narrow and specific. Every clause in it is carrying weight:

```
1. write the record to the WAL          (userspace buffer)
2. fsync the WAL                        (the one barrier you pay for)
3. ACK the client                       ← the only line that matters
4. apply the change to the data pages   (lazily, async, whenever)
```

Steps 1 through 3 are the whole durability contract. Step 4 can happen
a second later, a minute later, or after a crash and a replay, and it
genuinely does not matter which, because if the crash arrives before
step 4 finishes we do not need step 4's result. We need the WAL, and we
already made certain that one thing was durable before we told anybody
we were done.

The data pages, meanwhile, are allowed to be wrong. Half-written.
Entirely missing. At any instant you care to inspect them.

That sounds reckless until you see why it is fine: they are *derived*
state. They can be rebuilt. The WAL is the only object in this picture
that cannot be reconstructed from anything else, and that is exactly
why it is the one thing that gets the expensive, synchronous, ordered
barrier we bought in chapter 2.

<p class="quip">The data pages are allowed to be wrong. It takes a while to be comfortable writing that sentence down.</p>

Count the copies again. From the moment step 2 returns, there is one
durable copy of the fact on the device, and the acknowledgement in step
3 is never sent before that count reaches one. Every later failure,
including a failed `fsync` on a data page, leaves the count at one or
more. That is the whole design, said as a number.

One barrier. On the one irreplaceable thing.

## 10.4 What This Rules Out

This rules out the natural instinct to spread `fsync` calls evenly
across everything that looks important.

Not all durable-looking writes are equally irreplaceable. A data page is
a cached, derivable projection of the log. Losing an unflushed data page
after a crash costs you a replay, which is to say it costs you some
seconds. Losing the log entry costs you the fact itself. There is no
second copy anywhere, and no amount of retrying a broken `fsync` brings
it back.

Now here is a question that looks entirely unrelated, and I promise it
is the same question.

Why does PostgreSQL's torn-page protection (`full_page_writes`) take
its reference image from the **in-memory buffer pool**, and never by
re-reading the on-disk file it is trying to protect?

It would be so much simpler to read the file. The file is right there.

But the disk file is precisely the thing we do not trust. That is the
entire premise of needing torn-page protection in the first place: a
page write that crashes partway through leaves a sector-level mixture
of old and new bytes. If our known-good reference came from reading
that same file back, we would be verifying the disk against itself, and
a corrupted page would cheerfully certify its own corruption.

<p class="quip">Asking the suspect to vouch for the suspect. It passes every test you can think of, which is the trouble.</p>

The buffer pool copy is the one version of that page our process
actually validated. It is the only candidate in the room that is not
circular.

Same rule as before, wearing different clothes: your recovery source
has to be independent of the thing that failed.

## 10.5 The Pictorial

Four boxes and one arrow that matters. Watch where the acknowledgement
sits, because everything in the design follows from its position:

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
Notice the ACK sits <em>between</em> the WAL's fsync and the data-page
write, not after both. That ordering is the whole design. Everything
drawn to the right of the ACK arrow is allowed to fail, restart, or
simply take its time.
</div>

<div class="challenges">

## Challenges

1. A junior engineer "fixes" the retry bug by calling `fsync` in a loop
   until it returns success three times in a row. Explain, from Rule 12,
   why this is no safer than calling it once.

2. Your WAL fsync succeeds and you ACK the client. The process then
   crashes before applying the change to data pages. Walk through
   recovery. Where does the correct final state come from, and why
   doesn't it matter that step 4 never ran?

3. Suppose you moved the ACK to *after* the data pages are written
   instead of right after the WAL fsync. What does that change about
   your system's worst-case commit latency, and what do you gain for
   it?

4. `full_page_writes` doubles WAL volume right after every checkpoint.
   Using Rule 4 from chapter 2, propose a way to reduce that
   cost without weakening the torn-page guarantee.

</div>

<div class="challenges" id="design-note">

## Design Note: Design for the Failure You Can't Retry

Most error-handling advice quietly assumes failures are transient. Back
off, retry, and eventually the world cooperates. That assumption is
correct often enough that we stop noticing we are making it.

`fsync` breaks it quietly, which is far worse than breaking it loudly,
because the retry *looks* like it worked. It returns success. Your logs
show a transient error followed by a recovery. Everything about the
shape of it is reassuring, and every bit of that reassurance is false.

The lesson generalizes well past storage. Any time a failure silently
discards the thing you were trying to protect, "retry the same
operation" is not a recovery strategy. It is a way to convince yourself
that you have one, which is strictly worse than knowing you do not,
because the person who knows they have no recovery path goes and builds
one.

The real fix is architectural, and it is not subtle: keep an
independent, already-durable copy of anything you cannot afford to be
wrong about, and make it durable *before* you promise anybody it is
safe.

Write-ahead logging is not really a storage pattern, in the end. It is
what "design for the failure you cannot retry" looks like once somebody
draws it out on paper.

</div>

[^lwn]: J. Corbet, "PostgreSQL's fsync() surprise," *LWN.net*, 18 April
    2018: "When a buffered I/O write fails due to a hardware-level error,
    filesystems will respond differently, but that behavior usually
    includes discarding the data in the affected pages and marking them
    as being clean." <https://lwn.net/Articles/752063/>

[^pgwiki]: PostgreSQL wiki, "Fsync Errors" (last edited 5 July 2023).
    For Linux before 4.13: "buffers are marked clean after errors, so
    retrying fsync() can falsely report success." For 4.14 and 4.16 and
    later: "you still only get the error once (so retrying fsync() is
    not OK)" and "buffers are still thrown away."
    <https://wiki.postgresql.org/wiki/Fsync_Errors>
