# Experiments

A book that tells you to commit to a number before you measure owes you
something to measure with. These are the programs that check the
book's own claims, on your hardware, against your filesystem.

They live in [`experiments/`](https://github.com/Venugopalan2610/perfbook/tree/master/experiments)
in the repository.

```bash
cd experiments && make run
```

Nothing needs root. Nothing writes outside the working directory. Each
program cleans up after itself.

## Point them at the right filesystem first

This matters more than any other setting. The default is the current
directory, which is usually what you want. But run these against `/tmp`
on a `tmpfs` and you are measuring RAM, and every number that comes out
is fiction.

```bash
PERFBOOK_DIR=/mnt/nvme make run
```

Every experiment prints its kernel, filesystem, device, and whether it
detected a hypervisor before it prints a single measurement. If that
block does not say what you expected, stop there. The environment is
the result; the latency is just a number attached to it.

## What each one tests

| Program | Chapter | The claim |
|---|---|---|
| `01_write_latency` | [Five Microseconds](./01-five-microseconds.md) | A 1 MB write can return faster than any path that could have moved the bytes |
| `03_fsync_cost` | [The Barrier](./03-the-barrier.md) | fsync's cost is the round trip, not the payload |
| `06_crc_zero_seed` | [Where the Truth Stops](./06-where-the-truth-stops.md) | A zero-seeded CRC accepts an all-zero torn write |

The first two will give you different numbers than they gave me, and
that is the point. The third is deterministic: it prints the same thing
on every machine, which is what makes it checkable rather than
anecdotal.

## Your numbers will not match the book's

They are not supposed to. The axioms in these chapters are
order-of-magnitude figures for a class of hardware, and your device is
a specific one. On the machine these were developed on, a consumer NVMe
drive on ext4, `fsync` costs closer to 700 µs than the 100 µs chapter 3
quotes, because ext4 commits its journal on every sync and the drive
has no power-loss capacitor to acknowledge from.

That gap is not a problem to explain away. It is the exercise. Rule 1
says name the ratio: yours is roughly 7×, and the interesting question
is which of those two causes owns most of it.

<div class="aside">
The version of this that would embarrass you is publishing a number
without saying which drive, which filesystem, and whether a hypervisor
was in the path. That is why every program here prints all three before
it prints a measurement, and why the output block is worth pasting
whole when you compare notes.
</div>

## Method

**Percentiles, never the mean.** A mean latency averages the number you
care about with the number you care about much more. Each experiment
reports min, p50, p95, p99, and n.

**Warmup iterations, discarded.** The first few runs pay for page
faults and cold caches that steady state does not.

**The clock is measured too.** Every run prints its own
`clock_gettime` overhead. If a result is within an order of magnitude
of that figure, the result is the instrument.

## What is deliberately missing

Chapter 2 wants a power-loss test, and you cannot honestly run one from
inside the machine that is losing power. That is the chapter's whole
argument, so faking it in software would be worse than leaving it out.
It needs a managed PDU or an IPMI power cycle and a second machine to
verify from.

Chapter 5 wants concurrent writers. Chapters 7 and 8 want a GPU, and
until then the arithmetic is checkable with a calculator, which is most
of what those chapters are asking you to do anyway.
