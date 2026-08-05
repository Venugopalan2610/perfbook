# The Slot That Waited

> Eight sequences in flight, and one of them doing all the work.

Chapter 8 left us with a number we could act on. On an 80 GB card the KV
cache lets about 64 sequences run at once, so we size the batch at 64,
fill every slot, and watch the throughput counter with some optimism.

The counter reads like a batch of sixteen.

Every slot is occupied. Memory is full, the scheduler reports 64 live
sequences, nothing is queued. And we are getting a quarter of the
tokens per second that chapter 7's arithmetic promised for a batch that
size. Nothing in the last two chapters explains a factor of four.

## 9.1 Candidates and the Ratio

Candidate one: chapter 8's budget was optimistic. Activations, workspace
and fragmentation ate more than the couple of gigabytes we waved at, so
we are not really running 64 sequences, we are running sixteen and
misreporting it.

Candidate two: all 64 slots really are occupied, and most of them are
occupied by sequences that have already finished.

The spread between those is worth the trouble of separating them,
because they have opposite fixes. The first is a memory-accounting bug
and gets solved by measuring more carefully. The second is not a bug at
all, it's a property of how we decided to schedule, and no amount of
careful measurement will move it.

## 9.2 The Axioms

The thing chapters 7 and 8 never priced is that sequences do not all
finish together. Two of them, side by side in the same batch, can differ
in output length by two orders of magnitude, and neither one is unusual.

| Quantity | Value |
|---|---|
| "What is 2+2?" | ~5 output tokens |
| "Explain the CAP theorem" | ~400 output tokens |
| Ratio between them | **~80×** |
| A batch, once launched, runs until | its **slowest** member finishes |

That last line is the axiom doing all the damage, and it is a choice
rather than a law. We launch a batch, we run it to completion, we launch
the next one. It is the obvious way to write the loop, and every
framework wrote it that way first.

## 9.3 Doing the Division

Take eight requests with a spread that any real service would call
quiet, and count the slot-steps we bought against the slot-steps we
used. A slot-step is one sequence occupying one batch slot for one
forward pass: the atomic unit of the thing we are paying for.

```
output lengths        =  5, 8, 6, 120, 7, 9, 6, 11
batch runs for        =  max(lengths)          =  120 steps
slot-steps purchased  =  8 slots × 120 steps   =  960
slot-steps used       =  5+8+6+120+7+9+6+11    =  172

occupancy  =  172 / 960  =  18%
```

Eighteen percent. We provisioned a batch of eight and got the throughput
of roughly one and a half. Scale the same distribution to 64 slots and
the shortfall is the factor of four we measured, with room to spare.

If you carry one number out of this chapter, carry occupancy rather than
batch size. Batch size is what you configured; occupancy is what you
bought.

<img class="chart" src="img/occupancy-09-the-slot-that-waited.svg" alt="Two stacked timelines of eight batch slots over 120 decode steps. In the static batch, seven slots go dark within the first eleven steps and stay dark while one long sequence runs to 120, leaving 82 percent of the area unused. In the continuous batch, each slot that finishes is immediately refilled by a waiting request, and the area stays almost entirely filled.">

The slots did not fail. They finished, and then they waited, because we
never gave them a way to leave.

<div class="rule" id="iteration-scheduling">
<span class="rule-id">Rule 11 · Release the slot when the sequence ends, not when the batch does</span>
Schedule at the granularity of one forward pass, not one request. A
finished sequence should leave the batch on the step it finishes, and a
waiting one should take its place immediately.
</div>

## 9.4 What This Rules Out

This rules out the memory-accounting candidate, and it rules it out
cleanly: the arithmetic above never mentions bytes. We can hand the
scheduler a perfectly measured 64-sequence budget and still get 18%
occupancy, because the waste is in *time*, not space. Every fix aimed at
memory (a tighter budget, less fragmentation, a bigger card) leaves this
number exactly where it is.

It also rules out the reflex to blame padding. Padding is real: shorter
prompts get padded up to the longest one in the batch, and those padded
positions cost attention work. But padding is bounded by the spread in
*prompt* lengths within a single step, which is a small constant. What
we just measured is bounded by the spread in *output* lengths across the
whole batch's lifetime, which is 80×. They are not the same problem and
they are not the same size.

What survives is the second candidate, and the fix follows from it
directly. If the loss comes from a finished sequence holding a slot, let
it go. After every forward pass, ask which sequences emitted an
end-of-sequence token, evict them, and admit whatever is queued into the
space they left. The batch stops being a fixed group of requests that
start and end together, and becomes a running set with sequences
continuously joining and leaving.

<div class="aside">
This is <a href="./05-group-commit.md#adaptive-batching">group
commit</a> for the third time, and the resemblance is exact enough to be
worth naming. There, we stopped closing a batch on a fixed count and
started closing it when the in-flight fsync returned. Here, we stop
closing a batch on a fixed set of requests and start reconsidering it
every forward pass. Both replace a schedule fixed in advance with one
that reacts to what actually completed. Chapter 7 borrowed group
commit's amortization; this chapter borrows its <em>timing</em>.
</div>

The idea is from Orca (OSDI '22), where it goes by the name
iteration-level scheduling, and it is the single largest throughput win
in modern inference serving. Not because it makes any kernel faster.
Because it stops us paying for slots that finished their work and had
nowhere to go.

## 9.5 The Pictorial

The mechanism fits in a loop, and the loop is short enough to be worth
reading in full:

```
every forward pass:
    admit    while len(running) < max_seqs and queue is not empty:
                 prefill the next request, splice it into the batch
    harvest  record each running sequence's newest token
    evict    drop the ones that hit EOS or their token budget
    forward  one single-token pass over whatever survived
```

Four steps, and the order of the middle two is the whole chapter. Evict
before the forward pass and a finished sequence costs us nothing. Evict
after it, or at the end of the batch, and we are back at 18%.

<div class="aside">
<strong>Build it.</strong> This is where the book hands off to
<a href="https://github.com/Venugopalan2610/vllm-from-scratch">vllm-from-scratch</a>,
a twenty-stage course that constructs the engine these last chapters
derive. Stage 04 makes you build the static batch and measure its
padding waste yourself; stage 05 makes you build this loop and will not
let you pass until it uses under 60% of the forward passes the static
version needed. See <a href="./experiments.md">Experiments</a>.
</div>

<div class="challenges">

## Challenges

1. The loop above evicts finished sequences before the forward pass. Work
   out what happens to a request's output if you evict after it instead,
   and say precisely which token goes missing.

2. Admitting a new request means prefilling its prompt and splicing that
   prompt's KV into a batch whose sequences are all at different
   lengths. Sketch the tensor operations that requires, and estimate how
   much copying happens per admission. Then say what the copy cost is
   proportional to, and why that makes admission expensive at exactly
   the moment you want it to be cheap.

3. With the loop above and a 64-slot budget, what workload would still
   produce low occupancy? Describe the output-length distribution that
   defeats iteration-level scheduling, and say whether you think it
   occurs in practice.

4. A request arrives while the batch is full. Iteration-level scheduling
   says it waits for a slot. Chapter 8 says slots are bounded by KV
   memory, not by a count. Design the admission rule that decides
   whether a newly arrived request can start, given that you do not know
   how long it will run. (Nothing above answers this; the next chapter
   changes the memory model underneath it, which changes the answer.)

</div>

<div class="challenges" id="design-note">

## Design Note: The Cheapest Optimizations Are Refusals

Nothing in this chapter made anything faster. No kernel changed, no
byte moved sooner, no arithmetic got cheaper. We found a place where the
system was doing work it did not have to do, and we stopped.

That is worth noticing, because it is the pattern behind most of the
large wins in this book. Group commit did not make fsync faster, it
stopped calling it once per writer. Write-ahead logging did not make the
disk quicker, it stopped waiting on the data pages before acknowledging.
Here we did not make decoding faster, we stopped renting slots to
sequences that had finished.

The engineering instinct, faced with a throughput number that is four
times too low, is to go looking for something to speed up. It is worth
spending an hour first on the less flattering question: what is this
system doing that it does not need to do at all? The answer tends to be
cheaper to implement and larger in effect than anything you were about
to optimize, and it has the pleasant property that the code gets shorter.

</div>
