# Preface

This book is about an argument most of us lose.

Ask an engineer why an `fsync` is slow, and you get the answer everyone
gives, which is that it goes to the disk and disks are slow. Then ask
how slow. Almost nobody knows. We know the shape of the answer and not
the number, and not knowing the number means we do not really know
anything at all, because the number is very often orders of magnitude
away from where intuition has quietly parked it. I know, because mine
was parked there too.

So the book divides. Not measuring: dividing. And what is surprising
is how far you can get on a page of long division and a dozen constants
you already half remember. Most of the questions I had been treating as
research questions turned out to be arithmetic questions wearing a
disguise, and the arithmetic took ten seconds.

That is the whole book. Thirteen chapters of it.

## Nothing is taken on authority

Where a number genuinely cannot be derived, and there are plenty of
those, it arrives in a table labelled **The Axioms**, handed over
explicitly. A cache line on most x86 processors is 64 bytes because
somebody once chose 64.
There is no first-principles path to that, and pretending otherwise
would be a lie in a book whose whole premise is not lying about where
knowledge comes from. For the same reason, where an argument leans on an
interface's promise or on somebody else's published result, the page
says so and gives you the source, so that you can check it instead of
trusting me.

Everything else is derived in front of you, including the parts where
the derivation sets aside an answer I liked. I got things wrong writing
this, and where the recovery taught more than the correction would have,
I left the wrongness in and showed the recovery. Chapter 11 walks
deliberately into a checksum that certifies its own failure.

## Why bother, when you could just ask

Because you would get an answer, and an answer is not the same thing as
judgment.

Ask a good model why your writes are slow and it will tell you about
page cache, write-back, and `fsync`, and every word of it will be true,
and you will be no better at the next question than you were at this
one. Knowledge really is one sentence away now. What is not one sentence
away is knowing which sentence to ask for, and that is a skill you build
only by doing the arithmetic yourself and occasionally being wrong by a
factor of a thousand in a way you remember for years.

I would rather hand you the habit than the facts. The facts are cheap
and getting cheaper.

## How to read it

Straight through, once. After that, not by rereading. Rereading a
technical book feels productive and teaches almost nothing, because
recognition is not recall and your brain is extremely willing to confuse
the two.

Open the [Rules Index](./rules.md) instead. Fifteen sentences, one per
rule, each linking back to the derivation that earned it. Pick one and
try to rebuild the argument from the sentence alone. If you can, you
have just proved it to yourself in a way no amount of rereading would.
If you cannot, follow the link, and that failure is the most useful
thing that will happen to you that day.

The [Challenges](./challenges.md) page collects every question in the
book with no answers attached, and that is permanent. Several cannot be
answered from their own chapter at all and need something from a later
one, or from outside the book entirely. Those are the good ones.

## What it is not

Not a tuning manual: there is no list of flags to set. Not
comprehensive: thirteen chapters cannot cover storage, let alone storage
and accelerators, and I chose depth on a few numbers over coverage of
many. Not benchmarks: every experiment checks a *ratio* or an
*invariant* rather than an absolute latency, because latencies belong to
your hardware and ratios belong to the world.

When you want to stop reading and run something, the
[Experiments](./experiments.md) check the book's own claims on your
machine, and [The Course](./course.md) is thirty-five stages that build the
inference engine that Parts II, III and V derive. Commit to your number
before you run either. That is the entire exercise, and it stings a little every time.
