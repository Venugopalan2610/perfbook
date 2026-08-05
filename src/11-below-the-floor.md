# Below the Floor

> Two hundred and eighty launches, and the bus waiting through all of them.

Chapter 7 established that decoding is memory-bound, and the claim came
with a promise attached: if the bottleneck is the memory bus, then the
time per token should be the time it takes to drag the weights across
it. Nothing more, because nothing else is on the critical path.

That promise is checkable, and it is worth checking on a small model
where every number is easy to hold. Take a 0.6B model in bf16, 1.19 GB
of weights, on a card whose streaming bandwidth measures 380 GB/s.

```
roofline floor  =  1.19 GB ÷ 380 GB/s  =  3.13 ms/token
measured        =                         7.80 ms/token
```

Two and a half times the floor. The card is achieving 153 GB/s of the
380 it demonstrably has, which is 40% of a bus that chapter 7 said
should be saturated. Somewhere in every token, four and a half
milliseconds are going somewhere that is not the memory bus, on a
workload we have spent two chapters describing as memory-bound.

## 11.1 Candidates and the Ratio

Candidate one: the 380 GB/s figure is a streaming-copy number, and the
weight reads in a real forward pass have an access pattern that cannot
reach it. Real achievable bandwidth for this workload is closer to 153
GB/s and the floor was always wrong.

Candidate two: the bus really does deliver 380 GB/s here, and the extra
4.67 ms is time when nothing is being read at all.

Chapter 1 gave us the tool for exactly this shape of question. Its
[floor test](./01-five-microseconds.md#floor-test) says that a
measurement beating a theoretical floor means the work did not happen.
This is that rule looked at from the other side: a measurement that
*misses* a floor by 2.5× means work happened that we were not counting.
Either the floor is wrong, or our model of what the machine is doing is
incomplete. Those are the same two candidates, and the arithmetic can
tell them apart.

## 11.2 The Axioms

| Quantity | Value |
|---|---|
| Model weights, 0.6B bf16 | 1.19 GB |
| Measured streaming bandwidth | 380 GB/s |
| Transformer layers | 28 |
| GPU operations per layer (attention, MLP, norms) | ~10 |
| CPU cost to dispatch one operation, eager PyTorch | 5–20 µs |

That last row is the one chapters 7 and 8 never mentioned, and it is not
a GPU number at all. Every kernel that runs on the card was put there by
the host: a Python call, a dispatch through the framework, a driver call
that enqueues work on a stream. The GPU does not read its own program.
Something on the CPU has to hand it each piece.

## 11.3 Doing the Division

Count the handoffs in one token.

```
operations per token  =  28 layers × ~10 ops  =  ~280 launches

unaccounted time      =  7.80 ms − 3.13 ms    =  4.67 ms
per launch            =  4.67 ms ÷ 280        =  ~17 µs
```

Seventeen microseconds per operation, which lands inside the 5 to 20 µs
the axiom table gives for eager dispatch. The gap is not a mystery
quantity we have to attribute on faith. It is 280 individual acts of the
CPU telling the GPU what to do next, each one costing about what a
Python-dispatched kernel launch costs, and together they account for the
missing time almost exactly.

<img class="chart" src="img/launch-overhead-11-below-the-floor.svg" alt="Two stacked horizontal bars of time per decode token. The eager bar is 7.8 milliseconds: 3.13 milliseconds of memory traffic and 4.67 milliseconds of CPU launch overhead. The CUDA graph bar is 3.4 milliseconds: the same 3.13 milliseconds of memory traffic and a thin remainder of replay overhead. A dashed line marks the 3.13 millisecond roofline floor.">

So candidate one is set aside. The bus is not slow; the bus is idle,
waiting for a CPU that is 280 function calls behind. Each individual
kernel, once launched, runs at full bandwidth. The problem is the gaps
between them.

<div class="rule" id="floor-gap-is-cpu">
<span class="rule-id">Rule 13 · A workload that misses its own roofline floor is not yet bound by what you think</span>
When a memory-bound workload takes materially longer than
bytes ÷ bandwidth, the extra time is on the host, not the bus. Count
launches before optimizing kernels.
</div>

## 11.4 What This Rules Out

This rules out the entire category of fix we would otherwise reach for.
Every kernel in that forward pass could be made twice as fast and the
token would still take 4.67 ms of CPU time, because the CPU work happens
between the kernels, not inside them. Optimizing a kernel that is
already bandwidth-saturated, in a step where 60% of the wall clock is
dispatch, is effort spent on the 40%.

It also rules out more bandwidth. A card with 760 GB/s halves the 3.13
ms and leaves the 4.67 ms untouched, taking 7.80 ms down to 6.23. We
would have doubled the most expensive component of the machine to buy a
20% improvement, and the profiler would still show a bus at 40%
utilization, because it would then be at 20%.

What survives is the observation that the sequence of 280 launches is
the same every single token. Same kernels, same order, same shapes, same
buffers. We are paying the CPU to make an identical set of decisions
several hundred times a second.

That is a recording problem. CUDA graphs let us capture the whole launch
sequence once and replay it as a single submission, so the host makes
one call instead of 280 and the GPU walks the recorded graph itself. The
arithmetic does not change at all. The 3.13 ms of memory traffic is
still there, still irreducible, still the floor. What goes away is the
gap.

<div class="aside">
The catch is that a graph records exact pointers and exact shapes, which
is why serving systems capture a graph per batch size (1, 2, 4, 8, 16,
and so on) and pad up to the nearest one. It also means prefill is never
graphed: its shapes change with every prompt. The technique applies
precisely to the phase that needed it, which is a convenient accident
rather than a design.
</div>

## 11.5 The Pictorial

One token, drawn as a timeline of who is doing the work:

```
  eager, 7.80 ms
  CPU   ##  ##  ##  ##  ##  ##  ##  ##  ##  ##  ...  280 dispatches
  GPU     ##  ##  ##  ##  ##  ##  ##  ##  ##  ##
        ^^  ^^  ^^  ^^   bus idle in every gap

  graphed, ~3.4 ms
  CPU   #                                          one replay call
  GPU    ##############################            same kernels, no gaps
```

The GPU work is identical in both. The only thing we deleted was waiting
for permission.

Notice what we did not have to understand to get here. We never opened a
kernel, never looked at an access pattern, never learned what the
attention implementation does with its tiles. We computed a floor, found
a gap, divided the gap by a count, and the answer named itself.

<div class="aside">
<strong>Build it.</strong> Stage 03 of
<a href="https://github.com/Venugopalan2610/vllm-from-scratch">vllm-from-scratch</a>
makes you measure this gap on your own card before you know what causes
it, and it prints your floor next to your measurement. Stage 12 makes
you capture the graphs and will not pass until replay is measurably
faster than eager and bit-identical to it. The 7.80 against 3.13 in this
chapter came from that stage, on a laptop 4080.
</div>

<div class="challenges">

## Challenges

1. The gap arithmetic assumed ~10 GPU operations per transformer layer.
   Look up or count the actual operations in one layer of a model you
   have handy, redo the per-launch division, and say whether 17 µs still
   looks like dispatch or whether something else is hiding in there.

2. CUDA graphs need static shapes, so a server captures one graph per
   batch size and pads up. Work out the cost of that padding at batch 5
   on a system with graphs at 1, 2, 4, 8, and say when the padding waste
   would exceed the launch overhead it saves.

3. This chapter's model was 0.6B. Redo the floor and the gap for a 7B
   model on the same card, and say whether launch overhead is a larger
   or smaller fraction of the token. Then say what that implies about
   which deployments care most about this fix.

4. Graph replay reuses the same input and output buffers every time.
   Describe the bug that produces, in a server handling concurrent
   requests, if the output buffer is handed to the caller directly. Then
   describe how you would detect it in production, given that it
   produces plausible text rather than a crash.

</div>

<div class="challenges" id="design-note">

## Design Note: The Floor Test Runs in Both Directions

Chapter 1 introduced the floor test as a fraud detector. You compute the
fastest the work could possibly go, you measure faster than that, and
you know something you believed was happening did not happen. A 4 KB
write that returns in 200 nanoseconds did not reach the disk.

This chapter is the same instrument held the other way up, and it is the
more useful direction in practice. Compute the floor, measure well above
it, and you have found work you were not modelling. Not a slow
component: an *unmodelled* one. The distinction matters because it
redirects the search. A slow component means profile it and optimize it.
An unmodelled component means your mental picture of the machine is
missing a participant, and no amount of profiling the parts you already
know about will introduce you to it.

Both directions share one requirement, which is that you compute the
floor before you measure. A floor derived after the fact has a way of
landing suspiciously close to whatever you observed. Write down bytes ÷
bandwidth first, then run the thing, and let the gap be as embarrassing
as it wants to be.

</div>
