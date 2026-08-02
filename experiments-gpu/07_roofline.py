#!/usr/bin/env python3
"""07_roofline - measure the ridge, then watch a batch size walk toward it.

Chapter 7 claims that generating one token from a 7B model at batch 1
has an arithmetic intensity of about 1 FLOP per byte, that an A100's
ridge point is around 156, and that the gap is why the GPU sits idle.

Two of those three are properties of the hardware, so this lab does
not trust the datasheet for them. It measures the bandwidth and the
compute throughput of whatever card you actually have and divides.

The claims below are ratios and shapes, never absolute TFLOPS. A T4,
an A100 and a laptop 4080 disagree by an order of magnitude on the
numbers and agree exactly on the shape, and the shape is the chapter.
"""
import sys
import torch

import gpulab

# A 7B-class hidden dimension, so the arithmetic maps onto the book.
DIM = 4096
BATCHES = [1, 2, 4, 8, 16, 32, 64, 128, 256]


def measure_bandwidth_gbs():
    """Large device-to-device copy. Counts read + write."""
    n = 256 * 1024 * 1024 // 2          # 256 MB of fp16
    src = torch.empty(n, dtype=torch.float16, device="cuda").fill_(1.0)
    dst = torch.empty_like(src)
    secs = gpulab.time_cuda(lambda: dst.copy_(src))
    moved = src.numel() * src.element_size() * 2      # read + write
    del src, dst
    torch.cuda.empty_cache()
    return moved / secs / 1e9


def measure_peak_tflops():
    """Big square fp16 matmul: the most compute-dense thing available."""
    n = 8192
    a = torch.randn(n, n, dtype=torch.float16, device="cuda")
    b = torch.randn(n, n, dtype=torch.float16, device="cuda")
    secs = gpulab.time_cuda(lambda: torch.mm(a, b), warmup=3, iters=10)
    flops = 2.0 * n * n * n
    del a, b
    torch.cuda.empty_cache()
    return flops / secs / 1e12


def sweep(dim):
    """(batch, dim) @ (dim, dim): a decode step at batch 1, a prefill
    style matmul at large batch. Returns rows of measurements."""
    w = torch.randn(dim, dim, dtype=torch.float16, device="cuda")
    rows = []
    for m in BATCHES:
        x = torch.randn(m, dim, dtype=torch.float16, device="cuda")
        secs = gpulab.time_cuda(lambda: torch.mm(x, w))
        flops = 2.0 * m * dim * dim
        # Read the activations and the weights, write the result.
        bytes_moved = (m * dim + dim * dim + m * dim) * 2
        rows.append({
            "batch": m,
            "ai": flops / bytes_moved,
            "tflops": flops / secs / 1e12,
            "us": secs * 1e6,
        })
        del x
    del w
    torch.cuda.empty_cache()
    return rows


def main():
    gpulab.begin("07 · The Ridge, measured",
                 "The Ridge",
                 "Measure this GPU's ridge point, then walk a batch size toward it.")
    gpulab.require_cuda()
    env = gpulab.environment()

    bw = measure_bandwidth_gbs()
    peak = measure_peak_tflops()
    ridge = peak * 1e12 / (bw * 1e9)

    print("measured hardware constants (not from a datasheet)")
    print(f"  {'memory bandwidth':<24} {bw:8.1f} GB/s")
    print(f"  {'peak fp16 matmul':<24} {peak:8.1f} TFLOP/s")
    print(f"  {'ridge point':<24} {ridge:8.1f} FLOP/byte")
    print("\n  The book quotes ~156 FLOP/byte for an A100. Yours will differ,")
    print("  and the number itself is not the lesson. Where your workload")
    print("  sits relative to it is.\n")

    rows = sweep(DIM)
    print(f"decode step, {DIM}x{DIM} weights, by batch size")
    print(f"  {'batch':>6} {'FLOP/byte':>11} {'TFLOP/s':>10} {'% of peak':>10} {'µs':>9}")
    for r in rows:
        print(f"  {r['batch']:>6} {r['ai']:>11.1f} {r['tflops']:>10.1f} "
              f"{100 * r['tflops'] / peak:>9.1f}% {r['us']:>9.1f}")

    b1 = rows[0]
    bmax = rows[-1]

    print("\nclaims\n")

    # 1. Structural: at batch 1 the weight matrix dominates the bytes,
    #    so intensity lands near 1 FLOP/byte on ANY card.
    gpulab.check(
        "batch1-is-one-flop-per-byte",
        "at batch 1 you read a whole weight matrix to do one row of math",
        f"{b1['ai']:.2f} FLOP/byte", "between 0.5 and 3",
        0.5 <= b1["ai"] <= 3.0)

    # 2. Which puts it far below this card's ridge, whatever that is.
    gpulab.check(
        "batch1-sits-below-the-ridge",
        "so batch 1 is memory-bound: intensity is orders below the ridge",
        f"{b1['ai']:.2f} vs ridge {ridge:.0f}", "at least 10x below",
        b1["ai"] * 10 < ridge)

    # 3. And the consequence chapter 7 cares about: the compute units
    #    are idle. This is the "99.4% idle" claim, as a ratio.
    pct = 100 * b1["tflops"] / peak
    gpulab.check(
        "batch1-wastes-the-compute",
        "the GPU delivers a small fraction of its own peak at batch 1",
        f"{pct:.1f}% of peak", "under 15%",
        pct < 15.0)

    # 4. Batching is the fix, and it is the same amortization trick as
    #    group commit: one weight read, many rows of math.
    gain = bmax["tflops"] / b1["tflops"]
    gpulab.check(
        "batching-recovers-throughput",
        "batching amortizes the weight read across many tokens",
        f"{gain:.1f}x more TFLOP/s at batch {bmax['batch']}", "at least 5x",
        gain >= 5.0)

    # 5. And intensity tracks batch size, which is why it works.
    ratio = bmax["ai"] / b1["ai"]
    gpulab.check(
        "intensity-tracks-batch-size",
        "arithmetic intensity grows roughly linearly with batch",
        f"{ratio:.0f}x for {bmax['batch']}x batch", "within 2x of linear",
        bmax["batch"] / 2 <= ratio <= bmax["batch"] * 2)

    print("\nwhat this located")
    print("  The ridge is a property of the silicon, and you just measured")
    print("  yours instead of quoting mine. Batch 1 sits far to the left of")
    print("  it on every card ever built, because reading a weight matrix to")
    print("  compute one row is the same bad trade everywhere.")

    return gpulab.end(env)


if __name__ == "__main__":
    sys.exit(main())
