# The Cache That Ate the Batch

> 512 KB per token, and why the field went where it went.

Chapter 7 said batch 156 sequences together and we'd reach the A100's
ridge point — the GPU stops idling, compute finally becomes the limit.
Let's try it. On an 80 GB card, running the same 7B model, we run out
of memory at roughly **64**.

Not 156. Sixty-four. Less than half. And it's not close — we didn't
tune a knob and miss by 10%, the process died with an out-of-memory
error two and a half times short of the target chapter 7 set. Something
else is spending the memory chapter 7 assumed was free.

## 8.1 Two Candidates and a Missing Number

Candidate one: this is a scheduling problem — we're padding
variable-length sequences to a common size, and the padding is wasting
capacity. Candidate two: it's not padding at all. It's a second,
growing memory cost that chapter 7 never priced in.

Worth checking the ratio before hunting for padding bugs. Chapter 7
accounted for one thing living on the GPU: 14 GB of weights. It said
nothing about what accumulates *during* generation — every token
already produced leaves behind a cached Key and Value tensor, kept
around so the next token doesn't have to recompute attention over the
whole prefix from scratch. That cache has a size, and it was completely
absent from last chapter's arithmetic.

## 8.2 The Axioms

For a 7B-class model (32 layers, 4096-dim hidden state, fp16):

| Quantity | Value |
|---|---|
| KV cache per token | 2 × 32 layers × 4096 dim × 2 bytes = **512 KB** |
| KV cache per 2048-token sequence | 512 KB × 2048 = **1 GB** |
| A100 total memory | 80 GB |
| Model weights (fp16, 7B) | 14 GB |

The factor of 2 is Key *and* Value, one tensor each, per layer, per
token. It's not an implementation detail you can shrink by being clever
with your batching loop — it's a per-token cost that accrues for as
long as that token stays in context, for every sequence running
concurrently.

## 8.3 Doing the Division

```
memory budget for KV cache = 80 GB − 14 GB (weights) = 66 GB
sequences that fit          = 66 GB ÷ 1 GB/sequence  ≈ 66
```

Sixty-six, before accounting for activation memory, the CUDA context,
and other fixed overhead that eats a couple more gigabytes off the
top — which is exactly how we land at the observed ~64. **The KV cache
arithmetic alone explains the shortfall.** Padding waste, if it exists
at all, is a rounding error next to it.

<div class="rule" id="kv-budget-not-guess">
<span class="rule-id">Rule 10 · Size your batch from the KV budget, not a guess</span>
Before assuming a batch ceiling is a scheduling inefficiency, compute
bytes-per-token × context length × desired concurrency, and check it
against free memory. The wall is usually arithmetic, not a bug.
</div>

## 8.4 What This Rules Out

This rules out the idea that chapter 7's ridge point is reachable just
by "batching harder." The ridge told us the compute-optimal batch size;
this chapter shows the memory-optimal batch size is a *harder* ceiling
that sits below it. We hit the KV-cache wall at 64 before ever getting
near the 156 the ridge wanted, and no amount of scheduling cleverness
moves that number — it's set by architecture and context length, full
stop.

It also reframes what "add more GPU memory" buys us: linear headroom,
at GPU prices, for a quadratic-feeling problem — every additional
sequence costs another 1 GB *for the whole time it's in flight*, not
once. The field's actual answer wasn't bigger GPUs. It was making the
512 KB/token number itself smaller:

- **Multi-/Grouped-Query Attention (MQA/GQA)** — share Key/Value
  projections across multiple attention heads instead of computing a
  distinct KV pair per head. Directly divides the 512 KB/token figure
  by the sharing factor.
- **KV cache quantization** — store K/V in int8 or lower instead of
  fp16. Same lever as quantizing weights (chapter 7's challenge 3),
  aimed at the cache instead.
- **PagedAttention** — stop pre-allocating each sequence's KV cache for
  its worst-case length. Allocate in fixed-size pages on demand, like
  virtual memory, so unused headroom in a short sequence isn't locked
  away from a longer one running next to it.

Every one of these attacks the 512 KB constant or the waste around it.
None of them touch the ridge point from chapter 7 — they're a different
wall, and they need a different tool.

## 8.5 The Pictorial

<img class="chart" src="img/kv-budget-08-kv-cache.svg" alt="Bar chart comparing an 80 GB A100's memory budget. Top bar: 14 GB weights plus 64 GB KV cache fits under the 80 GB card line. Bottom bar: what the ridge point wants, 14 GB weights plus 156 GB KV cache for 156 sequences, extends well past the 80 GB card line and doesn't fit.">

(Activation memory and other fixed overhead — a couple more gigabytes — aren't shown; they're what pushes the real ceiling from 66 down to the observed ~64.)

<div class="aside">
This is why GQA/MQA and KV quantization get discussed in the same
breath as "faster inference," even though neither one adds a single
FLOP of compute. They're not making the GPU faster. They're moving the
wall in this diagram to the right.
</div>

<div class="challenges">

## Challenges

1. Grouped-Query Attention with a group size of 8 divides the KV cache
   per token by roughly 8. Recompute the batch ceiling on the same
   80 GB card, and check it against the ridge point's target of ~156.

2. Sequences in a real batch don't all sit at 2048 tokens — some are
   200 tokens long, some are 4000. Design a memory-accounting scheme
   for the 66 GB budget that handles this without falling back to "pad
   everyone to the max length." (This isn't fully answerable from this
   chapter alone — you'll need to think through what PagedAttention is
   actually doing under the hood.)

3. int8 KV quantization halves the 512 KB/token figure. Does it change
   the *ridge point* from chapter 7, or only the batch ceiling from
   this chapter? Be precise about which number moves and which
   doesn't.

4. A 70B model has roughly 10× the weights of the 7B one, but its KV
   cache per token doesn't scale by the same factor unless hidden
   dimension and layer count both scale linearly with parameters. Look
   up (or estimate from architecture) whether a real 70B-class model's
   KV-cache-per-token is closer to 5× or 10× the 7B figure, and redo
   the 80 GB budget.

</div>

<div class="challenges" id="design-note">

## Design Note: Two Walls Look Identical From the Outside

"Generation is slow" and "batch size is capped" both show up as the
same complaint — throughput isn't what it should be — and chapters 7
and 8 are proof that they can have completely unrelated causes. One is
a compute-vs-bandwidth ratio on the chip. The other is a
bytes-vs-capacity ratio in memory. Neither diagnosis transfers to the
other's fix.

Buying a GPU with more TFLOPS solves the wrong wall if you're capped by
KV memory. Buying a GPU with more memory solves the wrong wall if
you're capped by the ridge. The only way to know which one you're
actually up against is to do both pieces of arithmetic — FLOP/byte
against the ridge, bytes/token against the budget — before spending
money on either.

That's more or less the whole book in one sentence: two numbers that
don't fit are two different chapters, and they very rarely share a fix.

</div>
