# Experiments

A book that tells you to commit to a number before you measure owes you
something to measure with. These are the programs that check the
book's own claims, on your hardware, against your filesystem.

They live in [`experiments/`](https://github.com/Venugopalan2610/perfbook/tree/master/experiments)
in the repository.

```bash
cd experiments && ./run-labs.sh    # check every claim
cd experiments && ./predict.sh     # commit to a number first
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
PERFBOOK_DIR=/mnt/nvme ./run-labs.sh
```

Every experiment prints its kernel, filesystem, device, and whether it
detected a hypervisor before it prints a single measurement. If that
block does not say what you expected, stop there. The environment is
the result; the latency is just a number attached to it.

## Part IV is a separate repository

Chapters 9 through 12 derive an inference engine, and deriving it is as
far as prose can honestly take you. The build lives in
[vllm-from-scratch](https://github.com/Venugopalan2610/vllm-from-scratch):
twenty stages, each gated on a measurement rather than on your code
merely running.

```bash
gh repo fork Venugopalan2610/vllm-from-scratch --clone
cd vllm-from-scratch && ./setup.sh
./vc guide
```

It is the same contract as the labs here, scaled up. A stage does not
pass because the code executes; it passes because continuous batching
used under 60% of the forward passes static batching needed, or because
your Triton kernel beat your PyTorch one by more than 3x while agreeing
with it to 1e-3. The chapters tell you which number matters. The stages
will not let you past until yours moves.

| Chapter | Stages |
|---|---|
| [The Ridge](./07-the-ridge.md) | 01–03, the naive loop and the roofline |
| [The Cache That Ate the Batch](./08-kv-cache.md) | 02, KV bytes per token |
| [The Slot That Waited](./09-the-slot-that-waited.md) | 04–05, static then continuous batching |
| [A Page Table for Tokens](./10-a-page-table-for-tokens.md) | 06–09, blocks, paged attention, prefix cache |
| [Below the Floor](./11-below-the-floor.md) | 03 and 12, the gap and CUDA graphs |
| [Spending the Idle](./12-spending-the-idle.md) | 17, the n-gram proposer and rejection sampler |

The remaining stages (10, 11, 13 through 16, 18 through 20) build the
scheduler, chunked prefill, the sampler, the detokenizer, the server,
quantization, guided decoding and tensor parallelism. No chapter derives
those yet.

## What each one tests

| Lab | Chapter | Claims |
|---|---|---|
| `02_ladder_survival` | [The Ladder](./02-the-ladder.md) | 3, exact byte counts |
| `03_fsync_cost` | [The Barrier](./03-the-barrier.md) | 3, all ratios |
| `05_group_commit` | [Group Commit](./05-group-commit.md) | 4, ratios, at two arrival rates |
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

## The GPU labs, on a free Colab T4

Chapters 7 and 8 turn on a ratio between a GPU's compute throughput and
its memory bandwidth, so checking them needs a GPU. Colab's free tier
has one, which puts these within reach of anyone.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Venugopalan2610/perfbook/blob/master/experiments-gpu/colab.ipynb)

They do not trust the datasheet. Vendor peak figures are marketing, and
the ridge point is a division of two of them, so the labs measure your
card's bandwidth with a large copy, measure its matmul throughput with a
large matmul, and divide. The ridge you get is yours.

| Lab | Chapter | Claims |
|---|---|---|
| `07_roofline` | [The Ridge](./07-the-ridge.md) | 5, ratios and shapes |
| `08_kv_cache` | [The Cache That Ate the Batch](./08-kv-cache.md) | 5, mostly exact |

`07` sweeps a batch size from 1 to 256 across a 4096 by 4096 weight
matrix and reports both arithmetic intensity and the fraction of the
card's own peak it reaches. On the laptop card these were built
against, the measured ridge was 183 FLOP/byte, batch 1 landed at
1.0 FLOP/byte and 1.3% of peak, and batch 256 effectively saturated it.
A T4's numbers will be much smaller and every claim will still hold,
because the claims are ratios.

`08` checks the 512 KB per token by allocating a real KV cache and
asking CUDA what it cost, rather than trusting the multiplication. It
also measures that Grouped-Query Attention with 8 query heads per KV
head divides that figure by exactly 8.

<div class="aside">
You do not need a card big enough to hold a 7B model. Bytes per token
is measurable on any GPU, and the ceiling for larger cards follows by
division. The lab prints the ceiling for whatever card you are on,
which on a 12 GB laptop is a blunt lesson.
</div>

## What is deliberately missing

Chapter 2 wants a power-loss test, and you cannot honestly run one from
inside the machine that is losing power. That is the chapter's whole
argument, so faking it in software would be worse than leaving it out.
It needs a managed PDU or an IPMI power cycle and a second machine to
verify from.

Nothing else, for now. Chapter 4's write-ahead argument is checked
indirectly by chapters 2 and 3's labs, since it is built on their two
results rather than on a measurement of its own.
