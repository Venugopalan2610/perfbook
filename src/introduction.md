# Introduction

Here is a scene you have been in.

Something is slower than it should be. Six people are in a room, or a
thread, and within about ninety seconds somebody has opened a profiler.
Within ten minutes there is a flame graph. Within a day there is a
benchmark harness and a disagreement about statistical significance, and
by the end of the week there is a great deal of beautiful data and no
decision.

Nobody in that room did anything wrong. Every step was reasonable. But
somewhere near the start, a question got asked that a single division
would have settled in ten seconds, and instead of dividing, everybody
instrumented.

I want to make the case that this is the normal failure, not the
exceptional one, and that the fix is smaller and less impressive than
you would like.

## The claim

Most performance questions are settled by arithmetic you can do on
paper.

Not all. Some genuinely need counters and careful statistics, and
chapter 1 gives you a rule for telling which is which. But the ordinary
case, the "why is this slow" that arrives on a Tuesday, is usually a
question about which of two or three things dominates, and the things
being compared are usually so far apart that a rough calculation
separates them completely.

When candidates sit a thousand times apart, no amount of measurement
noise closes the gap, and the stopwatch already knew the answer. Reaching
for a profiler at that point is not rigour. It produces artifacts and
consumes a week, and the week is the real cost.

## What you actually need

Two things, and neither is a tool.

**A dozen constants.** Memory bandwidth, roughly. NVMe write bandwidth,
roughly. What an `fsync` costs. What a syscall costs. Cache line size.
The bandwidth and peak compute of whatever accelerator you own. Rough is
fine. Being within a factor of two is plenty when the candidates are a
thousand apart, and that is most of the time.

**The willingness to commit to a number before you check.** This is the
part people skip, and skipping it is why measurement so often teaches
nothing. If you write down "I think 300 microseconds" and it comes back
at 5, you have learned something violent and permanent about your mental
model. If you write down nothing and it comes back at 5, you nod and
move on, and next year you will make the same mistake with the same
confidence.

Prediction is what converts a measurement into a lesson. Without it you
are collecting numbers, and numbers are not understanding.

## The method

Every chapter in this book runs the same loop, and it is short enough to
memorise.

**Name the candidates.** Where could the truth plausibly be? Two or
three answers, stated plainly, before you have any attachment to which
one wins.

**Name the ratio between them, in the same breath.** This is the move
everything else rests on. Not "disk is slower than memory," which is a
direction and cannot decide anything. *How much* slower. A question
whose answers differ by a factor of a thousand splits the world and
should be asked immediately. A question whose answers differ by less
than two is a detail, and asking it early is procrastination wearing a
lab coat.

**Do the division.** Take your dozen constants, work out what each
candidate would cost if it were true, and compare that against what you
actually measured.

**See what survives.** Usually one candidate is off by orders of
magnitude and goes. Sometimes, and these are the best chapters, *none* of
them survive, which tells you the question itself was malformed and you
have just learned something you were not looking for.

That is it. There is nothing else in the bag.

## Why the ratio, and not the answer

Because the ratio tells you whether the question was worth asking at
all, and the answer does not.

If two candidates differ by 1.3×, then it does not much matter which is
right, and any effort spent separating them is effort not spent on the
thing that differs by 400×. Sorting your questions by the spread between
their possible answers is the cheapest triage available, and almost
nobody does it, because it feels like a step you can skip on the way to
the real work.

It is the real work. The rest is division.

## Why storage, and then GPUs

The book is in four parts. Parts II and III look like they belong to
different fields: one is about `fsync` and torn writes and crash
recovery, the other is about arithmetic intensity and KV caches and
tokens per second. Different decade, different hardware, different
vocabulary, different conferences.

They are here together on purpose.

If the method only worked on storage, it would be storage trivia dressed
up as a principle. What makes it a method is that the same four steps,
applied to a GPU nobody had when the storage chapters' ideas were
invented, produce the same kind of answer. Group commit and GPU batching
turn out to be the same trick. The floor test catches a fraudulent
benchmark in chapter 1 and an unmodelled CPU cost in chapter 11.
PagedAttention turns out to be virtual memory from 1962.

That is the actual claim of the book, and it is why the two halves sit
next to each other rather than in two books.

## What a rule is

Each chapter earns exactly one, and each is a single sentence in a box.

They are short deliberately. A rule you cannot recall at eleven at night
is not doing anything for you, and the test of whether you have learned
one is not whether you agree with it but whether you can rebuild the
derivation that produced it from the sentence alone.

Fourteen of them, collected in the [Rules Index](./rules.md), which is
the page to open when you have forgotten everything else.

## The shape of a chapter

So you can navigate: an anomaly, a measurement that does not fit. Two
candidates and the ratio between them. A table of axioms, the numbers
handed over because they cannot be derived. The division. What that
rules out, including at least one answer we liked. A picture. A rule.
Four challenges with no answers. And a design note, which is the part
where I stop deriving and tell you what I actually think.

Twelve times. Starting with a write that returns far too quickly to
possibly have happened.
