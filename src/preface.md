# Preface

This book began as an argument I was losing.

Somebody asked me why an `fsync` was slow, and I gave the answer
everyone gives, which is that it goes to the disk and disks are slow.
Then they asked how slow, and I did not know. I knew the shape of the
answer. I did not know the number, and it turned out that not knowing
the number meant I did not really know anything at all, because the
number was four orders of magnitude away from where my intuition had
quietly parked it.

So I started dividing. Not measuring: dividing. And what surprised me
was how far you can get on a page of long division and a dozen constants
you already half remember. Most of the questions I had been treating as
research questions turned out to be arithmetic questions wearing a
disguise, and the arithmetic took ten seconds.

That is the whole book. Twelve chapters of it.

## The one rule I set myself

Nothing is looked up.

Where a number genuinely cannot be derived, and there are plenty of
those, it appears in a table labelled **The Axioms**, handed over
explicitly, with a note saying that it cannot be derived and you simply
have to know it. A cache line is 64 bytes because somebody chose 64.
There is no first-principles path to that, and pretending otherwise
would be a lie in a book whose entire premise is not lying about where
knowledge comes from.

Everything else is derived in front of you, including the parts where
the derivation sets aside an answer I liked.

## Why bother, when you could just ask

Because you would get an answer, and an answer is not the same thing as
judgment.

Ask a good model why your writes are slow and it will tell you about
page cache, write-back, and `fsync`, and every word of it will be true,
and you will be no better at the next question than you were at this
one. Knowledge really is one sentence away now. What is not one sentence
away is knowing which sentence to ask for, which is a skill you can only
build by doing the arithmetic yourself and occasionally being wrong by a
factor of a thousand in a way you remember for years.

I would rather hand you the habit than the facts. The facts are cheap
and getting cheaper.

## How to use it

**Not by rereading.** Rereading a technical book feels productive and
teaches almost nothing, because recognition is not recall and your brain
is extremely willing to confuse the two.

Open the [Rules Index](./rules.md) instead. It is fourteen sentences,
one per rule, each linking back to the derivation that earned it. Pick
one. Try to rebuild the argument from the sentence alone. If you can,
you are done and you have just proved it to yourself in a way no amount
of rereading would. If you cannot, follow the link, and that failure is
the most useful thing that will happen to you that day.

The [Challenges](./challenges.md) page collects every question in the
book with no answers attached. That is deliberate and it is permanent. I
am not going to publish an answer key, not in an appendix, not later.
Several of the challenges cannot be answered from their chapter at all
and need something from a later one, or from outside the book entirely.
Those are the good ones.

## What this is not

It is not a tuning manual. There is no list of flags to set.

It is not comprehensive. Twelve chapters cannot cover storage, let alone
storage and accelerators, and I chose depth on a few numbers over
coverage of many.

It is not benchmarks. Every experiment in the repository checks a
*ratio* or an *invariant*, never an absolute latency, because absolute
latencies are properties of your hardware and ratios are properties of
the world.

## A confession about the errors

I got things wrong writing this, several times, and in two places the
wrongness was more instructive than the correction. Chapter 6 walks
deliberately into a checksum that certifies its own failure. Chapter 11
is built on a measurement that misses its floor by a factor of two and
a half, which I initially took for a bad benchmark.

Where being wrong taught something, I left the wrongness in and showed
the recovery. A book that only shows finished reasoning is teaching you
what conclusions look like, which is not the thing you need.

## Two companions

The [Experiments](./experiments.md) page describes programs that check
the book's own claims on your hardware. They are small, they need no
root, and they fail loudly when a claim does not hold on your machine.
Commit to your number before you run them. That is the entire exercise
and it stings a little every time.

And Part IV hands off to
[vllm-from-scratch](https://github.com/Venugopalan2610/vllm-from-scratch),
a twenty-stage course that builds the inference engine these chapters
derive. The chapters tell you which number matters. The stages will not
let you past until yours moves.
