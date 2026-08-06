# Where the Truth Stops

> Torn writes, CRC, and finding the edge of what survived.

<img class="chapter-illustration" src="img/illus-06-where-the-truth-stops.png" alt="A puzzled scribe holding up a scroll that ends halfway down in a ragged torn edge, peering over the top of it.">

Picture recovery scanning a log forward from the last checkpoint. It
reaches the final record. There is a valid magic byte. There is a
length field reading 200. And there are 200 bytes following it that
parse cleanly into a well-formed record.

Every check passes. The record is fiction.

The first 71 bytes are real: they made it to disk before the crash. The
remaining 129 are whatever happened to be occupying that block before
this write ever started. And nothing about the record's *structure*
tells us where the truth stops and the leftovers begin.

<p class="quip">Corruption that looks like corruption is a gift. Nobody ever writes a postmortem about the bytes that looked wrong.</p>

That is the thing I want you to sit with. Torn writes do not announce
themselves. They do not arrive corrupted-looking. They look like data,
because they are data. They are just somebody else's.

## 6.1 Two Candidates and a Missing Number

If structure cannot tell us where the record stops, we need to ask what
can. There are two answers, and they differ in a way we can put a number
on, which is the whole reason to prefer one.

The first: trust the framing. If the magic bytes check out and the
length field points at something parseable, the record is real.

The second: do not trust framing at all. Verify the content.

The ratio that separates them is a coincidence rate, and it is a
lopsided one. Structural framing has no floor on how often it
accidentally looks right. A length field is two to four bytes. When a
device has whole sectors of stale data sitting immediately behind your
last good write, the odds of *some* short field reading as a plausible
small number are not remotely negligible. They are not even small.

A 32-bit checksum has a known, tiny coincidence rate: roughly **1 in
4,294,967,296** that an altered message hashes to the same value by
chance.

Four billion to one against, versus whatever the stale bytes happen to
look like today. That is not a close call, and it is not a judgement
call either.

## 6.2 The Axioms

So we want an arithmetic check rather than a structural one. Before we
build it, here is what the standard one actually promises, because the
guarantees are sharper than most people expect and the one gap in them
is the whole of section 6.4.

| Property | Value |
|---|---|
| CRC-32 catches | all 1-bit and 2-bit errors, all odd-count bit errors, all burst errors ≤ 32 bits |
| CRC-32 misses (random corruption, non-adversarial) | ~1 in 2³² ≈ 4.3 billion |
| Computation | remainder of polynomial long division, in GF(2): XOR instead of subtract, no carries |

The mechanism here is arithmetic, not heuristic, and that distinction
is the reason it does not share framing's blind spot. A CRC does not
care whether the bytes *look* like a record. It has no opinion about
what a record looks like. It only cares whether they divide down to the
value the writer committed to before the crash.

## 6.3 Doing the Division

<p class="quip">Long division, with subtraction swapped for XOR. You already know how to do this; you just did not know it had a Galois field in it.</p>

I want to do this by hand. Not because you will ever need to, but
because "it's just arithmetic" is the sort of phrase that stays
abstract forever unless somebody makes you watch it happen once.

Take the message `1101011011` and the generator polynomial `x⁴+x+1`,
which is `10011`, degree 4, so a 4-bit CRC. Append four zero bits and
divide, XOR-ing the generator in wherever the leading bit is 1:

```
  11010110110000    ← message with 4 zero bits appended
  10011              XOR (leading bit at pos 0 is 1)
  ───────────
  01001110110000
   10011             XOR (leading bit at pos 1 is 1)
   ───────────
  00000010110000                     (pos 2–5: leading bit 0, skip)
        10011        XOR (leading bit at pos 6 is 1)
        ───────────
  00000000101000
          10011       XOR (leading bit at pos 8 is 1)
          ───────────
  00000000001110

  remainder: 1110   ← the CRC
```

That is long division. The kind you learned at nine years old. The only
difference is that subtraction has been replaced by XOR, so there are
no carries and no borrowing, which if anything makes it easier than the
version they taught you.

That 4-bit remainder ships alongside the message. On read-back we run
the same division over the record *including* its stored remainder, and
a clean write divides evenly and lands on zero.

<p class="quip">Four billion to one is a comfortable margin. It is also a number you will meet in person if you write enough records.</p>

A torn write, real bytes followed by stale ones, essentially never
does. And the reason is worth stating plainly: the stale tail was not
chosen to satisfy this particular division. It was chosen by whatever
used to live on that block, months ago, by a process that had never
heard of us.

<div class="rule" id="checksum-the-edge">
<span class="rule-id">Rule 8 · Checksum every record; seed the register nonzero</span>
Torn writes don't fail structural checks; they pass them by accident.
Only an arithmetic check, computed over the content, reliably finds
where the truth stops.
</div>

## 6.4 What This Rules Out

This rules out "trust the length field" as a recovery strategy. Good.

But it also sets a trap for the checksum itself, and I want to walk
into it deliberately, because it is the most satisfying mistake in this
book.

**Start the division register at zero, and an all-zero payload always
produces an all-zero remainder.**

Work it through with the long division above. If every bit of the
message is zero, the leading bit is never 1, so the divisor never gets
XORed in, not once. Zero goes in. Zero comes out. Every time.

Now, you might reasonably file that as a corner case not worth worrying
about. I would like to talk you out of that, because zeroed blocks are
one of the *most common* shapes a torn write takes. Plenty of
filesystems and devices hand back zero-filled bytes for storage that
was allocated but never written. This is not exotic. This is Tuesday.

<p class="quip">Zero is the most popular number in computing, and every check you write should be asked what it does when handed a great many of them.</p>

So picture the crash that leaves us a real header, followed by all
zeros where the payload and the checksum should be. The zero-seeded CRC
computes 0. It reads the stored trailer, which is also 0. It declares a
match.

And there it is: corruption that *looks* valid, which is the exact
failure this chapter opened with, sneaking back in through the one
mechanism we built specifically to catch it. We did not fail to check.
We checked, carefully, with real arithmetic, and the arithmetic said
yes.

The fix is one line. Seed the register with a nonzero value before you
start. CRC-32's standard does exactly this, with `0xFFFFFFFF`. An
all-zero message no longer produces an all-zero result, the degenerate
case that used to sail through now perturbs the register, and it gets
caught like anything else.

<p class="quip">Thirty-two bits of careful mathematics, defeated by a block of nothing at all, and fixed by starting somewhere other than nothing.</p>

One line. And you only ever find it by asking what your own check does
on its worst input, rather than on a typical one.

## 6.5 The Pictorial

Here is what recovery sees when it walks the log and hits the crash. Two
good records, then one that passes every structural test it has and
fails the only test that counts:

```
 record 1 [ok, CRC matches]
 record 2 [ok, CRC matches]
 record 3 [header parses ✓] [71 real bytes][129 stale bytes] [CRC: NO MATCH]
                                           ▲
                                   the edge of truth
                               recovery stops replaying
                                      right here
```

<div class="aside">
Torn writes are not really the exception we defend against. They are
the default ending of a crash. Anything in flight at the moment of
failure lands somewhere between fully written and not written at all,
and recovery code has to assume the last record is exactly that, every
single time, because most of the time it will be.
</div>

<div class="aside">
<strong>Run it.</strong> <code>experiments/06_crc_zero_seed.c</code> shows
the all-zero record passing a zero-seeded check and failing a properly
seeded one. It is deterministic, so it prints the same thing on your
machine as on mine. See <a href="./experiments.md">Experiments</a>.
</div>

<div class="challenges">

## Challenges

1. A record's stored CRC matches, but the *previous* record in the log
   was itself torn and truncated the file mid-record. Does the
   matching CRC on record 3 tell you anything about whether record 3
   is really the intended next record, or just something that happens
   to parse?

2. You upgrade from a 16-bit to a 32-bit checksum. Using the
   coincidence rate from 6.1, what's the new odds of an undetected
   corruption, and at what write rate would you expect to see one
   anyway over a year of operation?

3. CRC isn't cryptographically secure: an adversary who can choose the
   corrupted bytes can make the checksum match. Under what threat model
   does that matter for a crash-recovery log, and under what model
   doesn't it?

4. Design a scheme where the checksum itself could be torn (only part
   of the trailer made it to disk) but the record is still correctly
   rejected. What has to be true about where the checksum lives
   relative to the data it protects?

</div>

<div class="challenges" id="design-note">

## Design Note: A Passing Structural Check Is a Claim, Not Evidence

Length fields, magic bytes, and sentinel values all share a property
that is easy to forget: they were written by the same process, at the
same moment, as the data they are supposed to validate.

So if that write was torn, the framing can be torn right along with it.
And a torn framing field does not reliably fail. Sometimes it just
reads as a small, plausible, wrong number, and the parser has no way to
know from the inside. The check and the thing being checked went down
together, holding hands.

A checksum breaks that circularity because it is redundant *on
purpose*. It encodes information that could only be true if the rest of
the record is also intact. That redundancy is the entire value
proposition, and it is the same argument that made PostgreSQL take its
torn-page reference from the buffer pool rather than from the file it
was protecting, back in chapter 4. Your verifier cannot come from
inside the thing you are verifying.

It is worth noticing how rarely we apply this outside of storage. Any
boundary where a producer and a much-later consumer have to agree about
what actually happened in between has the same shape, and most of them
are guarded by something that would fail exactly when it matters.

</div>
