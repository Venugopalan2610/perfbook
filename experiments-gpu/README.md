# GPU labs

Chapters 7 and 8 turn on a ratio between a GPU's compute throughput
and its memory bandwidth. Checking them needs a GPU, and Colab's free
T4 is enough.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Venugopalan2610/perfbook/blob/master/experiments-gpu/colab.ipynb)

Runtime, then Change runtime type, then a GPU. The first cell says so
if you forget.

Locally, with any CUDA card:

```bash
pip install torch
python 07_roofline.py
python 08_kv_cache.py
```

## They measure the hardware, not the datasheet

Vendor peak numbers are marketing, and the ridge point is a division
of two of them. So these labs measure your card's bandwidth with a
large copy, measure its fp16 matmul throughput with a large matmul,
and divide. The ridge you get is yours.

The claims are ratios and shapes, never absolute TFLOPS, because a T4,
an A100 and a laptop card disagree by an order of magnitude on the
numbers and agree exactly on the shape. The shape is the chapter.

## 07_roofline

Measures the ridge, then walks a batch size from 1 to 256 across a
4096x4096 weight matrix, reporting arithmetic intensity and the
fraction of the card's own peak it achieves.

Five claims, all of which hold on any CUDA GPU:

| id | claim |
|---|---|
| `batch1-is-one-flop-per-byte` | at batch 1 the weight matrix dominates the bytes, so intensity is ~1 |
| `batch1-sits-below-the-ridge` | which is at least 10x below the measured ridge |
| `batch1-wastes-the-compute` | so the card delivers under 15% of its own peak |
| `batching-recovers-throughput` | batching recovers at least 5x more TFLOP/s |
| `intensity-tracks-batch-size` | intensity grows roughly linearly with batch |

On the laptop RTX 4080 these were developed against: measured ridge
183 FLOP/byte, batch 1 at 1.0 FLOP/byte and 1.3% of peak, batch 256 at
227 FLOP/byte and effectively saturated. A T4's absolute numbers will
be much lower and the five claims will still hold.

## 08_kv_cache

Chapter 8's 512 KB per token is a multiplication, so this checks it
with an allocator: build a real KV cache and ask CUDA what it cost.

| id | claim |
|---|---|
| `measured-matches-arithmetic` | allocating the cache costs what the multiplication says, within 5% |
| `seven-b-is-512kb-per-token` | a 7B-class config spends exactly 512 KB per token |
| `gqa-divides-by-the-sharing-factor` | 8 query heads per KV head divides the cache by exactly 8 |
| `a100-ceiling-is-about-64` | an 80 GB A100 fits ~61 sequences of 2048 |
| `memory-caps-below-the-ridge` | which is well under the 156 the ridge asked for |

You do not need a card big enough to hold a 7B model. The
bytes-per-token figure is measurable on any GPU, and the ceiling for
larger cards follows from it by division. The lab prints the ceiling
for your card too, which on a 12 GB laptop card is a rather blunt
lesson.

## results.json

Set `PERFBOOK_RESULTS` and both labs append their environment (GPU
name, compute capability, memory, torch and CUDA versions, whether it
detected Colab) and every claim's outcome. That file is what makes two
people's runs comparable.

## Honest limits

- **Colab gives you what it gives you.** The free tier is usually a
  T4 but not always, and a shared or throttled card can miss the
  throughput claims. The GPU name is recorded in every result.
- **`% of peak` above 100 is possible** and means the peak measurement
  did not quite find peak, not that physics broke. The large square
  matmul is a good approximation of peak, not a guarantee of it.
- **These do not run a real model.** They measure the primitive the
  chapters are about, a weight matrix multiplied by an activation, and
  the memory a KV cache actually occupies. Loading a 7B model would
  add a download and a dependency without changing the ratio.
