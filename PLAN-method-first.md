# Plan: make the book sell the method

Status: proposal, 2026-11-02. Nothing here is applied yet. Not published
(outside `src/`).

## The verdict

**Does one idea hold throughout?** Mostly, yes. The preface says it ("I
would rather hand you the habit than the facts"), the introduction states
it as a four-step loop (name the candidates, name the ratio, do the
division, see what survives), and the chapters keep pointing back at each
other: group commit returns four times, the floor test runs in both
directions, virtual memory turns up under PagedAttention. Chapter 12's
design note even names the thread: every chapter finds the one quantity
that is genuinely scarce.

But a reader cannot see that from the outside. The table of contents
sells systems (Durability, Accelerators, Building the Answer, a vLLM
course). The Rules Index, "the most important page", is 3 method rules
and 11 system facts. The general tools exist, but each one wears the
clothes of one system, and most of them are only named in design notes.

**Is it engaging?** Yes. Every chapter opens on an anomaly, the voice
works, the quips land, and chapter 6 does a CRC by hand. Strongest:
1, 3, 6, 7, 11, and the design note of 10. Weakest: 4 (a recital of
kernel facts, and it says so: "There is no arithmetic to do here") and 2
(its ratio is "a category error", not a division).

## What breaks the one idea, and trust

1. **Two chapters leave the method.** Chapter 4 has no division at all;
   chapter 2's division counts trials, not costs. Both carry good tools
   (independence, reachability) that the method should own.
2. **Anomalies presented as measurements that were not measured.** The
   method's own rule (chapter 11's design note) is to compute the floor
   before measuring. Several chapters do the opposite: they present a
   derived number as an observation.
   - ch 8: "It dies at 64": observed, or derived from 66 minus "a couple"?
   - ch 9: "It reads like a batch of sixteen": observed?
   - ch 10: "The mean request runs to about 350 tokens": no source.
   - ch 12: "Here is a measurement that ought to be impossible", but the
     7 ms is computed in 12.3, not measured.
   - ch 3: "We measured about 100 µs" for an 8-byte fsync: the book's lab
     can measure this; the number should come from it, dated.
   Real measurements exist for ch 1 (now) and ch 11 (laptop 4080). Every
   other anomaly should be either measured and dated, or framed as
   "suppose".
3. **One arithmetic error.** ch 5: "Ten million times worse". 100 s ÷
   10 ms = 10,000. In a book about doing the division, this costs most.
4. **Unsourced or inconsistent facts.**
   - ch 4: PostgreSQL 2018, Linux 4.13 `errseq_t`: need sources.
   - ch 5: fsync call rate costs "years off the drive's life": no source.
   - ch 10: "solved in 1961" and "shipped in 1962" in the same chapter.
   - ch 10: the vLLM paper's 60 to 80% waste: cite it.
   - ch 12: "it took the field until 2023". From memory, not yet
     verified: blockwise parallel decoding (Stern et al.) is from 2018,
     and the speculative decoding papers are from late 2022 and early
     2023. Check before the chapter states a year.
   - ch 1, 3, 7, 8, 12: undated hardware numbers (A100, its price, NVMe
     and fsync latencies). Under the timelessness rules they become dated
     examples.
5. **First-person stories that may not be the author's.** ch 1 (the 400×
   loop) and others. Each must be a real memory or be retold as a known
   pattern. Only the author can sort these.
6. **The same tool under two names.** Independence is taught in ch 4
   (`full_page_writes`) and again in ch 6 (CRC) without one name.
   Amortization appears in ch 3, 5, 7, 12 under four names.

## The toolkit the book already contains

17 general tools, found by reading every chapter. Each one passes the 10×
test: it stays true if every hardware number moves by 10×.

| # | Tool | Taught in | Rule now |
|---|---|---|---|
| T1 | Ratio triage: name the spread before the answer | 1 | 1 |
| T2 | Floor test: beat the floor and the work did not happen | 1, 3 | 2 |
| T3 | Match the instrument to the ratio | 1 | 3 |
| T4 | A cost that ignores the payload is charged per event | 3 | (in 5) |
| T5 | Amortize: pay a fixed cost once per batch | 3, 5, 7, 12 | 5 |
| T6 | Replace a tuned constant with a runtime observation | 5 | 7 |
| T7 | A test proves nothing about a layer it cannot reach; 0 in n gives about 3/n | 2 | 4 |
| T8 | Recovery and checks must be independent of what failed | 4, 6 | 6, 8 |
| T9 | Ask what your check does on its worst input | 6 | 8 |
| T10 | Work per byte decides which resource limits you (roofline) | 7, 12 | 9 |
| T11 | Every resource has a ceiling; the lowest one binds | 8 | 10 |
| T12 | Occupancy: compare what you bought with what you used | 9 | 11 |
| T13 | A waste fraction cannot be bought away; indirection bounds it | 10 | 12 |
| T14 | Describe the problem in its own terms; find the old shape | 10, intro | none |
| T15 | Well above the floor: an unmodelled participant; divide the gap by a count | 11 | 13 |
| T16 | Decisions repeated identically: record once, replay | 11 | none |
| T17 | An idle resource is a budget: spend the abundant to save the scarce | 12 | 14 |

## The proposed structure

The four-step loop stays the spine. The parts are named after what the
loop finds, not after systems. Every chapter keeps its anomaly, its
arithmetic and its voice; what changes is what it claims to teach, its
rule, and where it sits.

| Part | Tools | Chapters (existing, regrouped) |
|---|---|---|
| I. The Method | T1, T2, T3 | 1 |
| II. Cost Has a Shape | T4, T5, T6, T10 | 3, 5, 7 |
| III. The Scarce Thing | T11, T12, T13, T17 | 8, 9, 10, 12 |
| IV. Believing Your Evidence | T7, T8, T9 | 2, 4, 6 |
| V. When the Floor Is Wrong | T15, T16, T14 | 11, and a new chapter on T14 |
| The Course | an exercise, not the ending | course |

Chapter numbers in URLs: the files and the rule anchor ids stay as they
are (invariant 1). Only `SUMMARY.md` order and part titles change. Whether
the visible chapter numbers change is a decision for the author.

## Rules: general first, the system as the example

Rule anchor ids never change. The title and sentence do.

| Rule (id) | Now | Proposed |
|---|---|---|
| 4 `failure-fidelity` | Test the failure you claim to survive | Keep. Already general. |
| 5 `boundary-not-spray` | Buy durability at boundaries, not by the record | When a cost does not move with the payload, it is charged per event: pay it once per batch. *Example: fsync.* |
| 6 `fsync-terminal` | fsync failure is not retryable | When a failure destroys what you would retry with, retrying is not recovery: rebuild from an independent copy. *Example: Linux fsync, 2018.* |
| 7 `adaptive-batching` | Let the barrier set its own batch size | Let an event the system can observe close the batch, not a constant. *Example: group commit.* |
| 8 `checksum-the-edge` | Checksum every record; seed the register nonzero | A check written in the same act as the data fails with it; test every check on its worst input. *Example: CRC.* |
| 9 `ridge-before-flops` | Check arithmetic intensity before adding FLOPs | Keep. Already general. |
| 10 `kv-budget-not-guess` | Size your batch from the KV budget | Before blaming the scheduler, compute the ceiling of every resource; the lowest one is the wall. *Example: KV cache.* |
| 11 `iteration-scheduling` | Release the slot when the sequence ends | Release a resource when its work ends, not when its group ends. *Example: continuous batching.* |
| 12 `blocks-not-reservations` | Page the cache | When per-client growth is unpredictable, allocate fixed blocks through an indirection; waste falls under one block. *Example: PagedAttention.* |
| 13 `floor-gap-is-cpu` | A workload that misses its roofline floor... | Well above the floor means a participant you did not model: divide the gap by a count. *Example: kernel launches.* |
| 14 `spend-below-ridge` | Below the ridge, spend compute on work that might be wasted | An idle resource is a budget: spend it on work that might be thrown away. *Example: speculative decoding.* |
| new | (none) | Describe the problem in its own terms before its vocabulary. *Example: virtual memory, 1962.* |
| new | (none) | Work that repeats identically can be recorded once and replayed. *Example: CUDA graphs.* |

## Timelessness rules (to add to CLAUDE.md as an invariant)

1. Every number in `src/` is one of: derived on the page; a physical
   law; a stable interface promise (POSIX, a published standard); or a
   dated observation ("in 2026, on this machine"). No undated hardware or
   version numbers.
2. Every rule and conclusion passes the 10× test.
3. Arguments run in symbols and ratios first, then one dated example.
4. Append only. New hardware adds a dated field note or a new worked
   example. Old ones are never rewritten.
5. Every anomaly is either measured (lab, date, machine) or framed as
   "suppose". Never a derived number presented as an observation.

## Order of work

1. Author decisions: approve the structure; sort the first-person
   stories; say whether ch 8, 9, 10 anomalies were measured.
2. Add the timelessness invariant to CLAUDE.md.
3. Fix the trust items that need no restructure: the ch 5 arithmetic,
   the ch 10 year, sources for ch 4, 10, 12.
4. Rewrite the 11 rules general-first; regenerate the Rules Index.
5. Restructure `SUMMARY.md` and the introduction's "Why storage, and
   then GPUs" section around the parts.
6. Chapter by chapter: date the numbers, mark measured versus supposed,
   add the dated example framing. One chapter at a time, author review
   after each.
7. The new chapter on T14.
