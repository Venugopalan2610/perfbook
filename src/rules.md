# Rules Index

The page to open at 11pm. Each rule states a general tool first and
names the system it was derived on as its example, and each links back
to the derivation that earned it. If you can rebuild the argument from
the rule alone, you're done; if not, follow the link.

## I. The Method

- **[1 · Ratio triage](./01-twenty-five-microseconds.md#ratio-triage)**:
  sort your next questions by the spread between their possible
  answers. More than 10× apart: ask it now. Less than 2×: it's a detail.
- **[2 · The floor test](./01-twenty-five-microseconds.md#floor-test)**:
  when a measurement beats your theoretical floor, the system is not
  fast. The work did not happen.
- **[3 · Match the instrument to the ratio](./01-twenty-five-microseconds.md#instrument-precision)**:
  1000× apart, a wall clock. 20× apart, a wall clock used carefully.
  1.5× apart, counters and statistics.

## II. Cost Has a Shape

- **[4 · A cost that ignores the payload is charged per event](./03-the-barrier.md#boundary-not-spray)**:
  write the cost as a fixed price per trip plus a price per byte. When
  the trip dominates, pay it once per batch, never once per item.
  *Example: `fsync`, once per boundary you need to defend.*
- **[5 · Let something you can observe close the batch, not a constant](./05-group-commit.md#adaptive-batching)**:
  a constant is a guess about load; an observation adapts to it.
  *Example: group commit closes the batch when the in-flight `fsync`
  returns.*
- **[6 · Work per byte decides which resource limits you](./07-the-ridge.md#ridge-before-flops)**:
  compare the work's operations per byte with the machine's compute
  over bandwidth. Below that ridge, more compute buys nothing.
  *Example: a GPU decoding one token at a time.*

## III. The Scarce Thing

- **[7 · Every resource has a ceiling; the lowest one binds](./08-kv-cache.md#kv-budget-not-guess)**:
  before you call a limit a scheduling problem, compute the budget for
  every resource and see which runs out first. When a budget is full
  there are three moves: smaller items, shared items, less held space.
  *Example: the KV cache caps the batch before compute does.*
- **[8 · Release a resource when its work ends, not when its group ends](./09-the-slot-that-waited.md#iteration-scheduling)**:
  measure occupancy, what you used over what you bought, and schedule at
  the granularity at which work actually finishes.
  *Example: continuous batching evicts a sequence on the step it ends.*
- **[9 · You cannot buy your way out of a waste fraction](./10-a-page-table-for-tokens.md#blocks-not-reservations)**:
  when a resource is mostly reserved and barely used, more of it buys
  the same waste. Allocate what grows unpredictably in fixed blocks
  behind an indirection.
  *Example: paged attention, which is virtual memory from 1962.*
- **[10 · An idle resource is a budget](./12-spending-the-idle.md#spend-below-ridge)**:
  idle capacity does not accrue. Spend the abundant resource freely to
  save the scarce one, even on work you expect to throw away.
  *Example: speculative decoding below the ridge.*

## IV. Believing Your Evidence

- **[11 · A test proves nothing about a layer it cannot reach](./02-the-ladder.md#failure-fidelity)**:
  count the layers a test can touch before you count its runs. Zero
  failures in n runs bounds the failure rate at about 3/n, and only for
  those layers.
  *Example: `kill -9` can never reach the drive's cache.*
- **[12 · Retrying is not recovery when the failure took the copy](./04-write-ahead.md#fsync-terminal)**:
  count the independent copies at every step. When a failure destroys
  what you would retry with, only an earlier, independent copy helps.
  *Example: a failed `fsync` is final; write-ahead logging.*
- **[13 · A check made in the same act as the data fails with it](./06-where-the-truth-stops.md#checksum-the-edge)**:
  verify with arithmetic over the content, and ask what every check does
  on its worst input.
  *Example: checksum every log record, and seed the register nonzero.*

## V. When the Floor Is Wrong

- **[14 · Well above the floor means a participant you did not model](./11-below-the-floor.md#floor-gap-is-cpu)**:
  don't optimize the parts you know. Divide the gap by a count and see
  whether the answer is a believable price for something.
  *Example: kernel launches; and decisions repeated identically can be
  recorded once and replayed.*
