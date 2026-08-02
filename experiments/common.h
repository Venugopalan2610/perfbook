/* common.h - measurement plumbing shared by every experiment.
 *
 * Three jobs, all of them about not lying to yourself:
 *
 *   1. Time things with a clock that doesn't jump (CLOCK_MONOTONIC).
 *   2. Report percentiles, never the mean. A mean latency hides the
 *      tail, and the tail is usually the thing you care about.
 *   3. Print the environment alongside the numbers. A latency figure
 *      without its kernel, filesystem, device and virtualization
 *      status is not a result, it's an anecdote.
 */
#ifndef COMMON_H
#define COMMON_H

#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

/* This is a grab-bag header; no single experiment uses all of it. */
#ifdef __GNUC__
#  define MAYBE_UNUSED __attribute__((unused))
#else
#  define MAYBE_UNUSED
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <unistd.h>

/* ---------- timing ---------- */

static inline uint64_t now_ns(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
}

/* Cost of reading the clock, so we can say whether a measurement is
 * even resolvable. If your result is the same order as this, the
 * result is the instrument, not the system. */
static inline uint64_t clock_overhead_ns(void)
{
    enum { N = 10000 };
    uint64_t best = UINT64_MAX;
    for (int i = 0; i < N; i++) {
        uint64_t a = now_ns();
        uint64_t b = now_ns();
        if (b - a < best) best = b - a;
    }
    return best;
}

/* ---------- statistics ---------- */

static int cmp_u64(const void *a, const void *b)
{
    uint64_t x = *(const uint64_t *)a, y = *(const uint64_t *)b;
    return (x > y) - (x < y);
}

typedef struct {
    uint64_t min, p50, p95, p99, max;
    size_t n;
} stats_t;

/* Sorts `v` in place. */
MAYBE_UNUSED static stats_t summarize(uint64_t *v, size_t n)
{
    stats_t s = {0};
    if (n == 0) return s;
    qsort(v, n, sizeof v[0], cmp_u64);
    s.n = n;
    s.min = v[0];
    s.max = v[n - 1];
    s.p50 = v[(size_t)(n * 0.50)];
    s.p95 = v[n > 20 ? (size_t)(n * 0.95) : n - 1];
    s.p99 = v[n > 100 ? (size_t)(n * 0.99) : n - 1];
    return s;
}

/* Human-readable duration. Returns a pointer to a static buffer, so
 * don't call it twice in one printf. */
MAYBE_UNUSED static const char *fmt_ns(uint64_t ns)
{
    static char buf[32];
    if (ns < 1000ull)              snprintf(buf, sizeof buf, "%llu ns", (unsigned long long)ns);
    else if (ns < 1000000ull)      snprintf(buf, sizeof buf, "%.2f µs", ns / 1e3);
    else if (ns < 1000000000ull)   snprintf(buf, sizeof buf, "%.2f ms", ns / 1e6);
    else                           snprintf(buf, sizeof buf, "%.2f s",  ns / 1e9);
    return buf;
}

MAYBE_UNUSED static void print_stats(const char *label, stats_t s)
{
    char p50[32], p95[32], p99[32], mn[32];
    snprintf(mn,  sizeof mn,  "%s", fmt_ns(s.min));
    snprintf(p50, sizeof p50, "%s", fmt_ns(s.p50));
    snprintf(p95, sizeof p95, "%s", fmt_ns(s.p95));
    snprintf(p99, sizeof p99, "%s", fmt_ns(s.p99));
    printf("  %-28s min %-10s p50 %-10s p95 %-10s p99 %-10s (n=%zu)\n",
           label, mn, p50, p95, p99, s.n);
}

/* ---------- environment reporting ---------- */

MAYBE_UNUSED static void run_quiet(const char *cmd, char *out, size_t outsz)
{
    out[0] = '\0';
    FILE *f = popen(cmd, "r");
    if (!f) return;
    if (fgets(out, (int)outsz, f)) {
        size_t l = strlen(out);
        while (l && (out[l-1] == '\n' || out[l-1] == ' ')) out[--l] = '\0';
    }
    pclose(f);
}

/* Print everything a reader needs to compare their numbers to someone
 * else's. Without this block the numbers below are not reproducible. */
MAYBE_UNUSED static void print_environment(const char *target_dir)
{
    char buf[512], cmd[1024];

    printf("environment\n");

    run_quiet("uname -sr", buf, sizeof buf);
    printf("  %-18s %s\n", "kernel", buf[0] ? buf : "?");

    snprintf(cmd, sizeof cmd,
             "findmnt -no FSTYPE,SOURCE,OPTIONS --target '%s' 2>/dev/null", target_dir);
    run_quiet(cmd, buf, sizeof buf);
    printf("  %-18s %s\n", "filesystem", buf[0] ? buf : "?");

    snprintf(cmd, sizeof cmd,
             "findmnt -no SOURCE --target '%s' 2>/dev/null "
             "| xargs -r lsblk -no PKNAME 2>/dev/null | head -1", target_dir);
    char dev[48];                     /* a kernel device name is short */
    run_quiet(cmd, dev, sizeof dev);
    if (dev[0]) {
        char model[256], cmd2[512], rot[16];
        snprintf(cmd2, sizeof cmd2, "cat /sys/block/%s/device/model 2>/dev/null", dev);
        run_quiet(cmd2, model, sizeof model);
        printf("  %-18s %s %s\n", "device", dev, model);

        snprintf(cmd2, sizeof cmd2, "cat /sys/block/%s/queue/rotational 2>/dev/null", dev);
        run_quiet(cmd2, rot, sizeof rot);
        printf("  %-18s %s\n", "rotational",
               rot[0] == '1' ? "yes (spinning disk)" :
               rot[0] == '0' ? "no (solid state)" : "?");
    }

    run_quiet("systemd-detect-virt 2>/dev/null || echo unknown", buf, sizeof buf);
    printf("  %-18s %s\n", "virtualization", buf[0] ? buf : "unknown");
    if (buf[0] && strcmp(buf, "none") != 0 && strcmp(buf, "unknown") != 0)
        printf("  %-18s fsync here may reflect the hypervisor, not a device\n", "  ^ note");

    printf("  %-18s %s\n", "clock overhead", fmt_ns(clock_overhead_ns()));
    printf("\n");
}

/* Where to put test files. Readers can point this at a specific device.
 * Defaults to the current directory so results describe the filesystem
 * the reader actually cares about. */
MAYBE_UNUSED static const char *scratch_dir(void)
{
    const char *d = getenv("PERFBOOK_DIR");
    return (d && *d) ? d : ".";
}

#endif /* COMMON_H */
