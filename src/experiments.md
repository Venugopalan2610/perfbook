# Experiments

A book that tells you to commit to a number before you measure owes you
something to measure with. These are the programs that check the
book's own claims, on your hardware, against your filesystem.

They live in [`experiments/`](https://github.com/Venugopalan2610/perfbook/tree/master/experiments)
in the repository.

```bash
cd experiments && ./run-labs.sh
```

Exit code 0 means every claim in the book that this can reach held on
your machine. Nonzero means one did not, and the output names it.
Nothing needs root, and each lab cleans up after itself.

## They check claims, not numbers

A benchmark prints a number, and you cannot tell a correct run from a
broken one. So these assert **ratios** and **exact invariants**
instead, because those are what survive the change of hardware that
absolute latency does not.

A 700 µs fsync and a 100 µs fsync are both ordinary. An fsync that
costs the same as a buffered write means you are not measuring storage
at all, and every conclusion under it is void. That is a claim, so it
is a check: run the labs against a `tmpfs` and `measuring-real-storage`
fails loudly rather than quietly reporting that RAM is quick.

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

| Lab | Chapter | Claims |
|---|---|---|
| `02_ladder_survival` | [The Ladder](./02-the-ladder.md) | 3, exact byte counts |
| `03_fsync_cost` | [The Barrier](./03-the-barrier.md) | 3, all ratios |
| `06_crc_zero_seed` | [Where the Truth Stops](./06-where-the-truth-stops.md) | 6, exact, including a CRC-32 known-answer test |
| `01_write_latency` | [Five Microseconds](./01-five-microseconds.md) | timing survey |

## Where the data has been, located by survival

`02_ladder_survival` forks a writer, kills it with `SIGKILL` at three
moments, and counts what is left:

| killed after | survives | so the bytes were |
|---|---|---|
| `fwrite` | 0 bytes | in the process's own memory, rung 1 |
| `fwrite` + `fflush` | all of them | in the kernel's page cache, rung 2 |
| + `fsync` | all of them | rung 2 at least; this test sees no further |

Those counts are identical on every Linux machine. The third row is
the instructive one: it passes and proves nothing the second did not.
A test that cannot reach rung 3 tells you nothing about rung 3, which
is Rule 4, and the lab is a worked example of the mistake that rule
warns about.

<div class="aside">
An earlier version located the data with <code>mincore()</code> and
<code>posix_fadvise(DONTNEED)</code> instead. It was dropped: a control
file written with <code>O_DIRECT</code>, which by definition never
enters the page cache, still reported 100% resident. The probe was
measuring itself. Survival is cruder and correct.
</div>

The timing labs will give you different numbers than they gave me, and
that is expected. Their *claims* should still hold, because the claims
are ratios. The exact-invariant labs print the same values on every
machine, which is what makes them checkable rather than anecdotal.

## results.json

Every run appends a manifest recording the git commit, whether the tree
was dirty, the compiler, and a hash of each source file, then one
object per lab with its environment and every claim's outcome. Send
that file rather than a screenshot. It is the difference between "it
was fast on my laptop" and a result somebody can argue with.

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
