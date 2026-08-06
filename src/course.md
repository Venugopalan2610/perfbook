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
impatient with it.

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
