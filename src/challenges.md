# Challenges

Every question in the book, stripped of context and answers. Revision by
retrieval, not rereading.

## 1 · Twenty-Five Microseconds

1. A 4 KB write measures 900 ns. Which layer, and which floor decided it?
2. A service acks after `write()` returns. Which failure loses acked data,
   and which doesn't?
3. Someone claims a 3× speedup. First question, and what would make you
   reach for `perf`?
4. Derive the max durable-write rate for one `fsync` per request, then
   explain why real databases beat it.

## 2 · The Ladder

1. A crash harness uses `kill -9` *and* a clean `reboot` between runs.
   Which row does that validate, and which row does it still miss?
2. Does `echo b > /proc/sysrq-trigger` sit closer to `kill -9` or to a
   real power cut? Justify it from what each one destroys.
3. An NVMe spec sheet doesn't mention power-loss protection. What
   experiment tells you whether it has it, without opening the case?
4. Redraw the power-loss column as a function of shared-UPS failure
   rate. At what point does "no PLP on the drive" stop being a real risk?

## 3 · The Barrier

1. Batching 100 records behind one `fsync`: best-case throughput gain,
   and what makes the real gain fall short of it?
2. When does `fdatasync` not actually save you a barrier crossing?
3. Two threads `fsync` the same file near-simultaneously. Does the
   second call cost a full barrier or something cheaper, and how would you
   find out?
4. Does `O_DIRECT` make `fsync` unnecessary? Name the specific claim
   `fsync` makes that a direct write alone doesn't.

## 4 · Write-Ahead

1. Why does calling `fsync` in a retry loop until it "succeeds three
   times" not fix the terminal-error problem?
2. WAL fsync succeeds, ACK is sent, then the process crashes before data
   pages are written. Where does correct final state come from?
3. What changes about worst-case commit latency if the ACK moves to
   after the data-page write instead of right after the WAL fsync?
4. `full_page_writes` doubles WAL volume after every checkpoint. Reduce
   that cost without weakening the torn-page guarantee.

## 5 · Group Commit

1. At exactly one arrival per fsync-latency window, what does adaptive
   batching's average batch size converge to, versus fixed N=2?
2. Load spikes past what a 200 µs floor can drain. Does the floor still
   help, or start hurting?
3. Two writers share one log file. What has to be true about their
   fsync coordination for adaptive batching to stay correct?
4. Redo the arithmetic for two durability tiers: some callers need the
   fsync ack, some are fine off the page cache. One batch, or two?

## 6 · Where the Truth Stops

1. Record 3's CRC matches, but record 2 before it was torn and
   truncated the file mid-record. Does record 3's match mean anything?
2. Upgrading 16-bit → 32-bit checksum: new odds of undetected
   corruption, and at what write rate would you expect one over a year?
3. CRC isn't cryptographically secure. Under what threat model does
   that matter for crash recovery, and under what model doesn't it?
4. Design a scheme where a torn checksum trailer still gets the record
   correctly rejected. What has to be true about where it lives?

## 7 · The Ridge

1. What batch size reaches ~156 FLOP/byte, and what has to be true
   about traffic for that batch to fill without unacceptable latency?
2. A 13B model roughly doubles both weight bytes and FLOPs per token.
   Does its ridge-crossing batch size move, and which way?
3. fp16 → int8 halves bytes without changing FLOPs much. Recompute
   arithmetic intensity at batch 1. Closer to the ridge or not?
4. Redo the FLOP/byte arithmetic for a 2048-token prefill pass
   (matrix-matrix, not matrix-vector). Compute-bound or memory-bound?

## 8 · The Cache That Ate the Batch

1. GQA with group size 8 divides KV cache per token by ~8. Recompute
   the batch ceiling and check it against the ridge's target of ~156.
2. Design a memory-accounting scheme for mixed-length sequences that
   doesn't pad everyone to the max length.
3. int8 KV quantization halves bytes/token. Does it move the ridge
   point, the batch ceiling, or both?
4. Estimate whether a 70B model's KV-cache-per-token is closer to 5× or
   10× the 7B figure, and redo the 80 GB budget.

## 9 · The Slot That Waited

1. The loop evicts finished sequences before the forward pass. What
   happens if you evict after it, and precisely which token goes missing?
2. Admitting a request means splicing its prefilled KV into a batch whose
   sequences are all at different lengths. What is the copy cost
   proportional to, and why does that make admission expensive exactly
   when you want it cheap?
3. What output-length distribution still produces low occupancy under
   iteration-level scheduling, and does it occur in practice?
4. Design the admission rule for a request arriving at a full batch,
   given that you do not know how long it will run.

## 10 · A Page Table for Tokens

1. Average internal fragmentation per sequence at block sizes 1, 16 and
   256. What goes wrong at each end? One failure isn't about memory.
2. Paging drops the admission cost from 1 GB to one block. Write the
   admission rule, then find the failure it introduces mid-generation.
3. Two sequences share a block by refcount; one writes into it. What must
   happen, in what order, and what breaks if the refcount is decremented
   after the copy instead of before?
4. Why isn't hashing a block's own tokens enough to recognise a shared
   prefix, and what else goes into the hash? (The failure is a
   correctness bug and a privacy bug at once.)

## 11 · Below the Floor

1. Count the real GPU operations in one transformer layer, redo the
   per-launch division, and say whether 17 µs still looks like dispatch.
2. Graphs are captured at batch 1, 2, 4, 8 and padded up. Cost of that
   padding at batch 5, and when it exceeds the launch overhead it saves.
3. Redo the floor and the gap for a 7B model on the same card. Is launch
   overhead a larger or smaller fraction, and which deployments care?
4. Graph replay reuses one output buffer. Describe the bug that causes
   under concurrency, and how you would detect it given that it produces
   plausible text rather than a crash.

## 12 · Spending the Idle

1. Batch 32 with K=5 verification sits at what arithmetic intensity?
   Compare to the ridge and say whether both techniques are still free
   together.
2. Derive expected tokens per pass from the acceptance rate a, then find
   the K that maximizes it once the draft costs 5% of a target pass per
   proposed token.
3. Is acceptance rate higher for code or for poetry? Justify it from the
   target's output distribution, and say what that implies about
   advertising one speedup number.
4. Order the four throughput levers (batch, page, delete launch
   overhead, speculate) for a deployment averaging 30 output tokens at 4
   requests/sec, using arithmetic rather than preference.
