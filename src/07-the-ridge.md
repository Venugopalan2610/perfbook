# The Ridge

> Arithmetic intensity, and the 99% idle GPU.

Let's profile a 7-billion-parameter model generating one token. The
card is an A100, 312 teraFLOPS of fp16 compute, roughly $30,000 of
silicon. During that single token, it spends 45 microseconds computing
and 7 milliseconds waiting.

Do the fraction: **the GPU was busy 0.6% of the time.** Ninety-nine
point four percent idle, on the most expensive processor in the
building. This chapter is about why that's not a bug, and why it won't
be fixed by buying a faster one.

## 7.1 Two Candidates and a Missing Number

Candidate one: the GPU is slow because generating a token is
compute-heavy: matrix multiplies, attention, the works. Candidate two:
the GPU is slow because it's waiting on something that has nothing to
do with how many operations it can do per second.

Worth counting the operations before assuming they're the bottleneck.
Generating one token from a 7B model, batch size one, costs roughly:

```
compute:  2 × 7×10⁹ params  ≈  14 GFLOP
memory:   7×10⁹ params × 2 bytes (fp16)  =  14 GB  read
```

Fourteen billion floating-point operations, fourteen billion bytes
read. **One FLOP per byte moved.** That ratio has a name, arithmetic
intensity, and it's the only number this chapter needs to compute
anything else.

## 7.2 The Axioms

| Quantity | A100 (SXM, fp16) |
|---|---|
| Peak compute | ~312 TFLOP/s |
| Peak memory bandwidth | ~2 TB/s |
| **Ridge point** (compute ÷ bandwidth) | **~156 FLOP/byte** |

The ridge point is the arithmetic intensity at which a workload stops
being memory-bound and starts being compute-bound, on this specific
piece of hardware. Below it, the chip finishes the math faster than it
can be fed data, and sits idle waiting on the memory bus. Above it, the
bus finishes feeding data faster than the chip can chew through it, and
the compute units become the limit.

## 7.3 Doing the Division

Our workload's arithmetic intensity is 1 FLOP/byte. The hardware's
ridge is ~156. Let's line them up.

<img class="ruler-chart" src="img/ruler-07-the-ridge.svg" alt="Log-scale ruler: 1 FLOP per byte measured versus a ridge point around 156 FLOP per byte. The workload sits two orders of magnitude to the left of the ridge.">

Convert both halves to time, using the axioms:

```
compute time:  14 GFLOP ÷ 312 TFLOP/s  ≈  45 µs
memory time:   14 GB ÷ 2 TB/s          ≈  7 ms
```

Memory time is **~156× longer than compute time**, not a coincidence;
that ratio *is* the ridge point, restated in seconds instead of
FLOP/byte. The chip finishes its 14 GFLOP of work in 45 µs and then
waits 6.95 ms for the next byte of weight to arrive.

<div class="rule" id="ridge-before-flops">
<span class="rule-id">Rule 9 · Check arithmetic intensity before adding FLOPs</span>
Below the ridge point, more compute buys nothing. The wait is on
bytes, not operations. A faster chip with the same memory bandwidth
generates the same token in the same amount of time.
</div>

## 7.4 What This Rules Out

This rules out the instinct to solve slow generation by upgrading to a
higher-TFLOPS card. If the bottleneck sits 156× to the left of the
ridge, tripling peak compute moves the ridge point further right and
helps nothing. The workload was never anywhere near the compute wall
to begin with. What would move the needle is more memory *bandwidth*,
or (cheaper, and the more common answer) changing the workload's
arithmetic intensity itself.

That's the opening this chapter has been building toward: at batch
size one, we read the entire 14 GB of weights **to compute one token's
worth of math**. At batch size 32, we read the same 14 GB once and
compute 32 tokens' worth of math against it before the next byte has to
arrive. The memory cost didn't grow with batch size; the compute did.

It's worth doing that division in symbols, because the answer comes out
cleaner than it has any right to. Call the parameter count N. Each
weight is two bytes in fp16, and each weight takes part in exactly one
multiply-and-add, which is two operations. At batch size B:

```
bytes moved  =  2 bytes/weight × N              =  2N
operations   =  2 ops/weight × N × B sequences  =  2NB

                 2NB
intensity  =  --------  =  B FLOP/byte
                  2N
```

The twos cancel and the parameter count cancels, and what's left is the
batch size itself. Arithmetic intensity, for this workload, *is* B. Not
approximately, not in the limit. At batch 32 we sit at exactly 32
FLOP/byte, still under the ridge but a lot closer to it, and throughput
scales almost for free on the way there.

That identity is the one to carry out of this chapter. It turns the
ridge point from a property of the silicon into a number we can type
into a config file: a ridge of ~156 FLOP/byte says, in plain language,
"run about 156 sequences at once." Every serving system in the world
exposes that number as a tunable, and now we know what it's tuning
against.

<div class="aside">
The clean cancellation is an accident of fp16, where two bytes per
weight happens to match two operations per weight. Store the weights in
fp8 and the bytes halve while the operations don't, so intensity becomes
2B. Quantization buys arithmetic intensity <em>and</em> a shorter read,
which is two independent wins from one change. Challenge 3 is worth
redoing with that in mind.
</div>

<div class="aside">
This is <a href="./05-group-commit.md#adaptive-batching">group
commit</a>, again. There, a fixed fsync round-trip got amortized across
however many writers queued up behind it. Here, a fixed weight-read
gets amortized across however many tokens' worth of compute we can
queue up behind it before the next byte has to move. Same trick,
different barrier.
</div>

## 7.5 The Pictorial

<img class="chart" src="img/roofline-07-the-ridge.svg" alt="Roofline chart: achieved TFLOP/s versus arithmetic intensity in FLOP/byte, log-log scale. A diagonal memory-bound line rises to a flat compute-bound plateau at the ridge point around 156 FLOP/byte and 312 TFLOP/s. This chapter's workload sits far down the diagonal at 1 FLOP/byte, achieving about 2 TFLOP/s.">

<div class="aside">
Batching walks us rightward along the rising slope, not up onto the
plateau: still memory-bound, just less wastefully so, until we're
batched heavily enough to reach the ridge itself.
</div>

<div class="aside">
<strong>Run it.</strong> <code>experiments-gpu/07_roofline.py</code> measures
your own card's ridge point rather than quoting the A100's, then walks a batch
size toward it. A free Colab T4 is enough. Predict your ridge, and the percent
of peak you will get at batch 1, before you look. See
<a href="./experiments.md">Experiments</a>.
</div>

<div class="challenges">

## Challenges

1. Batch size 32 gets you to ~32 FLOP/byte, still left of the ridge.
   What batch size would this workload need to actually reach ~156
   FLOP/byte, and what has to be true about your traffic for that
   batch to fill up without unacceptable latency?

2. A 13B model has roughly double the weight bytes and double the
   FLOPs per token of the 7B one. Does its ridge crossing point (in
   batch size) change, stay the same, or move, and in which
   direction?

3. Quantizing weights from fp16 to int8 halves the bytes read per token
   without changing the FLOP count much. Recompute arithmetic intensity
   at batch 1 under int8, and say whether this workload is any closer
   to the ridge.

4. Prefill (processing a whole prompt at once) replaces the
   matrix-*vector* multiply this chapter used with a matrix-*matrix*
   multiply, because many tokens' worth of activations move through the
   weights together instead of one at a time. Redo the 7.1 arithmetic
   for a 2048-token prefill pass: does the FLOP count grow with prompt
   length, does the byte count, and where does arithmetic intensity
   land relative to the ridge? (Nothing above answers this; you'll
   need to derive the matrix-matmul FLOP count yourself.)

</div>

<div class="challenges" id="design-note">

## Design Note: The Ridge Doesn't Care How You Feel About the GPU

"99.4% idle" reads like a scandal the first time you compute it, and
the natural response is to go looking for something to blame: bad
kernels, an unoptimized runtime, a driver issue. Usually none of that's
true. The chip is idle because the arithmetic says it should be, and no
amount of engineering effort inside a single forward pass, at batch
size one, changes which side of the ridge you're standing on.

The lesson generalizes past GPUs: any time you're tempted to profile
harder to explain a bottleneck, check arithmetic intensity against the
hardware's ridge point first. If you're two orders of magnitude to the
left of it, the profiler is going to show a chip waiting on memory no
matter how you slice the flame graph, and the fix was never going to
live inside the kernel you were about to optimize.

</div>
