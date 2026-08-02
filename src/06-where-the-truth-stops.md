# Where the Truth Stops

> Torn writes, CRC, and finding the edge of what survived.

Picture recovery scanning a log forward from the last checkpoint. The
final record has a valid magic byte, a length field that reads 200, and
200 bytes follow it that parse cleanly into a well-formed record.

It's fiction. The first 71 bytes are real: they made it to disk before
the crash. The remaining 129 are whatever used to occupy that block
before this write ever started. Nothing about the record's *structure*
tells us where the truth stops and the leftovers begin, because torn
writes don't announce themselves. They just look like data.

## 6.1 Two Candidates and a Missing Number

Candidate one: trust the framing. If the magic bytes check out and the
length field points at something parseable, the record is real.
Candidate two: don't trust framing at all; verify the content.

The ratio that separates them is a coincidence rate. Structural framing
has no floor on how often it accidentally looks right. A length field
is 2–4 bytes; when a device has whole sectors of stale data sitting
right behind our last good write, the odds of *some* short field
reading as a plausible small number aren't remotely negligible. A
32-bit checksum, on the other hand, has a known, tiny coincidence
rate: roughly **1 in 4,294,967,296** for a message that's been altered
but happens to hash to the same value by chance. Four billion to one
against, versus "whatever the stale bytes happen to look like." Not a
close call.

## 6.2 The Axioms

| Property | Value |
|---|---|
| CRC-32 catches | all 1-bit and 2-bit errors, all odd-count bit errors, all burst errors ≤ 32 bits |
| CRC-32 misses (random corruption, non-adversarial) | ~1 in 2³² ≈ 4.3 billion |
| Computation | remainder of polynomial long division, in GF(2): XOR instead of subtract, no carries |

The mechanism is arithmetic, not heuristic, which is exactly why it
doesn't share framing's blind spot: it doesn't care whether the bytes
*look* like a record. It cares whether they hash to the value the
writer committed to before the crash.

## 6.3 Doing the Division

Let's do the GF(2) division by hand once, so "it's just arithmetic"
stops being an abstraction. Message `1101011011`, generator polynomial
`x⁴+x+1` (`10011`, degree 4 → a 4-bit CRC). Append four zero bits and
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

That 4-bit remainder ships alongside the message. On read-back, we run
the same division on the record *including* its stored remainder; a
clean write divides evenly and lands on zero. A torn write (real bytes
followed by stale ones) essentially never does, because the stale
tail wasn't chosen to satisfy this particular division. It was chosen
by whatever used to be on that block.

<div class="rule" id="checksum-the-edge">
<span class="rule-id">Rule 8 · Checksum every record; seed the register nonzero</span>
Torn writes don't fail structural checks; they pass them by accident.
Only an arithmetic check, computed over the content, reliably finds
where the truth stops.
</div>

## 6.4 What This Rules Out

This rules out "trust the length field" as a recovery strategy. But it
also sets a trap for the checksum itself if we're not careful: **start
the division register at zero, and an all-zero payload always produces
an all-zero remainder.** Zero in, zero out, every time: the leading
bit is never 1, so the divisor never gets XORed in at all.

That's not a corner case worth waving off. Zeroed blocks are one of the
*most common* shapes a torn write takes: plenty of filesystems and
devices return zero-filled bytes for storage that was allocated but
never written. If a crash lands us a record that's a real header,
then all zeros where the payload and checksum should be, a
zero-seeded CRC computes 0, finds the stored trailer also reading 0,
and calls it a match. The exact failure this chapter opened with,
corruption that *looks* valid, sneaks back in through the one place we
built to catch it.

The fix is one line: seed the register with a nonzero value before
starting (CRC-32's standard does this, with `0xFFFFFFFF`). An all-zero
message no longer produces an all-zero result, so the degenerate case
that used to sail through now perturbs the register and gets caught
like anything else.

## 6.5 The Pictorial

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
Torn writes aren't really the exception we defend against. They're the
default ending of a crash: anything in flight at the moment of failure
lands somewhere between "fully written" and "not written at all," and
recovery code has to assume every last record might be exactly that.
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
that's easy to forget: they were written by the same process, at the
same time, as the data they're supposed to validate. If that write was
torn, the framing can be torn right along with it, and a torn framing
field doesn't reliably fail. Sometimes it just reads as a small,
plausible, wrong number, and the parser has no way to tell from the
inside.

A checksum breaks that circularity because it's redundant *on
purpose*: it encodes information that was only true if the rest of the
record is also intact. That redundancy is the entire value
proposition, and it's worth noticing how rarely we reach for it outside
of storage. The same argument applies to any boundary where a producer
and a much-later consumer need to agree on what actually happened in
between.

</div>
