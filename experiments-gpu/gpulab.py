"""gpulab.py - the check framework, same idea as the C labs' lab.h.

A benchmark prints a number. A lab states a claim and checks it.

The claims here are ratios and structural facts, never absolute
TFLOPS, because a T4, an A100 and a laptop 4080 will disagree wildly
on absolute numbers while agreeing exactly on the shape of the curve.
That shape is what chapters 7 and 8 are actually about.

Nothing in here is specific to one GPU. If it only worked on the card
I happened to have, it would not be a lab.
"""
import json
import os
import sys
import time

_checks = []
_lab = {"name": "", "chapter": ""}


def begin(name, chapter, subtitle):
    _lab["name"] = name
    _lab["chapter"] = chapter
    print(f"\n{name}")
    print(f"    {subtitle}")
    print(f"    chapter: {chapter}\n")


def check(cid, claim, observed, bound, passed):
    _checks.append({
        "id": cid, "claim": claim,
        "observed": str(observed), "expected": str(bound),
        "pass": bool(passed),
    })
    print(f"  [{'PASS' if passed else 'FAIL'}] {cid:<38} {claim}")
    print(f"         observed {str(observed):<24} expected {bound}")


def environment():
    """Everything a reader needs to compare their run to someone else's."""
    import torch
    env = {
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
    }
    if torch.cuda.is_available():
        i = torch.cuda.current_device()
        p = torch.cuda.get_device_properties(i)
        env.update({
            "gpu": p.name,
            "compute_capability": f"{p.major}.{p.minor}",
            "total_memory_gb": round(p.total_memory / 1e9, 2),
            "multiprocessors": p.multi_processor_count,
            "cuda": torch.version.cuda,
        })
    env["colab"] = "COLAB_GPU" in os.environ or "COLAB_RELEASE_TAG" in os.environ

    print("environment")
    for k, v in env.items():
        print(f"  {k:<20} {v}")
    print()
    return env


def time_cuda(fn, warmup=5, iters=20):
    """Median seconds per call. CUDA is asynchronous, so every timing
    needs an explicit synchronize or you are timing the launch, not
    the work."""
    import torch
    for _ in range(warmup):
        fn()
    torch.cuda.synchronize()
    samples = []
    for _ in range(iters):
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        fn()
        torch.cuda.synchronize()
        samples.append(time.perf_counter() - t0)
    samples.sort()
    return samples[len(samples) // 2]


def end(env):
    failed = sum(1 for c in _checks if not c["pass"])
    print(f"\n  {len(_checks)} checks, {len(_checks) - failed} passed, {failed} failed")
    if failed:
        print("  A failure here is usually the environment, not the book.")
        print("  A shared or throttled GPU will miss the throughput claims.")
    print()

    out = os.environ.get("PERFBOOK_RESULTS")
    if out:
        with open(out, "a") as f:
            f.write(json.dumps({
                "lab": _lab["name"],
                "chapter": _lab["chapter"],
                "environment": env,
                "checks": _checks,
                "failed": failed,
            }, indent=2) + "\n")
        print(f"  appended to {out}\n")
    return 1 if failed else 0


def require_cuda():
    import torch
    if not torch.cuda.is_available():
        print("No CUDA device visible.\n")
        print("On Colab: Runtime > Change runtime type > T4 GPU, then rerun.")
        print("These labs measure a GPU's memory bandwidth against its")
        print("compute throughput, so there is nothing to measure without one.")
        sys.exit(2)
