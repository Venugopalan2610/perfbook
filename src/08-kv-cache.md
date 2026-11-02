# The Cache That Ate the Batch

> 512 KB per token, and why the field went where it went.

<img class="chapter-illustration" src="img/illus-08-kv-cache.png" alt="An enormously fat and rather smug cat filling an entire small room, bookshelves pressed against the walls behind it.">

Chapter 4 ended with an instruction that felt like a victory: batch
156 sequences together and the reference GPU reaches its ridge point.
The chip stops idling, compute finally becomes the limit, everybody
goes home happy.

So put a 7B model on the reference GPU's 80 GB and ask it to run 156
sequences at once, each with room for a 2048-token conversation. Before
you read on, make a prediction. Does it fit? If not, how many do you
think it holds? Write the number down.

It does not fit. It holds about **66**.

Not 156. Sixty-six. Less than half, and it is not close. This is not a
knob tuned ten percent wrong. Try it on a real card and the process dies
with an out-of-memory error, well short of the target.

<p class="quip">Sixty-six is not a tuning failure. It is an arithmetic result that nobody had got around to computing.</p>

Something is spending memory that chapter 4 assumed was free.

## 5.1 Two Candidates and a Missing Number

Something is eating the difference, and there are two obvious suspects.
One of them is a scheduling problem we could fix by being cleverer. The
other is a cost we simply never counted.

The first: this is a scheduling problem. We are padding
variable-length sequences to a common size, and the padding is eating
the capacity.

The second: it is not padding at all. There is a second, growing
memory cost that chapter 4 never priced.

Before we go hunting for padding bugs, it is worth checking the ratio.
And the fastest way in is to ask what chapter 4 actually accounted for.

It accounted for exactly one thing living on that GPU: 14 GB of
weights. It said nothing whatsoever about what accumulates *during*
generation.

Now think about what has to accumulate. Every token already produced
leaves behind a cached Key and Value tensor, kept around so the next
token does not have to recompute attention over the entire prefix from
scratch. That cache has a size. And it was completely absent from last
chapter's arithmetic, not because anybody was careless, but because at
batch size one, generating one token, there was nothing yet to
accumulate.

## 5.2 The Axioms

For a 7B-class model (32 layers, 4096-dim hidden state, fp16):

| Quantity | Value |
|---|---|
| KV cache per token | 2 × 32 layers × 4096 dim × 2 bytes = **512 KB** |
| KV cache per 2048-token sequence | 512 KB × 2048 = **1 GB** |
| Reference GPU memory | 80 GB |
| Model weights (fp16, 7B) | 14 GB |

The factor of 2 is Key *and* Value: one tensor each, per layer, per
token.

That is not an implementation detail you can shrink by being clever
with your batching loop. I want to be firm about it, because it is the
first thing people reach for. It is a per-token cost that accrues for
as long as that token stays in context, for every sequence running
concurrently, and no amount of scheduling makes it smaller.

<p class="quip">A 2048-token conversation costs a gigabyte. The complete works of Shakespeare are about five megabytes.</p>

Half a megabyte. Per word. Per conversation.

If you are used to thinking of a model as its weights, that is the
number that will catch you out, and it caught me out too. The weights
are the part that has a name and a download size. The cache is the part
that decides how many people you can serve.

## 5.3 Doing the Division

With a number for what a token costs, the batch ceiling is one
subtraction and one division. Take the card, remove the weights, and see
how many one-gigabyte sequences fit in what is left:

```
memory budget for KV cache = 80 GB − 14 GB (weights) = 66 GB
sequences that fit          = 66 GB ÷ 1 GB/sequence  ≈ 66
```

Sixty-six, and a few fewer on a real card, once activation memory and
the runtime take their share off the top. `experiments-gpu/08_kv_cache.py`
allocates a real KV cache on your GPU and asks the driver what it cost,
so you can check the 512 KB with your own eyes.

<p class="quip">Somewhere there is a very tidy padding fix, thoroughly reviewed and merged with compliments, that bought absolutely nobody anything.</p>

**The KV cache arithmetic alone explains why 156 cannot fit.** All of it.
There is nothing left over for padding to be responsible for, and if we
had gone hunting for padding bugs we would have found some, fixed them
carefully, and moved the number by almost nothing.

<div class="rule" id="kv-budget-not-guess">
<span class="rule-id">Rule 7 · Every resource has a ceiling; the lowest one binds</span>
Before you call a limit a scheduling problem, compute the budget for
every resource the work needs, and check which one runs out first. The
wall is usually arithmetic, not a bug. For LLM serving: bytes per token
× context length × concurrency, against free memory.
</div>

## 5.4 What This Rules Out

This rules out the idea that chapter 4's ridge is reachable just by
batching harder.

The ridge told us the compute-optimal batch size. This chapter shows
the memory-optimal batch size is a *harder* ceiling sitting underneath
it. We hit the KV wall at 66 before we got anywhere near the 156 the
ridge wanted, and no amount of scheduling cleverness moves that. It is
set by architecture and context length, and that is the end of it.

It also reframes what "add more GPU memory" actually buys. Linear
headroom, at GPU prices, for a problem that feels quadratic from the
inside. Every additional sequence costs another gigabyte *for the whole
time it is in flight*, not once.

<p class="quip">A gigabyte per conversation, for as long as the conversation lasts. Thinking out loud turns out to be an expensive habit.</p>

So the answer was never going to be bigger GPUs. And here is the tool,
which has nothing to do with GPUs: when a fixed budget is full, there
are only three moves. Make each item smaller. Let items share. Stop
holding space that nobody is using. Every capacity problem you will
ever meet is attacked with some mix of those three, and in this corner
of the field, in the early 2020s, each one got an acronym.

- **Multi- and Grouped-Query Attention (MQA/GQA)**: share Key and Value
  projections across several attention heads instead of computing a
  distinct KV pair for each. Divides the 512 KB directly by the sharing
  factor.
- **KV cache quantization**: store K and V in int8 or lower instead of
  fp16. The same lever as quantizing weights in chapter 4's challenge
  3, pointed at the cache instead.
- **PagedAttention**: stop pre-allocating each sequence's cache for its
  worst-case length. Hand out fixed-size pages on demand, like virtual
  memory, so unused headroom in a short sequence is not locked away
  from a longer one running beside it.

<p class="quip">Half the acronyms in this corner of the field are attacks on one constant. Once you know which constant, the reading list gets much shorter.</p>

Every one of those attacks the 512 KB constant, or the waste around it.
None of them touch the ridge point from chapter 4. Different wall,
different tool, and that distinction is the whole reason these are two
chapters instead of one.

## 5.5 The Pictorial

Two bars, one card. The top one is what we can actually run. The bottom
one is what chapter 4 told us to run, drawn to the same scale so you can
see exactly how far past the edge of the card it goes:

<img class="chart" src="img/kv-budget-08-kv-cache.svg" alt="Bar chart comparing an 80 GB card's memory budget. Top bar: 14 GB weights plus 66 GB KV cache fits under the 80 GB card line. Bottom bar: what the ridge point wants, 14 GB weights plus 156 GB KV cache for 156 sequences, extends well past the 80 GB card line and doesn't fit.">

(Activation memory and other fixed overhead, a few gigabytes, are not
shown. On a real card they take the ceiling a little below 66.)

<div class="aside">
This is why GQA and KV quantization get discussed in the same breath as
"faster inference," even though neither one adds a single FLOP of
compute. They are not making the GPU faster. They are moving the wall
in that diagram to the right, which from the outside looks identical.
</div>

<div class="aside">
<strong>Run it.</strong> <code>experiments-gpu/08_kv_cache.py</code> allocates a
real KV cache and asks CUDA what it cost, instead of trusting the 512 KB
multiplication, and measures the exact factor GQA saves. A free Colab T4 is
enough. See <a href="./experiments.md">Experiments</a>.
</div>

<div class="challenges">

## Challenges

1. Grouped-Query Attention with a group size of 8 divides the KV cache
   per token by roughly 8. Recompute the batch ceiling on the same
   80 GB card, and check it against the ridge point's target of ~156.

2. Sequences in a real batch don't all sit at 2048 tokens: some are
   200 tokens long, some are 4000. Design a memory-accounting scheme
   for the 66 GB budget that handles this without falling back to "pad
   everyone to the max length." (This isn't fully answerable from this
   chapter alone; you'll need to think through what PagedAttention is
   actually doing under the hood.)

3. int8 KV quantization halves the 512 KB/token figure. Does it change
   the *ridge point* from chapter 4, or only the batch ceiling from
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

"Generation is slow" and "batch size is capped" arrive as the same
complaint. Throughput is not what it should be. Somebody is unhappy.

Chapters 4 and 5 are proof that the identical complaint can have
completely unrelated causes. One is a compute-versus-bandwidth ratio on
the chip. The other is a bytes-versus-capacity ratio in memory. Neither
diagnosis transfers to the other's fix, and neither one is visible from
the complaint.

Buy a GPU with more TFLOPS and you have solved the wrong wall if you
are capped by KV memory. Buy one with more memory and you have solved
the wrong wall if you are capped by the ridge. Both purchases feel
responsible. Both come with a graph. The only way to know which one you
are actually against is to do both pieces of arithmetic, FLOP per byte
against the ridge and bytes per token against the budget, before
anybody spends money on either.

That is more or less the whole book in a sentence: two numbers that do
not fit are two different chapters, and they very rarely share a fix.

</div>
