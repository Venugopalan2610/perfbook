# The Barrier

> fsync is not a save button. It is a purchase.

Let's run a small loop: an 8-byte counter, appended to a file, once per
iteration. In memory, that loop does fifty million iterations a second.
Add one call — `fsync()` after every append — and it does two thousand.

Twenty-five thousand times slower, just to persist eight bytes. Not
eight megabytes. Eight bytes. Whatever `fsync` is charging us for, it
clearly isn't the data.

## 3.1 Two Candidates and a Missing Number

Candidate one: `fsync` is slow because it moves our bytes to the
device, and moving bytes takes bandwidth-bound time. Candidate two:
`fsync` is slow for a reason that has nothing to do with how many bytes
we handed it.

Let's name the ratio before picking. At even a modest 2 GB/s device
bandwidth, 8 bytes should cost:

```
8 B ÷ 2 GB/s ≈ 4 nanoseconds
```

We measured roughly 100 microseconds for that same call. Not a close
call — that's **25,000×** over the bandwidth floor. Candidate one isn't
slightly wrong, it's off by more than four orders of magnitude. Set it
aside.

<div class="aside">
Same move as chapter 1's floor test, run in the opposite direction.
There, a measurement came in *under* every floor and proved work had
been skipped. Here, a measurement comes in wildly *over* the bandwidth
floor and proves the cost isn't the thing we assumed we were paying
for.
</div>

## 3.2 The Axioms

`fsync` latency, end to end, by device class:

| Device | Typical `fsync` latency |
|---|---|
| NVMe SSD | ~100 µs |
| SATA SSD | ~1–3 ms |
| 7200 RPM spinning disk | ~5–10 ms |

Roughly a 100× spread top to bottom — and every one of those numbers
stays close to flat whether we're syncing 8 bytes or 8 kilobytes. That
flatness is the tell. If cost barely moves with payload size, payload
size was never the dominant term.

## 3.3 Doing the Division

What `fsync` actually is: a **barrier**. A call that blocks until every
write queued before it is provably on non-volatile media, and — this is
the part the name hides — a promise about *order*, not just
persistence. Nothing after the barrier gets to be considered durable
before everything ahead of it is.

<img class="ruler-chart" src="img/ruler-03-the-barrier.svg" alt="Log-scale ruler: 4 nanosecond bandwidth floor versus 100 microsecond measured fsync, 1-3 millisecond SATA, and 5-10 millisecond spinning disk. The floor sits six orders of magnitude to the left.">

Paying that barrier cost once, for a batch of a thousand records, and
paying it a thousand times, for the same thousand records one at a
time, move very differently: the first is one round trip, the second is
a thousand of them.

<div class="rule" id="boundary-not-spray">
<span class="rule-id">Rule 5 · Buy durability at boundaries, not by the record</span>
`fsync` cost is dominated by the round trip to the barrier, not the
bytes behind it. Pay it once per boundary you actually need to defend,
never once per write.
</div>

## 3.4 What This Rules Out

This rules out the intuition that durability is something we sprinkle
in — "just fsync after every write, to be safe." Safety isn't the axis
that scales badly here; call *count* is. A service that fsyncs every
record is choosing to pay a 100 µs–10 ms toll on every single
operation, no matter how small, because the toll booth doesn't care
what's in the trunk.

It also separates two things we tend to lump together: durability and
ordering aren't the same purchase. You can imagine a system that needs
writes applied in order but doesn't need every one of them durable the
instant it lands — and one that needs durability but doesn't care about
relative order. `fsync` sells us both together, bundled, whether we
wanted the bundle or not. Chapter 4 is what happens once you take that
bundling seriously: you put only the thing that *must* be
ordered-and-durable behind the barrier, and let everything else move
lazily behind it.

## 3.5 The Pictorial

```
 record 1 ─┐
 record 2 ─┤  queued, unordered w.r.t. the barrier
 record 3 ─┘
           │
     ══════╪══════  fsync()  ←  the barrier: one round trip,
           │                    ~100 µs – 10 ms, size-insensitive
           ▼
 [ record 1 | record 2 | record 3 ]  ← provably durable, in this order,
                                        only past this line
```

<div class="aside">
Fsync-per-record redraws this picture a thousand times for a thousand
records: a thousand barriers, each paying the full round trip for one
row's worth of data. Group commit (chapter 5) is what happens once we
let the queue fill before drawing the line.
</div>

<div class="challenges">

## Challenges

1. You batch 100 records behind one `fsync` instead of syncing each
   individually. Using the NVMe number above, what's the best-case
   throughput improvement, and what would make the real improvement
   fall short of it?

2. A teammate suggests using `fdatasync` instead of `fsync` to skip
   metadata (mtime, size) updates. Under what circumstance does that
   optimization not actually save a barrier crossing?

3. Two threads each call `fsync` on the same file at nearly the same
   time. Does the second call's cost look like a second full barrier,
   or something cheaper — and what would you measure to find out, per
   Rule 3?

4. `O_DIRECT` writes bypass the page cache entirely. Does that make
   `fsync` unnecessary for durability? Name the specific claim `fsync`
   makes that a direct write, by itself, does not.

</div>

<div class="challenges" id="design-note">

## Design Note: The Bundle You Didn't Ask For

Every `fsync` call sells two things at once: *this data is durable* and
*everything before it happened first*. Most of us only ever reach for
it because we want the first one, and end up paying for the second
without noticing.

That would be fine if the second one were free. It isn't — ordering
guarantees are exactly what turns a bandwidth-bound operation into a
latency-bound one, because proving order means waiting for
confirmation, and waiting is the opposite of throughput.

The systems that get this right unbundle it on purpose. They find the
one thing that truly needs the full barrier — usually a small,
append-only log — and let everything downstream inherit durability
without ever calling `fsync` itself. Not a trick. Just declining to buy
the bundle twice.

</div>
