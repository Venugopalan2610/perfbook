/* 03_fsync_cost - "fsync is not a save button. It is a purchase."
 *
 * Chapter 3 claims fsync's cost is dominated by the round trip to the
 * barrier, not by the bytes behind it. That is a falsifiable claim,
 * and this is the falsification test: sync payloads from 8 bytes to
 * 8 MB and see whether the cost tracks the size.
 *
 * If cost were bandwidth-bound, 8 MB would cost a million times more
 * than 8 B. If it is barrier-bound, the small sizes should all cost
 * about the same, and only the large ones should start to climb.
 */
#include "lab.h"
#include <fcntl.h>
#include <errno.h>

enum { ITERS = 60, WARMUP = 10 };

static const size_t SIZES[] = {
    8, 512, 4096, 64 * 1024, 1024 * 1024, 8 * 1024 * 1024
};
#define NSIZES (sizeof SIZES / sizeof SIZES[0])

static const char *human_size(size_t b)
{
    static char s[32];
    if (b < 1024)                snprintf(s, sizeof s, "%zu B", b);
    else if (b < 1024 * 1024)    snprintf(s, sizeof s, "%zu KB", b / 1024);
    else                         snprintf(s, sizeof s, "%zu MB", b / (1024 * 1024));
    return s;
}

int main(void)
{
    const char *dir = scratch_dir();
    char path[1024];
    snprintf(path, sizeof path, "%s/.perfbook_03.tmp", dir);

    lab_begin("03 · What does fsync actually charge you for?",
              "The Barrier",
              "Same call, payloads spanning six orders of magnitude.");
    print_environment(dir);

    char *buf = malloc(SIZES[NSIZES - 1]);
    if (!buf) { perror("malloc"); return 1; }
    memset(buf, 'x', SIZES[NSIZES - 1]);

    uint64_t *v = malloc(ITERS * sizeof *v);
    uint64_t p50_smallest = 0, p50_largest = 0, p50_4k = 0;

    printf("cost of one write() + fsync(), by payload\n");

    for (size_t si = 0; si < NSIZES; si++) {
        size_t sz = SIZES[si];

        for (int i = 0; i < WARMUP + ITERS; i++) {
            int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
            if (fd < 0) { perror("open"); return 1; }

            uint64_t t0 = now_ns();
            if (write(fd, buf, sz) != (ssize_t)sz) { perror("write"); return 1; }
            if (fsync(fd) != 0) { perror("fsync"); return 1; }
            uint64_t t1 = now_ns();

            close(fd);
            if (i >= WARMUP) v[i - WARMUP] = t1 - t0;
        }

        stats_t s = summarize(v, ITERS);
        char label[64];
        snprintf(label, sizeof label, "payload %s", human_size(sz));
        print_stats(label, s);

        if (si == 0)            p50_smallest = s.p50;
        if (sz == 4096)         p50_4k       = s.p50;
        if (si == NSIZES - 1)   p50_largest  = s.p50;
    }

    /* The whole argument, as claims a reader can hold me to. These
     * are ratios on purpose: they survive a change of hardware that
     * absolute latency does not. */
    size_t size_ratio = SIZES[NSIZES - 1] / SIZES[0];
    double cost_ratio = p50_smallest ? (double)p50_largest / (double)p50_smallest : 0.0;
    char obs[64], bound[64];

    printf("\nclaims\n");

    /* 1. Are we measuring storage at all? On tmpfs an fsync is close
     *    to free and every claim below becomes meaningless. */
    snprintf(obs,   sizeof obs,   "%s", fmt_ns(p50_smallest));
    snprintf(bound, sizeof bound, "> 20 µs");
    lab_check("measuring-real-storage",
              "an 8 B fsync costs real time, so this is not tmpfs or a no-op",
              obs, bound, p50_smallest > 20000);

    /* 2. The chapter's actual claim. Payload grew a million fold; if
     *    cost were bandwidth-bound it would have too. A factor of 100
     *    is a deliberately loose bound: the claim is about orders of
     *    magnitude, not a tuned threshold. */
    snprintf(obs,   sizeof obs,   "%.1f× for %zu× data", cost_ratio, size_ratio);
    snprintf(bound, sizeof bound, "< %zu× (100× slack)", size_ratio / 100);
    lab_check("cost-is-not-bandwidth-bound",
              "cost grows far slower than payload: the bytes are not the bill",
              obs, bound, cost_ratio < (double)size_ratio / 100.0);

    /* 3. The small payloads should be nearly indistinguishable from
     *    each other, because they are all paying for the same trip. */
    snprintf(obs,   sizeof obs,   "%s vs %s", fmt_ns(p50_smallest), fmt_ns(p50_4k));
    snprintf(bound, sizeof bound, "within 3×");
    {
        double r = (double)p50_4k / (double)p50_smallest;
        if (r < 1.0) r = 1.0 / r;
        lab_check("small-payloads-cost-the-same",
                  "8 B and 4 KB cost about the same: both buy one barrier",
                  obs, bound, r < 3.0);
    }

    printf("\nfloor test on the 8 B case\n");
    printf("  8 B at 2 GB/s would be           %s\n", fmt_ns(4));
    printf("  you measured (p50)               %s\n", fmt_ns(p50_smallest));
    if (p50_smallest > 4)
        printf("  overhead over the bandwidth floor %.0f×\n", (double)p50_smallest / 4.0);

    printf("\n");
    unlink(path);
    free(buf); free(v);
    return lab_end(dir);
}
