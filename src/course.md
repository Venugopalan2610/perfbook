# The Course

> Thirty-five stages, and not one of them passes because the code ran.

Parts II, III and V of the book derive an inference engine, and
[vllm-from-scratch](https://github.com/Venugopalan2610/vllm-from-scratch)
builds one. This page is that repository's map: what the thirty-five
stages are, in what order, and which number each one will not let you
past until it moves.

The split is worth being precise about, because it is the reason these
are two things instead of one longer book. A chapter's job is to find
the single quantity that is genuinely scarce and show you the arithmetic
that makes it scarce. It has done its job when you can predict the
number. The course does not care whether you can predict continuous
batching's win. It cares whether *your* continuous batching used under
60% of the forward passes *your* static batching needed, on your card,
this afternoon.

There are 465 checks across the thirty-five stages, thirty-three of
them core and two optional, and most of the checks assert a measurement
rather than a behaviour. `./vc submit` refuses to advance while anything
is red, so there is no way to skip a stage by being impatient with it.
(231 checks if you take the JAX route, which is two sections down. It
leaves out the CUDA stages and the capstone, which need a CUDA card.)

That refusal is the whole product. Anybody can read thirty-five descriptions
of PagedAttention. Rather fewer people have had a test inform them that
their page table is perfectly correct and slower than the contiguous
cache it replaced, and print by how much, which is the actual experience of writing
one, and which is stage 7.

## Start without installing anything

The honest problem with handing somebody a repository is that they have
to set it up first, and the setup here is a virtual environment, a
couple of gigabytes of PyTorch, and a model download, on a machine that
might not have a GPU in it at all. That is a great deal of friction to
pay before you know whether you want the thing.

So there is a notebook. It clones the course onto a free Colab T4, runs
the setup, and leaves you at stage 1's guide, and it costs you a browser
tab.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Venugopalan2610/vllm-from-scratch/blob/master/colab.ipynb)

It also puts the GPU stages within reach of a machine that cannot run
them. Stage 8 is a CUDA kernel, stage 12 captures CUDA graphs, and the
capstone from stage 21 on wants a CUDA card throughout: on a laptop with
integrated graphics those are stages you can read and not do. On a T4 they run.

One caveat, and it is a real one. A Colab runtime is temporary. Your
progress lives in `.progress.json` inside that container, and when the
session resets it goes, along with everything you wrote. That is fine
for working through the first arc and finding out whether you care. It
is not where you would do all thirty-five. The notebook's last cell pushes
your work to your own fork, and past about stage 5 you should take it up
on that.

## Or run it on your own machine

```bash
gh repo fork Venugopalan2610/vllm-from-scratch --clone
cd vllm-from-scratch
./setup.sh        # python 3.12 venv, torch, and the model. once, ~5 min.
./setup.sh --jax  # and JAX too, if you want the second track. +400 MB.
```

Fork rather than clone, because `./vc submit` commits your work and you
will want somewhere to push it.

No GPU is not fatal. Setup still works and about half the stages still
run, because the allocator, the scheduler, the prefix cache, the
metrics, the speculative sampler and the guided decoder are pure logic
and were deliberately written to be testable without a card.

## The loop

```bash
./vc              # where am I?
./vc guide        # what to build, and why it comes here and not earlier
                  # ... go and edit the file it names ...
./vc test         # run the checks. as often as you like.
./vc submit       # all green? banked, committed, next stage opens
```

`./vc submit` commits only `app/`, which is your work, and prints the
next stage's guide. There is also `./vc math` if you want the arithmetic
for your own card rather than the book's reference GPU, and `./vc peek` if you
are genuinely stuck and would rather read the answer than abandon the
ladder. Reading the answer is a worse outcome than working it out and a
much better one than quitting.

## Two ladders, one physics

Here is a question I did not expect to have to answer, and the answer
turned out to be worth more than the question. Does any of this depend
on PyTorch?

It had better not. The whole book is an argument from one physical fact,
that fetching a weight from HBM costs far more than the arithmetic you
then do with it, and silicon does not care which Python library you type
at it. But claiming that and demonstrating it are different activities.
So the course runs on two backends now.

```bash
./vc backend jax      # switch tracks. progress is banked per track.
./vc test 8 --jax     # or just one command on the other, without switching
```

Eleven stages get a JAX twin, so you edit `app/j08_paged_pallas.py`
where the other track edits `app/s08_paged_cuda.py`. Nine more are not
twins at all. They are the same file. The other fifteen are the CUDA
stages and the capstone, which the JAX track does not ask for.

Read that again, because it is the finding, and I did not go looking for
it. The block allocator, the prefix cache, the scheduler, chunked
prefill, the incremental detokenizer, the async server, the metrics, the
speculative sampler and the guided decoder were never ported, because
there is nothing in them to port. Not one of them contains a tensor
operation worth the name. Nearly half of an inference engine is
refcounts, free lists, three queues and a hash table, and it would look
much the same if you wrote it in Go.

Allow yourself a moment of disappointment about that, and then notice
that it is good news twice over. The hard part is not the framework. And
the part you were afraid of, the kernel, is a minority of the work.

### Where they do diverge, they diverge from one cause

XLA compiles a program for exact shapes. Torch dispatches a kernel per
operation, at runtime, from whatever shape the tensor happens to have.
So a KV cache that grows by one token per step, which is the obvious
design and the one the torch track uses, is a brand new program every
step. Seconds of compiler. Per token.

You fix it by refusing to change the shape: preallocate the cache to its
maximum and write into it. That is one sentence, and it moves four
stages sideways.

Stage 2 hands you back the bookkeeping torch was quietly doing on your
behalf, because now `cache_len` is yours to carry. Stage 4 right-pads
where the other track left-pads, since the padding belongs where the
generated tokens are about to land, and then you have to tell the model
which row's logits to read. Get that wrong and the short prompts in your
batch produce fluent continuations of the padding, which is a much worse
failure than an error, because it looks like text.

Stage 5 is the one I would send somebody to. When a sequence finishes
you cannot shrink the batch, because the batch dimension *is* the
compilation. So the batch becomes a fixed table of slots. Finishing
frees one, admitting fills one, and nothing is copied or re-indexed at
all. That is a page table with one page per sequence, and you have
arrived at it a whole arc before the course meant to introduce the idea.

There is a sting in it. A step costs the same whether one slot is busy
or eight, so continuous batching cannot possibly show up as a faster
step. It shows up as useful tokens per forward pass, and occupancy
becomes the entire game. The idea from
[The Slot That Waited](./09-the-slot-that-waited.md) survives intact.
The number you measure it with does not.

### The stage that convinced me

Stage 12, on the torch track, captures CUDA graphs. You know why from
[Below the Floor](./11-below-the-floor.md): a decode step at batch 1 is
about a millisecond of GPU work and about a millisecond of Python
issuing kernel launches, and the graph deletes the second millisecond.

None of that is true in JAX. XLA already fused the step into one
program. There is one launch. The Python is gone.

And stage 12 on the JAX track does exactly the same thing anyway. Pick a
handful of batch sizes, compile ahead of time for each, pad up to the
nearest one. The same fix, to the letter, for a completely unrelated
disease: not launch overhead but compilation, which is what you pay
every time a batch size you have not seen before walks in the door.

That is the strongest evidence in the repository that bucketing is not a
CUDA trick. It is what you do whenever preparing to run the work has
started to cost more than the work.

### Two places JAX is simply better, and one where it is not

Stage 8 is Pallas where the other track writes CUDA, and the online
softmax is, line for line, the same idea. What changes is the indirection. Pallas gives you a
BlockSpec that declares which tile of an array each program sees, which
is a lovely abstraction right until the tile you need depends on a page
table you have not read yet. So the block table lookup moves inside the
kernel, with an index you compute there. The one thing the abstraction
cannot do for you is precisely the thing PagedAttention is.

Stage 20 stops being a simulation, and I am slightly embarrassed by how
much better it gets. The torch track shards weights in a Python loop and
then spawns two gloo processes to prove a collective works. JAX simply
hands you devices. `shard_map` over a mesh, column-parallel and then
row-parallel, and the psum is a real all-reduce, so "exactly one
collective per block" stops being a claim in prose and becomes something
the check counts in the compiled HLO.

Now the honest one. Decode on the JAX track gets slower as the cache
gets bigger, and it should not. The preallocated buffer is rewritten
functionally, per layer, inside the scan, so you pay for the ceiling you
chose rather than the context you actually hold. Roughly 1.3x going from
a 128-slot cache to a 1024-slot one, where the torch track is nearly
flat. Buffer donation does not rescue it, because the copy is inside the
scan where the donation cannot reach.

Stage 3 says so, in the test, with the number, rather than quietly
choosing a friendlier measurement. What actually fixes it is making the
buffer granular so that a step only touches the blocks it needs, which
is PagedAttention, which is the next arc. The JAX track gives you a
reason to want stages 6 through 9 before you have finished stage 3. I
would not have been clever enough to design that on purpose.

## Which chapter derives which stage

Six of the thirteen chapters have a stage that builds what they derived.
Those are the ones where reading and building are the same activity done
twice, and doing both in that order is the intended path.

| Chapter | Stages |
|---|---|
| [The Ridge](./07-the-ridge.md) | 01–03, the naive loop and the roofline |
| [The Cache That Ate the Batch](./08-kv-cache.md) | 02, KV bytes per token |
| [The Slot That Waited](./09-the-slot-that-waited.md) | 04–05, static then continuous batching |
| [A Page Table for Tokens](./10-a-page-table-for-tokens.md) | 06–09, blocks, paged attention and its CUDA kernels, prefix cache |
| [Below the Floor](./11-below-the-floor.md) | 03 and 12, the gap and CUDA graphs |
| [Spending the Idle](./12-spending-the-idle.md) | 17, the n-gram proposer and rejection sampler |

The rest have no chapter deriving them, and I would rather say so than
pretend the coverage is complete. Stages 10, 11, 13 through 16 and 18
through 20 build the scheduler, chunked prefill, the sampler, the
detokenizer, the server, the metrics, quantization, guided decoding and
tensor parallelism. Stages 21 through 28 are the capstone, which puts
every part into one engine and races it against the roof of your card,
and 29 through 31 go past it. They are good stages. They are simply
ahead of the prose.

## The ladder

Nine arcs. The order is not the order a textbook would choose: it is
roughly the order the ideas were actually discovered, which means every
stage exists because the previous one broke in a specific way, and the
guide for each one opens by telling you what that way was.

The pips are how hard the code is, not how hard the idea is. Stage 3 is
two stars and is the most important thing in the course.

<!-- BEGIN LADDER -->

## A1 · The Naive Loop

Build the slow thing first, and measure it, so every later win is a
number.

### 01 · Greedy decode, no cache <span class="stage-diff">[*....]</span>

A transformer forward pass is a pure function of the whole prefix. The
naive loop makes N tokens at a cost of O(N^2) attention work. It
computes the K and V of every earlier token at every step.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s01_naive.py</code> generate() that emits one token at a time from a HF model.</span>
<span class="k">Gate</span><span>tokens/sec at 128 output tokens. This is your rock bottom.</span>
</div>

### 02 · The KV cache <span class="stage-diff">[**...]</span>

The K and V of a token never change after you compute them. Cache them,
and each decode step becomes a forward pass over one token. The total
cost is O(N). Memory now becomes your enemy, not compute.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s02_cache.py</code> A contiguous KV cache for each sequence. Decode attends over the cache and the new token.</span>
<span class="k">Gate</span><span>tokens/sec (expect a large multiple of stage 1) and bytes of KV per token.</span>
</div>

### 03 · Prefill vs decode: two different machines <span class="stage-diff">[**...]</span>

Prefill waits on compute. It runs big GEMMs at a high arithmetic
intensity. Decode waits on memory bandwidth. At batch size 1 the GPU
reads every weight from HBM to make one token. The two want opposite
optimizations. This is THE fact behind every later design decision.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s03_roofline.py</code> A microbenchmark separating prefill ms/token from decode ms/token.</span>
<span class="k">Gate</span><span>Achieved GB/s during decode vs your GPU's peak. You get near the peak.</span>
</div>

## A2 · Batching

Decode is bandwidth-bound, so extra sequences are nearly free. Exploit
that.

### 04 · Static batching with padding <span class="stage-diff">[**...]</span>

A batch spreads the weight read across the sequences. You get 8x the
tokens for almost 1x the time. But a static batch runs until its SLOWEST
member finishes. A short sequence then sits padded and idle, and it
wastes the slot.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s04_static_batch.py</code> Left-padded batch of N prompts, shared decode loop, attention mask. Then four_lines(): predict the floor, measure, divide, double.</span>
<span class="k">Gate</span><span>Throughput vs batch size, AND the % of decoded token-slots wasted on padding.</span>
</div>

### 05 · Continuous batching (iteration-level scheduling) <span class="stage-diff">[***..]</span>

Schedule for each ITERATION, and not for each request. When a sequence
emits EOS, remove it in that same step and admit a waiting sequence into
its slot. The idea comes from Orca (OSDI '22). On real traffic it gives
2x to 4x over a static batch. It is the largest throughput win in this
repo.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s05_continuous.py</code> A step() loop over a mutable running set. A request joins or leaves in mid-flight. Then four_lines(): predict the floor, measure, divide, double.</span>
<span class="k">Gate</span><span>Throughput on a Poisson arrival trace + p50/p99 latency vs stage 4.</span>
</div>

## A3 · PagedAttention

The idea behind the name vLLM. Virtual memory, applied to the KV cache.

### 06 · Blocks, block tables, free list <span class="stage-diff">[***..]</span>

A contiguous cache for each sequence forces you to allocate for max_len.
So a real server wastes 60% to 80% of its KV memory on internal
fragmentation and reservation. Cut the cache into fixed 16-token blocks.
Hand them out on demand. Keep one block table, which is a page table,
for each sequence. The waste falls to less than one block for each
sequence.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s06_blocks.py</code> BlockAllocator + BlockTable. No attention changes yet. Then four_lines(): predict the floor, measure, divide, double.</span>
<span class="k">Gate</span><span>Sequences resident in 12GB, paged vs contiguous. Expect a big jump.</span>
</div>

### 07 · Attention that reads through the page table <span class="stage-diff">[****.]</span>

The kernel must gather K and V from scattered blocks. It can no longer
stride through a contiguous tensor. Do it in PyTorch first, with
index_select and SDPA, to make it CORRECT. Then keep that version as the
reference oracle forever.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s07_paged_attn.py</code> write_kv(), paged_attention() and reference_attention() in plain PyTorch. The paged output must match the dense reference. Then four_lines(): predict the floor, measure, divide, double.</span>
<span class="k">Gate</span><span>Correctness vs the contiguous implementation, then the slowdown you just ate.</span>
</div>

### 08 · The same thing, in CUDA <span class="stage-diff">[*****]</span>

Give one block to each (sequence, query head) pair. Walk the block
table. Stream the K and V tiles, and fold them into a running softmax,
so that the score row never reaches HBM. The decision that matters is
not the arithmetic. It is what one block owns, because that fixes
everything else. A block that owns one output vector never needs to talk
to another block.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s08_paged_cuda.py</code> A CUDA paged decode kernel, plus the KV scatter kernel, that beats stage 07. Then four_lines(): predict the floor, measure, divide, double.</span>
<span class="k">Gate</span><span>Correctness against stage 07, then us/token, then the fraction of this card's bandwidth that you reached.</span>
</div>

### 09 · How to feed the memory system <span class="stage-diff">[****.]</span>

Your stage 08 kernel gave one thread to one position, and each thread
walked head_dim alone. So the 32 threads of a warp asked for 32
scattered rows at one time. Turn the mapping sideways. The threads then
cooperate ALONG head_dim, at 16 bytes each, and the requests of the warp
merge into whole 128-byte transactions. The arithmetic and the answers
do not change, and the bandwidth approximately doubles. This is the most
valuable habit in CUDA.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s08b_cuda_memory.py</code> The same kernel with coalesced, 128-bit vectorized loads and the accumulator in registers. Then four_lines(): predict the floor, measure, divide, double.</span>
<span class="k">Gate</span><span>At least 1.5x over stage 08, and a real fraction of this card's measured streaming bandwidth.</span>
</div>

### 10 · Warps, occupancy and split-K <span class="stage-diff">[*****]</span>

At batch 1 the grid is (1, num_heads), and most of the SMs have nothing
to do. So a kernel that is perfect on bandwidth still uses a few percent
of the card. There are two fixes. Use __shfl_xor_sync to reduce inside a
warp, with no shared memory and no barrier. Then use split-K, which cuts
the CONTEXT into chunks to make more blocks and merges the partial
softmax states exactly. Batch 1 is every interactive request.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s08c_cuda_warps.py</code> Warp-shuffle reductions, then a split-K kernel and an exact merge pass. Then four_lines(): predict the floor, measure, divide, double.</span>
<span class="k">Gate</span><span>At least 1.5x over stage 08b at 1, 2 and 4 sequences, and no more than a few percent given back at 64.</span>
</div>

### 11 · Copy-on-write and automatic prefix caching <span class="stage-diff">[****.]</span>

A block table makes sharing simple. Two sequences can point at the same
physical block. Count the references, and copy a block when one sequence
diverges. Then hash the contents of a block and share it across
REQUESTS. One prefill of a shared system prompt then serves everybody.
This is why APC looks like cheating.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s09_prefix.py</code> Refcounted blocks, CoW on write, content-hash prefix cache with LRU eviction. Then four_lines(): predict the floor, measure, divide, double.</span>
<span class="k">Gate</span><span>Blocks shared and prefill work saved for a shared system prompt. Stage 22 measures it on a real model.</span>
</div>

## A4 · The Scheduler

You have finite KV memory and infinite requests. Decide who runs.

### 12 · Waiting / running / swapped, and preemption <span class="stage-diff">[****.]</span>

Sequences grow one block at a time, so the batch you admitted can run
out of memory mid-decode. You need preemption: either SWAP blocks to CPU
or DROP them and recompute later. On a PCIe card a swap usually costs
less in total (part4_adm_2 measures it). Engines still make recompute
the default, because it is SCHEDULABLE: it can be cut into chunks, it
can start from a cached prefix, and it needs no pinned host memory.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s10_scheduler.py</code> Three queues, a KV budget check per step, preempt-by-recompute. Then four_lines(): predict the floor, measure, divide, double.</span>
<span class="k">Gate</span><span>Behavior under overload: does throughput degrade gracefully or collapse?</span>
</div>

### 13 · Chunked prefill and mixed batches <span class="stage-diff">[****.]</span>

One 8000-token prefill stalls every decoding sequence for a whole step,
wrecking inter-token latency for everyone. Split prefill into chunks and
co-schedule chunks with decodes in the SAME batch. From Sarathi-Serve.
This is the throughput/latency dial in every modern serving stack.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s11_chunked.py</code> A unified batch of [prefill chunks + decode tokens] with correct positions. Then four_lines(): predict the floor, measure, divide, double.</span>
<span class="k">Gate</span><span>p99 inter-token latency with a long prompt in flight. Before vs after.</span>
</div>

## A5 · How To Make It Fast

The kernels are fast. Now remove the overhead around them, and make the
output correct.

### 14 · CUDA graphs for the decode step <span class="stage-diff">[****.]</span>

At batch 1 a decode step is approximately 1 ms of GPU work. Python and
the kernel launches can cost another 1 ms. Capture the whole step as a
graph, and replay it. A graph needs static shapes, so capture at
bucketed batch sizes and pad up to the nearest bucket.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s12_cudagraph.py</code> Graph capture per bucket, replay path, eager fallback. Then four_lines(): predict the floor, measure, divide, double.</span>
<span class="k">Gate</span><span>us/step at batch 1, 2, 4, 8. Watch the Python tax vanish.</span>
</div>

### 15 · A real batched sampler <span class="stage-diff">[***..]</span>

Each request has its own temperature, top-k, top-p, penalties and seed.
ONE vectorized pass over the batch must apply all of them. When the
kernels become fast, a Python loop over the requests quietly becomes
your bottleneck.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s13_sampler.py</code> Vectorized temp/top-k/top-p/repetition penalty, per-request seeded RNG. Then four_lines(): predict the floor, measure, divide, double.</span>
<span class="k">Gate</span><span>Sampler ms/step at batch 64, plus a distributional test that top-p is exact.</span>
</div>

### 16 · Incremental detokenization and stop conditions <span class="stage-diff">[***..]</span>

You cannot decode tokens one by one. BPE pieces, multi-byte UTF-8 and
the leading-space rules make a naive stream emit mojibake and double
spaces. A stop STRING can also cross a token boundary, so you must
buffer. This stage is dull, and it causes most of the bugs that users
see in a real server.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s14_detokenizer.py</code> Streaming detokenizer with a lookback window + straddling stop-string check.</span>
<span class="k">Gate</span><span>Fuzz test: streamed output must equal batch-decoded output, always.</span>
</div>

## A6 · The Server

Turn the engine into something you can curl.

### 17 · Async engine + OpenAI-compatible API <span class="stage-diff">[***..]</span>

The engine loop must never block on HTTP, and HTTP must never block on
the GPU. One process runs step() forever. Requests reach it as futures
and queues. Real vLLM V1 goes further and uses a separate EngineCore
process, so that Python overhead on the API side cannot stall the GPU.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s15_server.py</code> /v1/completions with SSE streaming and cancellation, around an engine that you inject.</span>
<span class="k">Gate</span><span>Streams interleave, and a disconnect calls abort. Stage 27 connects the real engine.</span>
</div>

### 18 · The metrics that matter <span class="stage-diff">[**...]</span>

Export TTFT, TPOT and ITL, throughput, queue wait, KV utilization and
the preemption rate. Without the KV utilization and the preemption count
you can tune nothing, and you diagnose every performance problem
incorrectly.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s16_metrics.py</code> Prometheus-style metrics + a load generator with a Poisson arrival trace.</span>
<span class="k">Gate</span><span>A throughput/latency Pareto curve as you sweep max_num_seqs.</span>
</div>

## A7 · Modern vLLM

Where the field is now. The capstone uses stages 17, 18b and 19, so they
are not optional.

### 19 · Draft, verify, reject <span class="stage-diff">[*****]</span>

Decode waits on bandwidth, so a check on K tokens costs about as much as
one new token. Propose K tokens with something cheap, such as an n-gram
lookup or a very small model. Check them in one pass, and accept the
longest correct prefix. Modified rejection sampling keeps the output
distribution EXACTLY the same.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s17_speculative.py</code> N-gram speculator + rejection sampler + acceptance-rate telemetry. Then four_lines(): predict the floor, measure, divide, double.</span>
<span class="k">Gate</span><span>Speedup against acceptance rate. Prove that the output distribution does not move.</span>
</div>

### 20 · Weight-only quantization <span class="stage-diff">[****.]</span>

Decode reads every weight for every token. So half the weight bytes
gives almost half the decode time. Use INT8 or FP8 on the weights only,
with a scale for each channel, and dequantize in the kernel epilogue.
Quantize the KV cache too. It is the other big reader.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s18_quantization.py</code> INT8 weight-only linear + FP8 KV cache, with a fidelity guard: top-1 agreement and KL against bf16. Then four_lines(): predict the floor, measure, divide, double.</span>
<span class="k">Gate</span><span>tokens/sec and VRAM, against the KL from bf16 at the generated tokens of an ISL/OSL workload.</span>
</div>

### 21 · The dequantize belongs in the epilogue <span class="stage-diff">[****.]</span>

Stage 18 made the weight bytes half as many, and then gave the multiply
to PyTorch. PyTorch builds a bf16 copy of the weight before it can use
it. Time that honestly, and the quantization is a LOSS. Weight-only
quantization pays only when the kernel applies the scale at the end of
the dot product, to a register value. Then measure against cuBLAS, and
find the batch size where your kernel stops to win. That number is the
boundary between decode and prefill, in milliseconds.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s18b_gemv_cuda.py</code> An int8 GEMV with a fused dequantize epilogue, and a Linear that dispatches on batch size. Then four_lines(): predict the floor, measure, divide, double.</span>
<span class="k">Gate</span><span>At least 3x over dequantize-then-matmul, at least 1.5x over bf16 cuBLAS at one row, and the crossover where that stops.</span>
</div>

### 22 · Constrained output via logit masking <span class="stage-diff">[****.]</span>

Compile a grammar or a JSON schema to an FSM over token ids. Mask the
illegal logits at each step. Two parts are hard: the tokenizer
alignment, and the mask build. Keep the mask build off the critical
path, so that it does not stall the GPU.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s19_guided.py</code> JSON-schema-constrained sampling with a precomputed token mask cache.</span>
<span class="k">Gate</span><span>100% schema-valid outputs, and the ms/step the mask costs you.</span>
</div>

### 23 · Tensor parallelism (simulated on one GPU) <span class="stage-diff">[*****]</span>

Shard the attention heads and the MLP columns across the ranks, with one
all-reduce after the attention and one after the MLP: two in each layer.
You have one GPU, so run 2 gloo ranks on the CPU, and make the
collectives and the sharding logic correct. The lesson is where the
communication lands. It is not the speedup.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s20_tensor_parallel.py</code> Column/row-parallel Linear, 2-rank sharded model, output matches 1-rank.</span>
<span class="k">Gate</span><span>Correctness first. Then all-reduce bytes per token per layer.</span>
</div>

## A8 · The Capstone: One Engine

Every part you built, in one server, measured against the roof.

### 24 · The model runs on your paged cache <span class="stage-diff">[****.]</span>

The live engine hosted your stage 06 to 08c parts with slow glue. The HF
model cannot host them at all, because its cache grows by concatenation.
tvllm/model.py takes a flat batch and calls your attention backend. Your
backend writes K and V with your stage 08 kernel and reads them with
your stage 08c kernel. Put the decodes first, so that one launch serves
them all.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s21_paged_runner.py</code> A ModelRunner that runs a mixed batch of decodes and prefill chunks on the paged cache. Then four_lines(): predict the floor, measure, divide, double.</span>
<span class="k">Gate</span><span>Tokens identical to HF in fp32, for ragged batches, shuffled blocks and chunked prefill.</span>
</div>

### 25 · One engine from the parts <span class="stage-diff">[*****]</span>

Stages 10 and 11 were two schedulers that decided by counts, and the
live engine only executed their plans. Here they become one rule. Each
sequence has pending tokens: one for a decode, many for a prefill, all
of them after a preemption. Each step gives pending tokens to sequences
until the budget runs out. The prefix cache, the sampler and the
detokenizer attach to that loop.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s22_engine.py</code> An LLMEngine with a token budget, preemption by recompute, prefix caching, sampling and stop strings.</span>
<span class="k">Gate</span><span>Tokens identical to HF under preemption and with the prefix cache. No leaked block.</span>
</div>

### 26 · The real decode step, captured <span class="stage-diff">[****.]</span>

The eager step at batch 1 costs about two times the weight-read time,
because it is about a thousand small kernels. Capture the decode step
for each bucket. A padding row must write to slot -1, because a zero
slot writes into block 0, and block 0 belongs to a real sequence.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s23_graphs.py</code> A GraphedModelRunner that replays a captured decode step and runs everything else eager. Then four_lines(): predict the floor, measure, divide, double.</span>
<span class="k">Gate</span><span>At least 1.2x over eager at batch 1, and at least 50% of the weight-read floor.</span>
</div>

### 27 · Quantized weights in the engine <span class="stage-diff">[***..]</span>

Your stage 18b GEMV reads half the bytes of bf16, and it wins at a few
rows. Above a crossover, cuBLAS in bf16 wins, because the rows share the
weight read. So each matmul dispatches on its row count. Measure the
crossover in the real graphed step, not on one matrix: one matrix of a
small model fits in L2, and the result is wrong.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s24_quantized.py</code> Int8 weights in every matmul, with a dispatch to bf16 above a measured crossover. Then four_lines(): predict the floor, measure, divide, double.</span>
<span class="k">Gate</span><span>At least 1.2x at batch 1, no loss at batch 32, KL from bf16 at most 0.015 nats.</span>
</div>

### 28 · The KV cache in FP8 <span class="stage-diff">[*****]</span>

At long context the KV cache, not the weights, is most of the bytes of a
step. Store it in FP8. Your stage 08c kernel reads it with 16-byte
loads, converts two values with one instruction, and folds the key scale
into the query and the value scale into the output. Half the bytes to
read, and twice the tokens in the pool.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s24b_kv_fp8.py</code> FP8 write and attention kernels, calibrated scales, and an FP8 runner. Then four_lines(): predict the floor, measure, divide, double.</span>
<span class="k">Gate</span><span>At least 1.2x at 16 x 2048 tokens, KL from bf16 through the decode kernel at most 0.03 nats.</span>
</div>

### 29 · Speculative decoding inside the engine <span class="stage-diff">[****.]</span>

A verify of K draft tokens is K+1 decode rows that share one block
table. Each row sees its own context, so the verify is causal, runs on
your stage 08c kernel, and replays a captured graph. Greedy accepts
while the draft matches the argmax. Sampling uses the stage 17 rule with
a one-hot draft, so the output does not move.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s25_speculative.py</code> A SpeculativeEngine with n-gram drafts and an exact verify.</span>
<span class="k">Gate</span><span>Greedy output identical in fp32, the target distribution kept, at least 1.5x on a copy task.</span>
</div>

### 30 · Guided JSON decoding inside the engine <span class="stage-diff">[*****]</span>

Stage 19 validated the whole text again for every token, and its cache
never hit. A real engine walks a character automaton, and it caches the
masks by automaton state: a whole JSON answer needs a few dozen states.
Near max_tokens, admit only the tokens that bring the object closer to
complete, or the answer ends open.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s26_guided.py</code> A JSON automaton, masks cached by state, a forced close, and a GuidedEngine.</span>
<span class="k">Gate</span><span>Every answer parses. The automaton agrees with json. A second round builds almost no mask.</span>
</div>

### 31 · The server, for real <span class="stage-diff">[****.]</span>

A real step holds the GPU for 5 to 50 ms, and the stage 15 loop runs it
inside the event loop. Run step() in a worker thread, and send
add_request and abort to it through a deque. Then speak the API that
clients send: chat, sampling fields, stop strings, streaming, JSON mode,
usage and the real finish_reason.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s27_serve.py</code> /v1/completions and /v1/chat/completions on your full engine, with /metrics.</span>
<span class="k">Gate</span><span>Chat, JSON mode, streaming and stop strings work. A disconnect frees real blocks. The event loop stays free.</span>
</div>

### 32 · Against the roof <span class="stage-diff">[***..]</span>

A throughput number alone says nothing, because it changes from card to
card. The floor of a step also changes, by the same factor. So divide:
the floor of the steps that your engine ran, divided by the time that
they took. That ratio travels between cards, and it tells you what
remains to win.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s28_bench.py</code> A benchmark that measures the engine against the roofline floor of its own steps.</span>
<span class="k">Gate</span><span>At least 30% of the floor, and at least 2x your stage 05 engine on the same requests.</span>
</div>

## A9 · Beyond the Capstone

Stage 29 is core: the prefix cache of stage 22 needs eviction. Stages 30
and 31 are optional extensions. Their checks are thin, and no
measurement of the core ladder asks for them.

### 33 · LRU prefix eviction and cache-aware admission <span class="stage-diff">[****.]</span>

Prefix caching without eviction either leaks blocks forever or pins the
pool when multiple long documents circulate. Retain blocks at refcount 0
in an LRU order, reclaim them under memory pressure, and order the
waiting queue by prefix hit depth to maximize prefill reuse.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s29_lru_cache.py</code> An LRUPrefixCache and CacheAwareScheduler that evicts inactive blocks and prioritizes cache hits.</span>
<span class="k">Gate</span><span>Zero leaks, deterministic LRU order under eviction, and hit-rate prioritized admission.</span>
</div>

### 34 · Multi-LoRA serving and batched GEMV <span class="stage-diff">[****.]</span>

Serving 50 fine-tuned adapters simultaneously cannot afford 50 separate
forward passes. Batching them with standard GEMM fails because adapter
weights differ per request. Batched GEMV (BGMV) routes each sequence's
activations through its assigned adapter rank matrices in a single
launch, scaling multi-tenant serving at zero base-model overhead.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s30_multi_lora.py</code> A multi-LoRA dispatch engine and batched GEMV kernel simulation.</span>
<span class="k">Gate</span><span>Correctness against unbatched LoRA passes and multi-adapter throughput scaling.</span>
</div>

### 35 · DeepSeek Multi-Head Latent Attention (MLA) <span class="stage-diff">[*****]</span>

Full KV caches at 128k context consume hundreds of gigabytes. DeepSeek
compresses KV into low-rank latents with decoupled RoPE. During decode,
uncompression matrices are absorbed into query and output projections:
attention runs directly against the compressed cache without expanding K
and V in VRAM, saving over 80% of KV cache bandwidth with zero loss in
precision.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s31_mla.py</code> MLA compression, baseline unabsorbed attention, and the exact decode weight absorption trick.</span>
<span class="k">Gate</span><span>Exact numerical equivalence to standard attention and >80% KV memory reduction.</span>
</div>

<!-- END LADDER -->
