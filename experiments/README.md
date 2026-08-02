# Labs

Every number in this book is meant to be one you can check. These are
the programs that check them, on your hardware, and tell you plainly
whether the book's claims held.

```
./run-labs.sh          # check every claim
./predict.sh           # commit to a number first, then check
```

Exit code 0 means every claim held. Nonzero means one did not, and the
output says which. Nothing needs root, nothing writes outside the
working directory, and each lab cleans up after itself.

## Why these are labs and not benchmarks

A benchmark prints a number. You cannot tell a correct run from a
broken one, and you cannot compare your run to mine, because your
drive is not my drive.

So these do not assert absolute numbers. They assert **ratios** and
**exact invariants**, which are the things that survive a change of
hardware:

- A 700 µs fsync and a 100 µs fsync are both perfectly normal.
- An fsync that costs the same as a buffered write means you are not
  measuring storage at all, and every conclusion below it is void.

That second statement is a claim, so it is a check. Run these against
a `tmpfs` and `measuring-real-storage` fails with a real error rather
than quietly reporting that RAM is very fast storage.

## Where the data has been, located by survival

`02_ladder_survival` is the one that pins down location. It forks a
writer, kills it with `SIGKILL` at three different moments, and counts
what is left on disk:

| killed after | survives | so the bytes were |
|---|---|---|
| `fwrite` | 0 bytes | in the process's own memory, rung 1 |
| `fwrite` + `fflush` | all of them | in the kernel's page cache, rung 2 |
| `fwrite` + `fflush` + `fsync` | all of them | at least rung 2; this test cannot see further |

Those byte counts are identical on every Linux machine, which is what
makes them checkable rather than anecdotal. The third row is the
interesting one: it passes, and it proves nothing the second row did
not. A test that cannot reach rung 3 tells you nothing about rung 3.
That is Rule 4, and the lab is a worked example of the mistake it
warns about.

An earlier version of this lab tried to locate the data with
`mincore()` and `posix_fadvise(DONTNEED)`. That approach was dropped:
a control file written with `O_DIRECT`, which by definition never
enters the page cache, still reported 100% resident. The probe was
measuring itself. Survival is cruder and correct.

## The labs

| Lab | Chapter | Claims checked |
|---|---|---|
| `02_ladder_survival` | The Ladder | 3, all exact byte counts |
| `03_fsync_cost` | The Barrier | 3, all ratios |
| `06_crc_zero_seed` | Where the Truth Stops | 6, all exact, including a CRC-32 known-answer test |
| `05_group_commit` | Group Commit | 4, ratios, at two arrival rates |
| `01_write_latency` | Five Microseconds | timing survey, no pass/fail yet |

`06` proves its own CRC against the IEEE 802.3 vector for `123456789`
before it claims anything, so the zero-seed finding cannot be blamed
on a broken implementation.

## Point them at the right filesystem

This matters more than anything else here.

```
PERFBOOK_DIR=/mnt/nvme ./run-labs.sh
```

The default is the current directory. Run these on `/tmp` when `/tmp`
is `tmpfs` and you are measuring RAM. The labs will catch it, but it
is faster to point them somewhere real to begin with.

## results.json

Every run appends to `results.json`: a manifest, then one object per
lab.

The manifest records the git commit, whether the tree was dirty, the
compiler version, and a SHA-256 prefix of every source file. Each lab
object records the kernel, the mount line, whether a hypervisor was
detected, and every claim with its observed value, its bound, and
whether it held.

Send that file, not a screenshot. It is the difference between "it was
fast on my laptop" and a result someone else can argue with.

## What will move your numbers

- **A hypervisor.** `fsync` on a cloud VM often returns when the host
  cache has it, not the media. Recorded in every lab object.
- **A volatile drive write cache.** Consumer SSDs acknowledge flushes
  early. That is chapter 2's point, and it is why an `fsync` latency
  alone never proves durability.
- **Filesystem journalling.** `ext4` with `data=ordered` commits its
  journal on `fsync`, so you are timing two writes. The mount options
  are in the output.
- **A laptop on battery.** Frequency scaling will change the same
  program's numbers ten minutes apart.

## Reproducibility, stated honestly

`Dockerfile` gives you a consistent toolchain, and carries
instructions for pinning the base image by digest. It ships unpinned
on purpose: a digest that was never verified fails to pull in a way
that looks like your mistake rather than mine.

It does not make the **measurement** reproducible. The storage stack
under a container is still your machine's, plus an overlayfs layer
your host does not have, and on Docker Desktop everything runs inside
a Linux VM whose virtual disk is what you would actually be timing.

Use it for a consistent toolchain. Bind-mount a real directory. Then
compare ratios and claim outcomes, not microseconds.

## predict.sh

Chapter 1's design note argues that instrumentation without a
prediction has no failure condition: every result looks interesting,
nothing is surprising, and nothing you believed was ever at risk.

So `predict.sh` asks four questions before anything runs, then prints
your guesses beside what actually happened. Being wrong by 10x is the
normal outcome and the reason to do it.

## Not here yet

- **Rungs 3 and 4** need a real power cut: a managed PDU or an IPMI
  power cycle, and a second machine to verify from. It cannot be done
  honestly from inside the machine losing power, which is the whole
  argument of chapter 2.
- **Chapters 7 and 8** need a GPU, and now have labs for it in
  [`../experiments-gpu`](../experiments-gpu), runnable on a free
  Colab T4.
