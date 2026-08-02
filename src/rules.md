# Rules Index

The page to open at 11pm. Each rule links back to the derivation that
earned it. If you can rebuild the argument from the rule alone, you're
done; if not, follow the link.

## I. The Method

- **[Ratio triage](./01-five-microseconds.md#ratio-triage)**: sort next
  questions by the spread between their possible answers. >10×: ask now.
  <2×: it's a detail.
- **[The floor test](./01-five-microseconds.md#floor-test)**: when a
  measurement beats your theoretical floor, the work didn't happen.
- **[Match the instrument to the ratio](./01-five-microseconds.md#instrument-precision)**:
  1000× apart, wall clock. 1.5× apart, counters.

## II. Durability

- **[Test the failure you claim to survive](./02-the-ladder.md#failure-fidelity)**:
  a crash test that can't reach the layer your data lives in has
  proven nothing about that layer.
- **[Buy durability at boundaries, not by the record](./03-the-barrier.md#boundary-not-spray)**:
  fsync cost is dominated by the round trip, not the bytes. Pay it
  once per boundary, never once per write.
- **[fsync failure is not retryable](./04-write-ahead.md#fsync-terminal)**:
  once fsync errors, the page behind it is already gone. Recover from
  an independent durable source, don't retry the same call.
- **[Let the barrier set its own batch size](./05-group-commit.md#adaptive-batching)**:
  close the batch when the in-flight fsync returns, not when a counter
  hits a constant.
- **[Checksum every record; seed the register nonzero](./06-where-the-truth-stops.md#checksum-the-edge)**:
  torn writes pass structural checks by accident. Only arithmetic
  over the content finds where the truth stops.

## III. Accelerators

- **[Check arithmetic intensity before adding FLOPs](./07-the-ridge.md#ridge-before-flops)**:
  below the ridge point, more compute buys nothing. The wait is on
  bytes, not operations.
- **[Size your batch from the KV budget, not a guess](./08-kv-cache.md#kv-budget-not-guess)**:
  before blaming scheduling for a batch ceiling, check bytes-per-token
  × context length × concurrency against free memory.
