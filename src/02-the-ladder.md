# The Ladder

> Your test suite has never once lost power.

Say we build a crash-test harness for a write path we care about.
`kill -9` the process mid-write, ten thousand times, at a random byte
offset each time. Zero bytes lost, every single run. Feels great, so we
ship it.

Six weeks later, someone runs the same workload through a power-fault
rig instead (a switch that cuts the wall socket rather than the
process), and it loses data on the very first try.

Ten thousand for ten thousand on one test. Zero for one on the other.
That's not a flaky test. It's two different questions wearing the same
word, "crash," and this chapter is about learning to tell them apart.

## 2.1 Two Candidates and a Missing Number

The natural reflex is to treat this as a probability problem: kill -9
failure is rare, power-loss failure is common, go collect more samples
and find the true rate.

Worth resisting. Let's ask Rule 1's question first: how much do the
candidate answers actually differ? Here the honest answer is that
this isn't a spread at all, it's a category error. `kill -9` removes a
*process*. A power cut removes *power to the machine*. Those aren't two
points on the same axis; they're different axes entirely. No amount of
extra sampling turns one into evidence about the other.

<div class="aside">
A sharper version of ratio triage: sometimes the "spread" between two
candidates isn't a number at all, and computing one anyway is how we
talk ourselves into a false sense of coverage.
</div>

So the real question underneath "why did these two tests disagree" is:
**what does each failure actually destroy?** Answer that, and both
results stop being surprising.

## 2.2 The Axioms

Four places a byte can live between `write()` and "safe forever." Each
one is owned by something different, and ownership is what determines
what kills it. The last three columns ask the same question of each
layer: does it *survive* this failure?

| Layer | Owned by | Process death | Kernel panic | Power loss |
|---|---|---|---|---|
| Userspace buffer | Your process | No | No | No |
| Page cache | The kernel | Yes | No | No |
| Drive write cache | The device | Yes | Yes | **Only with PLP\*** |
| Flash / platter | The device, non-volatile | Yes | Yes | Yes |

*PLP = power-loss protection, explained below.

That third row is the one nobody's intuition gets for free: consumer
SSDs and spinning disks both carry a small volatile write cache *on the
device itself*, after the data has already left the kernel. Enterprise
drives often ship power-loss protection, a capacitor sized to finish
the flush during the few milliseconds after the plug is pulled.
Consumer drives usually don't. Two drives can both report "write
complete" and quietly disagree about whether that claim survives a
power cut.

## 2.3 Doing the Division

There is arithmetic here, and it isn't the arithmetic the harness
looked like it was doing.

Ten thousand clean runs is a real statistical result. When we see zero
failures in n trials, the ninety-five percent upper bound on the true
failure rate is about 3/n, so the harness bought us a genuinely
precise number:

```
     10,000 runs, 0 failures  ->  failure rate below 1 in 3,339
  1,000,000 runs, 0 failures  ->  failure rate below 1 in 333,809
```

That is defensible, and it wasn't free. Which makes it worth being
exact about what it is a number *about*.

`kill -9` deletes a process, and a process owns row one. So every one
of those ten thousand trials was a trial of row one, and not one of
them was a trial of anything else. Run the division again with that
column added:

```
  trials that reached row 1        10,000
  trials that reached row 3             0

  95% bound, row 1 data loss   1 in 3,339
  95% bound, row 3 data loss          100%
```

Zero trials support no bound at all. After ten thousand runs, our
honest upper bound on losing acknowledged data to a power cut is one
hundred percent, exactly where it stood before the harness was
written. Ten million runs would leave it at one hundred percent too.

The test wasn't flaky and it wasn't lucky. It was accurate to three
significant figures, about row one, while the data we were worried
about lived three rows further down.

<div class="rule" id="failure-fidelity">
<span class="rule-id">Rule 4 · Test the failure you claim to survive</span>
A crash test that cannot reach the layer your data lives in has proven
nothing about that layer. Count rows before you count nines.
</div>

## 2.4 What This Rules Out

This retires a comfortable piece of folk wisdom: "we crash-test in CI,
we're covered." Covered against what, exactly? If the harness only ever
sends `SIGKILL`, it has validated exactly one row of the ladder: the
row that was never actually in danger, since page cache doesn't care
whether our process is still alive.

The claim that needed testing (*does an acknowledged write survive
losing the wall socket*) requires reaching row three or four. That
needs `fsync()` (next chapter) and a fault injector that removes power,
not signals: IPMI power-cycle, a managed PDU, a physical switch.
Nothing short of that reaches the rows where the real risk actually
lives.

## 2.5 The Pictorial

<img class="chart" src="img/survival-grid-02-the-ladder.svg" alt="Grid of four storage layers (userspace buffer, page cache, drive write cache, flash/platter) against four failure modes (kill -9, kernel panic, power loss, power loss with PLP). Checkmarks and crosses show which layers survive which failures: the same data as the 2.2 table, arranged so the failure boundary for each column is visible at a glance.">

<div class="aside">
Read each column top to bottom: the first ✗ you hit is where that
failure mode stops your data. `kill -9`'s ✗ sits at the very top.
Power loss without a capacitor puts its ✗ two rows deeper than most
test suites ever bother to look.
</div>

Five microseconds put us on row one, back in chapter 1. The rest of
this book is about what it costs, in time and in engineering, to walk
down to row four on purpose, and about not fooling ourselves into
thinking we're already there.

<div class="challenges">

## Challenges

1. Your crash harness now uses `kill -9` *and* reboots the VM (a clean
   `reboot`, not a power cut) between runs. Which row does that
   combination actually validate, and which row does it still miss?

2. A colleague proposes testing power loss by calling `echo b >
   /proc/sysrq-trigger` (immediate reboot, no shutdown sequence) instead
   of physically cutting power. Where does that sit on the ladder:
   closer to `kill -9` or closer to a real power cut? Justify it from
   what each one actually destroys.

3. An NVMe drive's spec sheet doesn't mention power-loss protection.
   What experiment would tell you whether it has it, without opening
   the case?

4. You have a fleet of machines behind a shared UPS. The UPS itself has
   a failure rate. Redraw the ladder's power-loss column as a function
   of UPS reliability. At what UPS failure rate does "no PLP on the
   drive" stop being a real risk in practice?

</div>

<div class="challenges" id="design-note">

## Design Note: Coverage Is a Claim About a Layer, Not a Count

"We have a crash test" and "we have crash *coverage*" aren't the same
sentence, and the gap between them is exactly the ladder.

A test count is seductive because it's a single number that goes up.
Ten thousand runs feels like more assurance than one hundred. But the
count only matters *after* we've established the test can reach the
failure we're actually worried about. A million `kill -9` runs against
a page-cache-only claim is a million data points about a question
nobody asked.

Before adding a zero to your run count, it's worth asking which row the
test can possibly fail at. If the honest answer is "row one," more runs
buy a tighter confidence interval on a claim you weren't worried about
in the first place. Better to redirect that effort at reaching row
three, even if the run count goes down as a result.

</div>
