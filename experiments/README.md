# Experiments

Every number in this book is supposed to be one you can check. These
are the programs that let you check them.

```
make run
```

That builds three experiments and runs them in order. Nothing needs
root, nothing writes outside the current directory, and each one
cleans up after itself.

## Point them at the right filesystem

This matters more than anything else here. The default is the current
directory, which is probably fine. But if you run these on `/tmp` and
`/tmp` is `tmpfs`, you are measuring RAM and every result is a lie.

```
PERFBOOK_DIR=/mnt/nvme make run
```

Every experiment prints the filesystem, device, and whether it detected
a hypervisor before it prints a single measurement. If that block does
not say what you expected, stop and fix it before reading the numbers.

## What each one is for

| | Chapter | The claim it tests |
|---|---|---|
| `01_write_latency` | [Five Microseconds](../src/01-five-microseconds.md) | A 1 MB write can return faster than any path that could have moved the bytes |
| `03_fsync_cost` | [The Barrier](../src/03-the-barrier.md) | fsync's cost is the round trip, not the payload |
| `06_crc_zero_seed` | [Where the Truth Stops](../src/06-where-the-truth-stops.md) | A zero-seeded CRC accepts an all-zero torn write |

The first two are timing experiments and will give you different
numbers than they gave me. That is the point. The third is
deterministic and prints the same thing everywhere, which is what
makes it checkable rather than anecdotal.

## Method, and why it is this way

**Percentiles, never the mean.** A mean latency is an average of a
number you care about and a number you care about much more. Each
experiment reports min, p50, p95, p99, and the count.

**Warmup runs, discarded.** The first few iterations pay for page
faults and cold caches that steady-state operation does not.

**The clock is measured too.** Every run prints its own
`clock_gettime` overhead. If a result is within an order of magnitude
of that number, you are measuring the instrument.

**The environment is printed with the result.** A latency figure
without its kernel, filesystem, device, and virtualization status is
not a result. It is an anecdote. Paste the whole block when you
compare notes with someone.

## Things that will skew your numbers

- **A hypervisor in the path.** `fsync` on a cloud VM often returns
  when the host cache has it, not when the media does. The experiments
  detect this and say so.
- **A drive with a volatile write cache.** Consumer SSDs frequently
  acknowledge a flush early. This is chapter 2's whole point, and it
  is why an `fsync` number alone does not prove durability.
- **Filesystem journalling.** `ext4` with `data=ordered` commits its
  journal on `fsync`, so you are timing two writes, not one. `findmnt`
  output in the environment block shows your mount options.
- **A laptop on battery.** Frequency scaling will make the same
  program produce different numbers ten minutes apart.

## Reproducibility, honestly

`Dockerfile` pins the compiler and the base image, which makes the
*build* reproducible. It does not make the *measurement* reproducible,
because the storage stack under the container is still whatever your
machine has, plus an overlayfs layer that your host does not have.

Use it for a consistent toolchain, bind-mount a real directory, and
read the environment block. Do not use it to claim your numbers match
someone else's.

## What is not here yet

- **Chapter 2 (The Ladder)** wants a power-loss test. You cannot do
  that honestly from inside the machine losing power, which is the
  chapter's entire argument. It needs a managed PDU or an IPMI
  power-cycle and a second machine to verify from.
- **Chapter 5 (Group Commit)** wants a load generator with real
  concurrent writers.
- **Chapters 7 and 8** want a GPU, and the arithmetic is checkable
  with a calculator in the meantime.
