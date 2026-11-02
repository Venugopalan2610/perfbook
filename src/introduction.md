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
thousand apart, and that is most of the time. This book does its
arithmetic on an imaginary reference machine with round values for all
of them, so that it never goes out of date, and the labs measure yours.

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

## Why the parts are named the way they are

The parts of this book are not named after technologies. They are named
after what the method keeps finding, because that is the thing worth
carrying out of it.

- **I. The Method.** Name the candidates, name the ratio between them,
  do the division, and see what survives.
- **II. Cost Has a Shape.** Most costs are a fixed price per trip plus
  a price per byte, and knowing which term dominates tells you what to
  do.
- **III. The Scarce Thing.** In every system one resource runs out
  first, and the others are worth spending freely to save it.
- **IV. Believing Your Evidence.** Tests, checks and recoveries can only
  see what they can reach, and the method has to be turned on them too.
- **V. When the Floor Is Wrong.** A measurement far from its floor
  means somebody is in the room that you did not count.
- **VI. The Old Shape.** Strip a problem of its vocabulary and write
  what it costs in symbols, and more often than not it is a problem
  somebody has already solved.

The examples come from storage in one chapter and from GPUs in the
next, on purpose. If the method only worked on storage, it would be
storage trivia dressed up as a principle. What makes it a method is that
the same four steps, applied to hardware nobody had when the storage
ideas were invented, produce the same kind of answer. Group commit and
GPU batching turn out to be the same equation. The floor test catches a
write that never reached the disk in chapter 1 and an unmodelled CPU cost in chapter
12. Paged attention turns out to be virtual memory from 1962.

The technologies in the examples will age. The tools will not, and every
rule in the book is stated so that it would still be true if every
hardware number in it moved ten times in either direction.

## What a rule is

Each chapter earns one, and each is a single sentence in a box. Chapter
1 is the exception and earns three, because it is about the method
itself and the method has three moving parts.

They are short deliberately. A rule you cannot recall at eleven at night
is not doing anything for you, and the test of whether you have learned
one is not whether you agree with it but whether you can rebuild the
derivation that produced it from the sentence alone.

Fifteen of them, collected in the [Rules Index](./rules.md), which is
the page to open when you have forgotten everything else.

## The shape of a chapter

So you can navigate: an anomaly, a number that does not fit, and in most
chapters a prediction you are asked to write down before you read on.
Two candidates and the ratio between them. A table of axioms, the
numbers handed over because they cannot be derived, on the reference
machine. The division. What that rules out, including at least one
answer we liked. A picture. A rule, which states a general tool first
and names the system as its example. A lab, where one exists, so the
surprise happens on your machine rather than mine. Four challenges with
no answers. And a design note, which is the part where I stop deriving
and tell you what I actually think.

Thirteen times. Starting with a write that returns far too quickly to
possibly have happened.
