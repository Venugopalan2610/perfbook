# Five Microseconds

> Any sufficiently advanced measurement is indistinguishable from a lie.

<img class="chapter-illustration" src="img/illus-01-five-microseconds.png" alt="A postman cheerfully posting a letter into the front of a pillar box while a cascade of mail spills out of a crack in its side onto the pavement behind him. He is not looking.">

I want to start with something you can do right now, without leaving
this page. Write a megabyte to a file. Time the call. See what comes
back.

On an ordinary machine, on an ordinary day, it comes back in about five
microseconds.

<p class="quip">Five microseconds is about how long it takes light to cross a football pitch. Your megabyte did not go anywhere near that far.</p>

Now, if you run that a hundred times, the number stops registering.
It's small, the write worked, the test passed, and there's a whole
afternoon of other work waiting. I have done exactly this and thought
nothing of it. But five microseconds is the loudest thing that will
happen to you all week, and this chapter is about learning to actually
hear it.

We are not going to look anything up. By the end you will know exactly
where that megabyte is sitting, and we will have gotten there with four
numbers and some long division, which is honestly all this ever takes.

## 1.1 Two Candidates and a Missing Number

Let's start where everybody starts. Where could the data actually be?

<div class="aside">
Notice that "candidates" came before "answer." We are not trying to be
right yet. We are trying to bound the space cheaply enough that being
wrong costs us nothing.
</div>

Either it's still in memory, or it's out on the disk. That's a
reasonable first cut. And the reflex that follows, the one I have had a
hundred times, is to say *disk is slower than memory* and feel like
some progress has been made.

It hasn't. Not really. That's a **direction**, and a direction cannot
decide anything by itself. Both candidates are still standing, and we
have no idea which way to lean, because we never asked the question
that actually separates them:

**How much slower?**

This is the habit the whole book is built on, so it is worth saying
plainly. When you name two possibilities, name the ratio between them
in the same breath. The ratio is what tells you whether the question
was worth asking at all.

<div class="rule" id="ratio-triage">
<span class="rule-id">Rule 1 · Ratio triage</span>
Sort your next questions by the spread between their possible answers.
A question whose answers differ by 10× splits the world. Ask it now.
A question whose answers differ by less than 2× is a detail, and
asking it early is procrastination wearing a lab coat.
</div>

## 1.2 The Axioms

Here is the part nobody quite says out loud. Some of this we cannot
derive. Not because we aren't clever enough, but because there is
nothing underneath it to derive *from*.

A cache line is 64 bytes because somebody, once, in a meeting, chose
64. DRAM latency is whatever physics and market economics happened to
settle on between them. There is no first-principles path to either
number. You just have to know it, the way you know a stop sign is red.

So let's take them as given. There is no shame in being handed a
constant. The only real shame is needing to be handed the conclusion
too.

| Path | Throughput |
|---|---|
| memory copy, single core | ~10 GB/s |
| NVMe SSD | ~2 GB/s |
| spinning disk | ~150 MB/s |

A dozen numbers roughly like these make up most of the toolkit. Twelve
numbers. That's it. What we do with them is the entire skill.

## 1.3 Doing the Division

One megabyte, three plausible paths home.

Before you read on, write down what you think the answer is. I mean it,
actually write it down. Not because the arithmetic is hard, but because
committing to a value you might be wrong about is the whole exercise,
and reading past this sentence without doing it is how you get the
comfortable feeling of learning without any of the learning.

```
1 MB ÷  10 GB/s  =  100 µs     memory copy
1 MB ÷   2 GB/s  =  500 µs     NVMe
1 MB ÷ 150 MB/s  =  6.7 ms     spinning disk
```

Now let's put those next to the thing we actually measured.

<img class="ruler-chart" src="img/ruler-01-five-microseconds.svg" alt="Log-scale ruler: 5 microseconds measured, versus 100 microsecond memcpy, 500 microsecond NVMe write, and 6.7 millisecond disk write floors. The measurement lands to the left of every candidate.">

Sit with that a moment, because it is not the outcome anybody was set
up to expect.

Five microseconds beats every option on the list. Every one. Including
the option that never touches storage at all. So the conclusion is not
"it must be in memory." The conclusion is much better than that:
**our list of candidates was wrong.**

The ratio test did not just rank our candidates against each other. It
caught that the question itself was malformed. Nobody told us we were
buying that when we started dividing, and it is the most useful thing
in the chapter.

<div class="rule" id="floor-test">
<span class="rule-id">Rule 2 · The floor test</span>
When a measurement beats your theoretical floor, the system is not
fast. The work did not happen.
</div>

Let me digress for a paragraph, because this rule has a family
resemblance to something you have probably already lived through.

Years ago I watched somebody optimize a numerical loop and report a
speedup of about four hundred times. Four hundred! Everyone was
delighted. There was a graph. What had actually happened was that the
result of the loop was never read, so the compiler noticed this and
deleted the entire computation, and the benchmark was faithfully timing
an empty program. The number was real. The measurement was honest. The
work had simply not occurred.

That is the same rule as the one in the box, wearing different clothes,
and it is why I trust it more than almost anything else in this book. A
result that is too good does not mean you won. It means you should go
looking for the step that got skipped. Nobody moved a megabyte anywhere
in five microseconds, and now we get to find out what got skipped.

## 1.4 Turning It On Our Own Answer

The textbook reflex here is *page cache*. The kernel took the bytes,
parked them in its own memory, and returned without ever touching the
device. Deferred write-back. It is clever, it is well documented, and
it feels like an answer the instant you say it out loud.

So let's turn the floor test on it, exactly the way we would turn it on
somebody else's claim.

Copying into page cache is still a memory copy. It is still a megabyte
moving through a single core at ten gigabytes a second. That is 100 µs,
a number we derived four paragraphs ago and now get to reuse for free.

<div class="aside">
This is the move that separates knowing the vocabulary from being able
to use it. The floor test does not get to sit on a shelf, waiting for
other people's claims. It applies to your own favourite answer, and it
should be aimed there first.
</div>

Page cache is **twenty times too slow** to explain what we saw.

It does not survive contact with our own arithmetic. Not because we
read something that contradicted it, not because an expert corrected
us, but because numbers we already had in hand would not let it stand.
That is a lovely way to be wrong. It costs nothing and it happens in
ten seconds.

So the kernel never copied our data either. Which leaves something
stranger and more interesting. Maybe nothing copied it at all.

## 1.5 Reading the Band

We have a floor. Now let's get a ceiling, coming at it from the other
direction.

```
plain function call, off the stack  ~1–5 ns
null syscall (post-Spectre)         ~0.5–5 µs
1 MB memcpy                         ~100 µs
```

Five microseconds is a thousand times too slow for a bare function
call, and twenty times too fast for the copy. It is wedged between two
floors, and that particular gap has a name.

**One to ten microseconds is the signature of a syscall that did some
bookkeeping and handed the real work off.** It crossed into the kernel,
wrote something into a queue, and came straight back without moving
your bytes anywhere at all. That is an asynchronous submission:
`io_uring`, or something in that family.

Now, there is a second candidate here that feels just as good as the
first one did, and I want to name it precisely so we can watch it fail.
Maybe no syscall happened. `fwrite`, `BufWriter`, and the default file
API in nearly every language keep your bytes in your own process's
memory and defer the syscall until there is enough to make the trip
worthwhile.

All of that is true. And it is still not an explanation for this
measurement.

Buffering does not make the megabyte disappear. It copies it somewhere
closer, and a copy into a userspace buffer is a copy, and we know what
a megabyte of copying costs because we derived it two sections ago:
100 µs. To return in five, that copy would have to run at roughly
200 GB/s through a single core. That is an order of magnitude past
what any core can do.

So the floor test takes this one too.

<div class="aside">
That is three times in one chapter that the same 100 µs has been used
to set something aside, and twice that it has taken an answer we liked.
Reusing one derived floor against every new candidate, especially your
own, is most of the method. You are not accumulating facts. You are
accumulating one number and pointing it at things.
</div>

What survives is the asynchronous submission: a syscall that queued a
pointer and returned without touching the bytes.

And here is a detail I find genuinely delightful. Buffering explains
plenty of fast returns, just smaller ones. Ask for four kilobytes
instead of a megabyte and the copy costs well under a microsecond, and
buffering becomes the likeliest answer in the room. The mechanism we
land on depends on the size we asked about. Which is why the megabyte
was in the question at all, and why "how fast is a write" is not a
question that has an answer.

## 1.6 Resisting `strace`

Here is where most of us reach for a tool. I want you to resist for one
more second, and ask what the tool would actually buy.

We are separating "no syscall," which is nanoseconds, from "syscall
that enqueued," which is microseconds. Three orders of magnitude apart.
No amount of measurement noise, scheduler jitter, or thermal drift
closes a 1000× gap. **The stopwatch already answered it.**

<div class="rule" id="instrument-precision">
<span class="rule-id">Rule 3 · Match the instrument to the ratio</span>
1000× apart, use a wall clock. 20× apart, use a wall clock carefully.
1.5× apart, now you need counters and statistics. Reaching for a
profiler on a 1000× gap isn't rigor. It's procrastination that
produces artifacts.
</div>

For the day you genuinely need them: `strace -c` counts syscalls,
`perf trace` times them. They are excellent tools and you should need
them far less often than you think.

## 1.7 So Where Is It

Four layers, in the order they would survive:

```
   YOUR PROCESS
 ┌──────────────────┐
 │ userspace buffer │  gone if your process crashes
 └──────────────────┘
          │  write()        ~1–5 µs
          ▼
   THE KERNEL
 ┌──────────────────┐
 │   page cache     │  survives a crash
 └──────────────────┘  DIES on power loss
          │  fsync()        ~100 µs – 10 ms
          ▼
   THE DEVICE
 ┌──────────────────┐
 │   drive cache    │  still volatile
 └──────────────────┘
          │
          ▼
 ┌──────────────────┐
 │  FLASH / PLATTER │  actually durable
 └──────────────────┘
```

At five microseconds, you are at level one. Not two. Not four.

Now, the names in that diagram are worth complaining about for a
moment. `write()` is the syscall that *leaves* userspace, which the
name rather undersells. Your data lands in page cache. And `fsync()` is
not "send it to the kernel," because it is already there. `fsync` is
what pushes it *out* of the kernel, toward the media.

Most people know about `fsync`. What catches people off guard is
subtler, and it is the thing I would tattoo on a wall if I could: the
default path in nearly every file API stops one level short of durable,
and you have to opt into that last step on purpose. Closing a file
flushes userspace into the kernel. It does not sync.

Which sets up everything in Part II. That last arrow turns out to be
expensive enough that entire database architectures exist for no reason
other than to avoid taking it more often than they must.

<div class="aside">
<strong>Run it.</strong> <code>experiments/01_write_latency.c</code> writes
a megabyte four ways and prints each one against the floors above. Commit
to your four numbers before you run it. See <a href="./experiments.md">Experiments</a>.
</div>

<div class="challenges">

## Challenges

No answers here, on purpose. Re-deriving is the point. If you wanted to
re-read, you would have the chat log.

1. You measure a 4 KB write at 900 ns. Which layer is it at, and what
   floor did you use to decide?

2. Your service acks a client immediately after `write()` returns.
   Name the exact failure that loses acknowledged data, and the one
   that doesn't.

3. A colleague says an optimization made the write path "three times
   faster." Using Rule 3, what's the first thing you'd ask, and what
   would make you reach for `perf` instead of a stopwatch?

4. `fsync` on NVMe costs ~100 µs. `write()` costs ~5 µs. Derive the
   maximum sustainable durable-write rate for a system that syncs once
   per request, and explain why real databases beat that number anyway.

</div>

<div class="challenges" id="design-note">

## Design Note: Procrastinating With Rigor

There is a specific failure mode that looks exactly like diligence, and
I have fallen into it more than once.

You have a question. Instead of estimating an answer, you instrument.
Flame graphs. Tracing. A benchmark harness. An argument with a
colleague about statistical significance. Three days later you have
beautiful data about something a single division would have settled in
ten seconds, and the worst part is that everyone involved feels good
about it, because it looked like the careful thing to do.

The tell is that you never wrote down what you *expected*.

Instrumentation without a prediction has no failure condition. Every
result looks interesting. Nothing is surprising. And you learn
remarkably little, because nothing you believed was ever put at risk.
That is the whole trick of it: the process feels rigorous precisely
because it cannot fail.

The discipline is cheap and it stings a little. Before you measure,
commit to a number. Not "faster." Not "I expect an improvement." A
number, with units, that you would be a little embarrassed to be wrong
about by 10×.

Being wrong that way is what makes a lesson stick. I know which of my
numbers were wrong by 10× and I do not remember a single one I got
right.

</div>
