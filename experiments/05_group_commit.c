/* 05_group_commit - a fixed batch size is a bet on a load level.
 *
 * Chapter 5 claims a fixed-count batch collapses at low load, because
 * the ack waits for the counter rather than for the disk, and that
 * closing the batch when the in-flight fsync returns fixes it without
 * anyone naming a number.
 *
 * Two real committer policies, a real producer thread arriving at a
 * controlled rate, and real fsyncs. We measure the latency each
 * record actually experienced: submit to ack.
 *
 * The book's example is 1000 records at 10/sec, which would take 100
 * seconds to fill one batch. We use a smaller N and a faster arrival
 * rate so the lab finishes in seconds. The ratio is the claim; the
 * absolute wait just scales with the constants you pick.
 */
#include "lab.h"
#include <fcntl.h>
#include <pthread.h>
#include <errno.h>

enum {
    FIXED_N     = 64,      /* the hardcoded batch size, the bug       */
    RECORDS     = 256,     /* records per run                         */
    SLOW_US     = 2000,    /* quiet night: slower than one fsync      */
    FAST_US     = 50,      /* busy hour:   faster than one fsync      */
    RECORD_SIZE = 128,
};

typedef struct {
    uint64_t submitted_ns;
    uint64_t acked_ns;
} record_t;

typedef struct {
    record_t  recs[RECORDS];
    int       produced;      /* how many have been submitted   */
    int       acked;         /* how many have been acked       */
    int       done;          /* producer has finished          */
    int       adaptive;      /* policy selector                */
    int       arrival_us;    /* inter-arrival gap              */
    int       fd;
    int       batches;       /* how many fsyncs we performed   */
    pthread_mutex_t m;
    pthread_cond_t  cv;
} queue_t;

static void *producer(void *arg)
{
    queue_t *q = arg;
    for (int i = 0; i < RECORDS; i++) {
        pthread_mutex_lock(&q->m);
        q->recs[i].submitted_ns = now_ns();
        q->produced = i + 1;
        pthread_cond_signal(&q->cv);
        pthread_mutex_unlock(&q->m);
        usleep(q->arrival_us);
    }
    pthread_mutex_lock(&q->m);
    q->done = 1;
    pthread_cond_broadcast(&q->cv);
    pthread_mutex_unlock(&q->m);
    return NULL;
}

/* Write and sync records [from, upto), WITHOUT holding the queue lock.
 *
 * Dropping the lock here is the whole mechanism, not an optimization.
 * The chapter's rule is "sweep in everyone who arrived while the last
 * fsync was in flight", and nobody can arrive while in flight if the
 * committer is holding the lock the producer needs. An earlier version
 * of this lab held it across the fsync and the batch size never rose
 * above 1.0 at any load, which is what a serialized queue looks like.
 */
static void commit_range(queue_t *q, int from, int upto)
{
    char buf[RECORD_SIZE];
    memset(buf, 'x', sizeof buf);
    for (int i = from; i < upto; i++)
        if (write(q->fd, buf, sizeof buf) != (ssize_t)sizeof buf) { perror("write"); exit(2); }
    if (fsync(q->fd) != 0) { perror("fsync"); exit(2); }
}

static void *committer(void *arg)
{
    queue_t *q = arg;
    for (;;) {
        pthread_mutex_lock(&q->m);

        if (q->adaptive) {
            /* Anything outstanding at all is enough. */
            while (q->produced == q->acked && !q->done)
                pthread_cond_wait(&q->cv, &q->m);
        } else {
            /* Wait for the counter, however long that takes. */
            while (q->produced - q->acked < FIXED_N && !q->done)
                pthread_cond_wait(&q->cv, &q->m);
        }

        if (q->acked == q->produced && q->done) { pthread_mutex_unlock(&q->m); break; }

        int from = q->acked;
        int upto = q->produced;
        if (!q->adaptive && upto - from > FIXED_N) upto = from + FIXED_N;
        pthread_mutex_unlock(&q->m);

        /* Lock released: the producer keeps arriving during this. */
        commit_range(q, from, upto);

        pthread_mutex_lock(&q->m);
        uint64_t t = now_ns();
        for (int i = from; i < upto; i++) q->recs[i].acked_ns = t;
        q->acked = upto;
        q->batches++;
        pthread_mutex_unlock(&q->m);
    }
    return NULL;
}

typedef struct { uint64_t p50, p99; int batches; double avg_batch; } result_t;

static result_t run(const char *path, int adaptive, int arrival_us)
{
    queue_t q;
    memset(&q, 0, sizeof q);
    q.adaptive = adaptive;
    q.arrival_us = arrival_us;
    pthread_mutex_init(&q.m, NULL);
    pthread_cond_init(&q.cv, NULL);

    q.fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (q.fd < 0) { perror("open"); exit(2); }

    pthread_t p, c;
    pthread_create(&c, NULL, committer, &q);
    pthread_create(&p, NULL, producer, &q);
    pthread_join(p, NULL);
    pthread_join(c, NULL);
    close(q.fd);

    uint64_t *lat = malloc(RECORDS * sizeof *lat);
    for (int i = 0; i < RECORDS; i++)
        lat[i] = q.recs[i].acked_ns - q.recs[i].submitted_ns;
    stats_t s = summarize(lat, RECORDS);
    free(lat);

    result_t r = { s.p50, s.p99, q.batches,
                   q.batches ? (double)RECORDS / q.batches : 0.0 };
    return r;
}

int main(void)
{
    const char *dir = scratch_dir();
    char path[1024], obs[64], bound[64];
    snprintf(path, sizeof path, "%s/.perfbook_05.tmp", dir);

    lab_begin("05 · A constant is a bet on a load level",
              "Group Commit",
              "Fixed-count vs adaptive batching, same arrival rate, real fsyncs.");
    print_environment(dir);

    printf("two arrival rates, same code, nothing tuned between them\n\n");

    result_t slow_fixed = run(path, 0, SLOW_US);
    result_t slow_adapt = run(path, 1, SLOW_US);
    result_t fast_fixed = run(path, 0, FAST_US);
    result_t fast_adapt = run(path, 1, FAST_US);

    printf("quiet night: one record every %d µs (%.0f/sec)\n", SLOW_US, 1e6 / SLOW_US);
    printf("  %-18s p50 ack %-12s %3d fsyncs, avg batch %.1f\n",
           "fixed count", fmt_ns(slow_fixed.p50), slow_fixed.batches, slow_fixed.avg_batch);
    printf("  %-18s p50 ack %-12s %3d fsyncs, avg batch %.1f\n",
           "adaptive", fmt_ns(slow_adapt.p50), slow_adapt.batches, slow_adapt.avg_batch);

    printf("\nbusy hour: one record every %d µs (%.0f/sec)\n", FAST_US, 1e6 / FAST_US);
    printf("  %-18s p50 ack %-12s %3d fsyncs, avg batch %.1f\n",
           "fixed count", fmt_ns(fast_fixed.p50), fast_fixed.batches, fast_fixed.avg_batch);
    printf("  %-18s p50 ack %-12s %3d fsyncs, avg batch %.1f\n",
           "adaptive", fmt_ns(fast_adapt.p50), fast_adapt.batches, fast_adapt.avg_batch);

    printf("\nclaims\n");

    /* 1. The headline: at low load the counter, not the disk, is what
     *    the fixed policy makes everyone wait for. */
    double ratio = slow_adapt.p50 ? (double)slow_fixed.p50 / (double)slow_adapt.p50 : 0.0;
    snprintf(obs,   sizeof obs,   "%.0fx worse at low load", ratio);
    snprintf(bound, sizeof bound, "at least 5x");
    lab_check("fixed-count-collapses-at-low-load",
              "the fixed batch acks far later because it waits on a counter",
              obs, bound, ratio >= 5.0);

    /* 2. Adaptive pays for the disk and essentially nothing else. */
    snprintf(obs,   sizeof obs,   "%s", fmt_ns(slow_adapt.p50));
    snprintf(bound, sizeof bound, "under one arrival gap (%d µs)", SLOW_US);
    lab_check("adaptive-pays-only-the-barrier",
              "adaptive acks inside one arrival gap: it never waits for a quorum",
              obs, bound, slow_adapt.p50 < (uint64_t)SLOW_US * 1000);

    /* 3. The self-tuning half. Same code, faster arrivals, and the
     *    batch size grows on its own because more people are queued
     *    behind each flush. Nobody set a number. */
    snprintf(obs,   sizeof obs,   "%.1f at low load -> %.1f at high",
             slow_adapt.avg_batch, fast_adapt.avg_batch);
    snprintf(bound, sizeof bound, "grows by at least 3x, untuned");
    lab_check("adaptive-self-tunes-with-load",
              "the batch size follows the arrival rate with no constant to set",
              obs, bound, fast_adapt.avg_batch >= slow_adapt.avg_batch * 3.0);

    /* 4. And it does that without giving the latency back. */
    snprintf(obs,   sizeof obs,   "%s vs fixed %s",
             fmt_ns(fast_adapt.p50), "see table");
    snprintf(bound, sizeof bound, "no worse than fixed at high load");
    lab_check("adaptive-never-loses",
              "amortizing more did not cost latency, even where fixed looks fine",
              obs, bound, fast_adapt.p50 <= fast_fixed.p50);

    printf("\nwhat this located\n");
    printf("  Nobody tuned anything between those two runs. The adaptive\n");
    printf("  policy has no batch size in it at all, and its batch size\n");
    printf("  still tracked the load, because the disk was setting it.\n");
    printf("\n");
    printf("  Notice the fixed policy looks fine in the busy hour. It was\n");
    printf("  never wrong exactly. It was only ever right about one\n");
    printf("  Tuesday, and nothing in it notices when Tuesday ends.\n");

    unlink(path);
    return lab_end(dir);
}
