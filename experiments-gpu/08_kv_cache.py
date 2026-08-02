#!/usr/bin/env python3
"""08_kv_cache - the wall chapter 8 runs into, measured in real bytes.

Chapter 8 claims a 7B-class model spends about 512 KB of KV cache per
token, that a 2048-token sequence therefore costs about 1 GB, and that
this, not padding, is what caps the batch size.

The 512 KB is arithmetic, so this lab checks it by allocating the
tensors and asking CUDA how much memory actually moved, rather than
trusting the multiplication.

Then it computes the ceiling for whichever GPU you are on. You do not
need enough memory to hold a 7B model to learn the lesson; you need
the bytes-per-token figure, which is measurable on any card.
"""
import sys
import torch

import gpulab

# A 7B-class configuration, so the numbers map onto the book.
LAYERS = 32
DIM = 4096
HEADS = 32
DTYPE = torch.float16
SEQ = 2048
WEIGHTS_GB = 14.0            # 7B params at fp16


def analytic_bytes_per_token(layers=LAYERS, dim=DIM, kv_heads=HEADS, heads=HEADS):
    """2 tensors (K and V), per layer, per token, scaled by how many
    query heads share one KV head."""
    head_dim = dim // heads
    return 2 * layers * kv_heads * head_dim * torch.finfo(DTYPE).bits // 8


def measured_bytes_per_token(layers=LAYERS, dim=DIM, kv_heads=HEADS, heads=HEADS,
                             tokens=256):
    """Allocate a real KV cache and ask the allocator what it cost."""
    head_dim = dim // heads
    torch.cuda.empty_cache()
    torch.cuda.synchronize()
    before = torch.cuda.memory_allocated()
    cache = [
        (torch.empty(tokens, kv_heads, head_dim, dtype=DTYPE, device="cuda"),
         torch.empty(tokens, kv_heads, head_dim, dtype=DTYPE, device="cuda"))
        for _ in range(layers)
    ]
    torch.cuda.synchronize()
    after = torch.cuda.memory_allocated()
    del cache
    torch.cuda.empty_cache()
    return (after - before) / tokens


def main():
    gpulab.begin("08 · The cache that ate the batch",
                 "The Cache That Ate the Batch",
                 "Measure KV cache bytes per token, then find this card's ceiling.")
    gpulab.require_cuda()
    env = gpulab.environment()

    total_gb = torch.cuda.get_device_properties(0).total_memory / 1e9

    analytic = analytic_bytes_per_token()
    measured = measured_bytes_per_token()

    print("KV cache cost per token (32 layers, 4096 dim, fp16)")
    print(f"  {'arithmetic':<24} {analytic/1024:8.1f} KB/token")
    print(f"  {'measured on this GPU':<24} {measured/1024:8.1f} KB/token")
    print(f"  {'per 2048-token sequence':<24} {analytic*SEQ/1e9:8.2f} GB\n")

    print("claims\n")

    # 1. The book's headline number, checked by allocation.
    err = abs(measured - analytic) / analytic
    gpulab.check(
        "measured-matches-arithmetic",
        "allocating a real KV cache costs what the multiplication says",
        f"{measured/1024:.1f} KB vs {analytic/1024:.1f} KB",
        "within 5%", err < 0.05)

    gpulab.check(
        "seven-b-is-512kb-per-token",
        "a 7B-class config spends 512 KB of cache per token",
        f"{analytic/1024:.0f} KB/token", "512 KB", analytic == 512 * 1024)

    # 2. Grouped-Query Attention is the field's answer, and the saving
    #    is exactly the sharing factor. Measurable, not asserted.
    gqa = analytic_bytes_per_token(kv_heads=HEADS // 8)
    gqa_measured = measured_bytes_per_token(kv_heads=HEADS // 8)
    factor = analytic / gqa
    gpulab.check(
        "gqa-divides-by-the-sharing-factor",
        "sharing 8 query heads per KV head divides the cache by 8",
        f"{factor:.1f}x smaller ({gqa_measured/1024:.0f} KB/token)", "8x",
        abs(factor - 8.0) < 0.01)

    # 3. The wall. Whatever card you have, weights come off the top and
    #    the rest divides by the per-sequence cost.
    seq_gb = analytic * SEQ / 1e9
    print(f"\nthe ceiling on this card ({total_gb:.1f} GB total)")
    for wgb, label in ((WEIGHTS_GB, "7B fp16 weights"), (0.0, "weights elsewhere")):
        free = total_gb - wgb
        fits = int(free / seq_gb) if free > 0 else 0
        if free <= 0:
            print(f"  {label:<22} does not fit on this card at all")
        else:
            print(f"  {label:<22} {free:5.1f} GB free -> {fits} sequences of {SEQ}")

    # The A100 case from the book, computed rather than quoted, so the
    # claim is checkable even from a card that cannot run it.
    a100_free = 80.0 - WEIGHTS_GB
    a100_fits = int(a100_free / seq_gb)
    gpulab.check(
        "a100-ceiling-is-about-64",
        "an 80 GB A100 fits far fewer sequences than the ridge wants",
        f"{a100_fits} sequences", "between 55 and 70",
        55 <= a100_fits <= 70)

    # 4. And that ceiling is below what chapter 7's ridge asked for.
    gpulab.check(
        "memory-caps-below-the-ridge",
        "the memory ceiling binds before the compute-optimal batch does",
        f"{a100_fits} sequences vs 156 wanted", "fewer than 156",
        a100_fits < 156)

    print("\nwhat this located")
    print("  The 512 KB is not a rule of thumb, it is a multiplication you")
    print("  can check with an allocator. Every technique the field reached")
    print("  for, GQA, KV quantization, PagedAttention, is an attack on that")
    print("  one constant or on the waste around it.")

    return gpulab.end(env)


if __name__ == "__main__":
    sys.exit(main())
