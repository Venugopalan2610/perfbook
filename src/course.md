# The Course

> Twenty stages, and not one of them passes because the code ran.

Chapter 12 ends by saying that this is where the book stops deriving and
[vllm-from-scratch](https://github.com/Venugopalan2610/vllm-from-scratch)
starts building. This page is that repository's map: what the twenty
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

There are 229 checks across the twenty stages, and most of them assert a
measurement rather than a behaviour. `./vc submit` refuses to advance
while anything is red, so there is no way to skip a stage by being
impatient with it. (222 checks if you take the JAX route, which is two
sections down, and which is the same twenty stages.)

That refusal is the whole product. Anybody can read twenty descriptions
of PagedAttention. Rather fewer people have had a test inform them that
their page table is perfectly correct and four times slower than the
contiguous cache it replaced, which is the actual experience of writing
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
them. Stage 8 is a Triton kernel, stage 12 captures CUDA graphs, stage
18 wants FP8: on a laptop with integrated graphics those are three
stages you can read and not do. On a T4 they run.

One caveat, and it is a real one. A Colab runtime is temporary. Your
progress lives in `.progress.json` inside that container, and when the
session resets it goes, along with everything you wrote. That is fine
for working through the first arc and finding out whether you care. It
is not where you would do all twenty. The notebook's last cell pushes
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
for your own card rather than the book's A100, and `./vc peek` if you
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

Twenty stages either way. Eleven of them get a JAX twin, so you edit
`app/j08_paged_pallas.py` where the other track edits
`app/s08_paged_triton.py`. The remaining nine are not twins. They are
the same file.

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

Stage 8 is Pallas rather than Triton, and the online softmax is, line for
line, the same idea. What changes is the indirection. Pallas gives you a
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

Six of the twelve chapters have a stage that builds what they derived.
Those are the ones where reading and building are the same activity done
twice, and doing both in that order is the intended path.

| Chapter | Stages |
|---|---|
| [The Ridge](./07-the-ridge.md) | 01–03, the naive loop and the roofline |
| [The Cache That Ate the Batch](./08-kv-cache.md) | 02, KV bytes per token |
| [The Slot That Waited](./09-the-slot-that-waited.md) | 04–05, static then continuous batching |
| [A Page Table for Tokens](./10-a-page-table-for-tokens.md) | 06–09, blocks, paged attention, prefix cache |
| [Below the Floor](./11-below-the-floor.md) | 03 and 12, the gap and CUDA graphs |
| [Spending the Idle](./12-spending-the-idle.md) | 17, the n-gram proposer and rejection sampler |

The rest have no chapter deriving them, and I would rather say so than
pretend the coverage is complete. Stages 10, 11, 13 through 16 and 18
through 20 build the scheduler, chunked prefill, the sampler, the
detokenizer, the server, quantization, guided decoding and tensor
parallelism. They are good stages. They are simply ahead of the prose.

## The ladder

Seven arcs. The order is not the order a textbook would choose: it is
roughly the order the ideas were actually discovered, which means every
stage exists because the previous one broke in a specific way, and the
guide for each one opens by telling you what that way was.

The pips are how hard the code is, not how hard the idea is. Stage 3 is
two stars and is the most important thing in the course.

<!-- BEGIN LADDER -->

## A0 · The Naive Loop

Build the slow thing first, and measure it, so every later win is a
number.

### 01 · Greedy decode, no cache <span class="stage-diff">[*....]</span>

A transformer forward pass is a pure function of the whole prefix.
Generating N tokens naively costs O(N^2) attention work because you
recompute every previous token's K and V on every single step.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s01_naive.py</code> generate() that emits tokens one at a time from a HF model.</span>
<span class="k">Gate</span><span>tokens/sec at 128 output tokens. This is your rock bottom.</span>
</div>

### 02 · The KV cache <span class="stage-diff">[**...]</span>

K and V for a token never change once computed. Cache them and each
decode step becomes a single-token forward pass: O(N) total. This is
also the moment memory becomes your enemy instead of compute.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s02_cache.py</code> Per-sequence contiguous KV cache; decode attends over cache+new token.</span>
<span class="k">Gate</span><span>tokens/sec (expect a large multiple of stage 1) and bytes of KV per token.</span>
</div>

### 03 · Prefill vs decode: two different machines <span class="stage-diff">[**...]</span>

Prefill is compute-bound (big GEMMs, high arithmetic intensity). Decode
is memory-bandwidth-bound (batch size 1 means every weight is read from
HBM to produce one token). They want opposite optimizations. This is THE
fact that explains every design decision downstream.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s03_roofline.py</code> A microbenchmark separating prefill ms/token from decode ms/token.</span>
<span class="k">Gate</span><span>Achieved GB/s during decode vs your GPU's peak. You'll be near peak.</span>
</div>

## A1 · Batching

Decode is bandwidth-bound, so extra sequences are nearly free. Exploit
that.

### 04 · Static batching with padding <span class="stage-diff">[**...]</span>

Batching amortizes the weight read across sequences: 8x the tokens for
almost 1x the time. But a static batch runs until its SLOWEST member
finishes, and short sequences sit padded and idle, burning the slot.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s04_static_batch.py</code> Left-padded batch of N prompts, shared decode loop, attention mask.</span>
<span class="k">Gate</span><span>Throughput vs batch size, AND the % of decoded token-slots wasted on padding.</span>
</div>

### 05 · Continuous batching (iteration-level scheduling) <span class="stage-diff">[***..]</span>

Schedule per ITERATION, not per request. When a sequence emits EOS,
evict it that same step and admit a waiting one into its slot. From Orca
(OSDI '22). Typically 2-4x over static batching on real traffic, and it
is the single largest throughput win in this entire repo.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s05_continuous.py</code> A step() loop over a mutable running-set; requests join and leave mid-flight.</span>
<span class="k">Gate</span><span>Throughput on a Poisson arrival trace + p50/p99 latency vs stage 4.</span>
</div>

## A2 · PagedAttention

The idea vLLM is named after. Virtual memory, applied to the KV cache.

### 06 · Blocks, block tables, free list <span class="stage-diff">[***..]</span>

Contiguous per-sequence caches force you to pre-allocate for max_len, so
real serving wastes 60-80% of KV memory to internal fragmentation and
reservation. Chop the cache into fixed 16-token blocks, hand them out on
demand, and keep a per-sequence block table (a page table). Waste drops
to under one block per sequence.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s06_blocks.py</code> BlockAllocator + BlockTable. No attention changes yet.</span>
<span class="k">Gate</span><span>Sequences resident in 12GB, paged vs contiguous. Expect a big jump.</span>
</div>

### 07 · Attention that reads through the page table <span class="stage-diff">[****.]</span>

The kernel must gather K/V from scattered blocks instead of striding a
contiguous tensor. Do it in PyTorch first (index_select + SDPA) to get
it CORRECT, then keep that as the reference oracle forever.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s07_paged_attn.py</code> paged_attn() in pure PyTorch, bit-comparable to stage 2's output.</span>
<span class="k">Gate</span><span>Correctness vs the contiguous implementation, then the slowdown you just ate.</span>
</div>

### 08 · The same thing, fast <span class="stage-diff">[*****]</span>

One program per (sequence, head, block); stream K/V tiles through SRAM;
online-softmax so you never materialize the full score row. Decode
attention is bandwidth-bound, so your kernel's job is coalesced reads.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s08_paged_triton.py</code> A Triton paged decode kernel that beats the PyTorch version.</span>
<span class="k">Gate</span><span>us/token vs stage 7, and vs real vLLM's kernel on the same shapes.</span>
</div>

### 09 · Copy-on-write and automatic prefix caching <span class="stage-diff">[****.]</span>

Block tables make sharing trivial: two sequences can point at the same
physical block. Refcount them, copy-on-write when one diverges. Then
hash block contents and reuse across REQUESTS: a shared system prompt
gets prefilled once for everybody. This is why APC feels like cheating.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s09_prefix.py</code> Refcounted blocks, CoW on write, content-hash prefix cache with LRU eviction.</span>
<span class="k">Gate</span><span>TTFT for a 2000-token shared system prompt, cold vs warm.</span>
</div>

## A3 · The Scheduler

You have finite KV memory and infinite requests. Decide who runs.

### 10 · Waiting / running / swapped, and preemption <span class="stage-diff">[****.]</span>

Sequences grow one block at a time, so the batch you admitted can run
out of memory mid-decode. You need preemption: either SWAP blocks to CPU
or DROP them and recompute later. Recompute usually wins, because
prefill is fast and PCIe is not.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s10_scheduler.py</code> Three queues, a KV budget check per step, preempt-by-recompute.</span>
<span class="k">Gate</span><span>Behavior under overload: does throughput degrade gracefully or collapse?</span>
</div>

### 11 · Chunked prefill and mixed batches <span class="stage-diff">[****.]</span>

One 8000-token prefill stalls every decoding sequence for a whole step,
wrecking inter-token latency for everyone. Split prefill into chunks and
co-schedule chunks with decodes in the SAME batch. From Sarathi-Serve.
This is the throughput/latency dial in every modern serving stack.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s11_chunked.py</code> A unified batch of [prefill chunks + decode tokens] with correct positions.</span>
<span class="k">Gate</span><span>p99 inter-token latency with a long prompt in flight. Before vs after.</span>
</div>

## A4 · Making It Actually Fast

Everything left is overhead removal.

### 12 · CUDA graphs for the decode step <span class="stage-diff">[****.]</span>

At batch 1 a decode step is ~1ms of GPU work and can be ~1ms of Python
and kernel-launch overhead. Capture the whole step as a graph and replay
it. Requires static shapes, so you capture at bucketed batch sizes and
pad up to the nearest bucket.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s12_cudagraph.py</code> Graph capture per bucket, replay path, eager fallback.</span>
<span class="k">Gate</span><span>us/step at batch 1, 2, 4, 8. Watch the Python tax vanish.</span>
</div>

### 13 · A real batched sampler <span class="stage-diff">[***..]</span>

Every request has its own temperature, top-k, top-p, penalties, and
seed, and they all must be applied in ONE vectorized pass over the
batch. The naive per-request Python loop silently becomes your
bottleneck once the kernels are fast.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s13_sampler.py</code> Vectorized temp/top-k/top-p/repetition penalty, per-request seeded RNG.</span>
<span class="k">Gate</span><span>Sampler ms/step at batch 64, plus a distributional test that top-p is exact.</span>
</div>

### 14 · Incremental detokenization and stop conditions <span class="stage-diff">[***..]</span>

You cannot decode tokens independently: BPE pieces, multi-byte UTF-8,
and leading-space rules mean naive streaming emits mojibake and doubled
spaces. Stop STRINGS can also straddle a token boundary, so you must
buffer. Boring, and the source of most user-visible bugs in real
servers.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s14_detokenizer.py</code> Streaming detokenizer with a lookback window + straddling stop-string check.</span>
<span class="k">Gate</span><span>Fuzz test: streamed output must equal batch-decoded output, always.</span>
</div>

## A5 · The Server

Turn the engine into something you can curl.

### 15 · Async engine + OpenAI-compatible API <span class="stage-diff">[***..]</span>

The engine loop must never block on HTTP, and HTTP must never block on
the GPU. One process runs step() forever; requests are futures/queues
fed into it. Real vLLM V1 pushes this further, into a separate
EngineCore process, so Python overhead on the API side cannot stall the
GPU.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s15_server.py</code> /v1/chat/completions with SSE streaming, cancellation, backpressure.</span>
<span class="k">Gate</span><span>TTFT under concurrent load; verify a client disconnect frees KV blocks.</span>
</div>

### 16 · The metrics that matter <span class="stage-diff">[**...]</span>

TTFT, TPOT/ITL, throughput, queue wait, KV utilization, preemption rate.
If you cannot see KV utilization and preemption count, you cannot tune
anything, and you will misdiagnose every performance problem you hit.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s16_metrics.py</code> Prometheus-style metrics + a load generator with a Poisson arrival trace.</span>
<span class="k">Gate</span><span>A throughput/latency Pareto curve as you sweep max_num_seqs.</span>
</div>

## A6 · Modern vLLM

Optional, but this is where the field currently is.

### 17 · Draft, verify, reject <span class="stage-diff">[*****]</span>

Decode is bandwidth-bound, so verifying K tokens costs about the same as
generating 1. Propose K with something cheap (n-gram lookup or a tiny
model), verify in one pass, accept the longest correct prefix. Modified
rejection sampling keeps the output distribution EXACTLY unchanged.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s17_speculative.py</code> N-gram speculator + rejection sampler + acceptance-rate telemetry.</span>
<span class="k">Gate</span><span>Speedup vs acceptance rate. Prove the output distribution is unbiased.</span>
</div>

### 18 · Weight-only quantization <span class="stage-diff">[****.]</span>

Decode reads every weight per token, so halving weight bytes nearly
halves decode time. INT8/FP8 weight-only with per-channel scales,
dequantized in the kernel epilogue. Also quantize the KV cache: it is
the other big reader.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s18_quantization.py</code> INT8 weight-only linear + FP8 KV cache, with a perplexity guard.</span>
<span class="k">Gate</span><span>tokens/sec and VRAM vs perplexity delta on a fixed text sample.</span>
</div>

### 19 · Constrained output via logit masking <span class="stage-diff">[****.]</span>

Compile a grammar/JSON schema to an FSM over token ids, and mask illegal
logits each step. The hard parts are tokenizer alignment and doing the
mask build off the critical path so it does not stall the GPU.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s19_guided.py</code> JSON-schema-constrained sampling with a precomputed token mask cache.</span>
<span class="k">Gate</span><span>100% schema-valid outputs, and the ms/step the mask costs you.</span>
</div>

### 20 · Tensor parallelism (simulated on one GPU) <span class="stage-diff">[*****]</span>

Shard attention heads and MLP columns across ranks; one all-reduce per
layer. You have one GPU, so run 2 ranks on it with NCCL to get the
collectives and the sharding logic right. The lesson is where the
communication lands, not the speedup.

<div class="stage-meta">
<span class="k">Build</span><span><code>app/s20_tensor_parallel.py</code> Column/row-parallel Linear, 2-rank sharded model, output matches 1-rank.</span>
<span class="k">Gate</span><span>Correctness first. Then all-reduce bytes per token per layer.</span>
</div>

<!-- END LADDER -->
