# Group Commit

> A constant that works at one load level is a bug waiting for load to change.

Say we've read chapter 3, and taken it seriously. Fsync-per-record was
costing us 25,000× what the bytes warranted, so we batch: collect 1000
records, fsync once, ack all of them together. Under load, throughput
jumps fifty-fold. We ship it, pleased with ourselves.

Overnight, traffic drops to ten events a second. The same code now
takes **one hundred seconds** to acknowledge a single write.

Nothing actually broke. The arithmetic is exactly the arithmetic we'd
expect: 1000 records at 10/sec takes 1000 ÷ 10 = 100 seconds to fill the
batch. We didn't introduce a bug. We hard-coded a load level, and then
the load changed on us.

## 5.1 Two Candidates and a Missing Number

Candidate one: pick a bigger fixed batch size for throughput, a smaller
one for latency, and tune the constant to match our traffic. Candidate
two: stop picking a constant at all.

Let's name the ratio, because it's the whole argument. A fixed batch of
1000 costs us:

```
at 100,000 events/sec:  1000 ÷ 100,000  =  10 ms  to fill    (fine)
at      10 events/sec:  1000 ÷      10  = 100  s  to fill    (not fine)
```

**Ten million times worse**, same constant, just a quieter night.
There's no single value of N that's safe across a load range that
wide. Whatever we pick is only correct at the traffic level we tuned
it for, and wrong by orders of magnitude everywhere else.

<div class="aside">
A fixed time window ("always wait 10 ms") looks like a fix, and it does
bound the worst case. But it also *forces* every request to pay that
10 ms even at 3 a.m. when nobody's behind you and the fsync could have
gone out immediately. We'd just be trading a variable disaster for a
constant tax.
</div>

## 5.2 The Axioms

The one fact this chapter needs, and chapter 3 already handed us: an
`fsync` round trip costs roughly the same whether it carries one record
or a thousand.

| Path | Cost per fsync |
|---|---|
| NVMe, one record | ~100 µs |
| NVMe, a thousand records | ~100 µs |

That equality is the whole opportunity. If a barrier crossing is nearly
free per additional record, the only thing worth optimizing is *how
many records arrive during the crossing we're already paying for*,
not how many we force ourselves to wait for.

## 5.3 Doing the Division

So let's not set N. Set the rule instead: **when the in-flight `fsync`
returns, immediately start the next one, and sweep in everyone who
arrived while the first was in flight.**

```
t=0         fsync #1 issued (covers whatever's queued right now)
t=0..100µs  requests 2, 3, 4 arrive; they queue behind fsync #1
t=100µs     fsync #1 returns → ack 1; fsync #2 issued, covers {2,3,4}
t=100..??   whatever arrives now queues behind fsync #2
t=200µs     fsync #2 returns → ack 2,3,4; fsync #3 issued, covers {...}
```

The batch size falls out of the arrival rate automatically. At high
load, dozens of requests pile up during one 100 µs window and ride out
together, and we get the throughput win without ever naming a number. At
low load, a single request often finds nobody else queued, its "batch"
is size one, and it still only waits one fsync round trip, not the
100 seconds a fixed count of 1000 would have imposed.

<div class="rule" id="adaptive-batching">
<span class="rule-id">Rule 7 · Let the barrier set its own batch size</span>
Close the batch when the in-flight fsync returns, not when a counter
hits a constant. The batch size becomes a function of load instead of a
guess about it.
</div>

## 5.4 What This Rules Out

This rules out both fixed-count and fixed-time-window batching as
general solutions, not because they're wrong exactly, but because each
one encodes an assumption about load that the adaptive version doesn't
need to make. Fixed-count breaks low; fixed-window taxes everyone,
always, even when nobody's waiting behind you.

One wrinkle the naive adaptive version misses: at *moderate* load,
just under one arrival per fsync-latency window, batches regress
toward size one anyway, and we're back to firing an `fsync` for nearly
every record. That's not a correctness problem, but it does mean
maximum call rate, and on flash media, call rate correlates with write
amplification and wear. A small floor (hold the batch open for a
minimum of roughly 200 µs even if the in-flight fsync would've returned
sooner) caps how often the device gets hit, at the cost of a bounded,
small, constant latency add. Same trade as the fixed window, just sized
to be negligible instead of dominant.

## 5.5 The Pictorial

<img class="chart" src="img/group-commit-05-group-commit.svg" alt="Log-scale bar chart comparing wait time to fill a batch under fixed-count versus adaptive batching, at low load (10 events/sec) and high load (100,000 events/sec). Fixed count swings from 100 seconds at low load to 10 milliseconds at high load. Adaptive stays flat around 100 microseconds at both.">


<div class="aside">
This is the same amortization trick as batching writes before `fsync`
in the first place, and (spoiler for chapter 7) the same trick that
makes GPU batching worthwhile too. Pay a fixed round-trip cost once,
spread it over whoever showed up while you were paying it.
</div>

<div class="challenges">

## Challenges

1. At exactly one arrival per fsync-latency window, adaptive batching's
   average batch size converges to what? Is that better or worse than
   fixed-count N=2 at the same load?

2. Your floor is 200 µs. Load spikes to 50,000 events/sec, well above
   what one fsync can drain in 200 µs. What happens to the queue, and
   does the floor still help or start hurting?

3. Two independent adaptive-batching writers share the same underlying
   log file. What has to be true about how they coordinate fsync calls
   for the scheme in 5.3 to still be correct?

4. Redraw the 5.1 arithmetic for a system with two tiers of durability
   need: some callers require the fsync ack, others are fine acking
   off the page cache. Does one adaptive batch still serve both, or do
   you need two?

</div>

<div class="challenges" id="design-note">

## Design Note: Tuning a Constant Is Postponing a Bug

Every hardcoded batch size, timeout, or thread-pool count is a bet that
tomorrow's load looks like today's. The bet is usually fine, until
traffic has a bad night, a good launch, or a regional failover doubles
one region's share. The constant doesn't fail loudly when the bet goes
bad. It just quietly stops being the right answer, and the system keeps
running, worse, until someone notices the 100-second tail.

The fix isn't a better constant. It's noticing which inputs to the
formula are actually *observable at runtime* (here, "is the fsync
still in flight") and driving the decision off those instead of a
number picked once, in a meeting, based on last week's dashboard.

If we can replace a constant with a measurement the system already has
for free, that's not a nice-to-have. That's removing a bug that hasn't
happened yet.

</div>
