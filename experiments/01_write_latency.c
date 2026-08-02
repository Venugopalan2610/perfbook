/* 01_write_latency - "You write a megabyte. It returns in five
 * microseconds. Where is your data?"
 *
 * Chapter 1 claims a 1 MB write can return faster than any path that
 * could have moved the bytes. This measures four paths that all look
 * like "write a megabyte to a file" and shows they differ by four
 * orders of magnitude.
 *
 * The floor test in the chapter says: if a measurement beats the
 * theoretical floor, the work did not happen. This program prints the
 * floor next to the measurement so you can apply that test yourself.
 */
#include "common.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <errno.h>

#define MB (1024 * 1024)

enum { ITERS = 200, WARMUP = 20 };

static char *make_buffer(size_t n, int aligned)
{
    void *p = NULL;
    if (aligned) {
        /* O_DIRECT needs the buffer, offset and length all aligned to
         * the device's logical block size. 4096 covers every common case. */
        if (posix_memalign(&p, 4096, n) != 0) { perror("posix_memalign"); exit(1); }
    } else {
        p = malloc(n);
        if (!p) { perror("malloc"); exit(1); }
    }
    memset(p, 'x', n);
    return p;
}

/* Path A: stdio. fwrite() into the process's own buffer. This usually
 * doesn't syscall at all for a buffer this size, it just memcpy's. */
static void measure_fwrite(const char *path, uint64_t *out, char *buf)
{
    for (int i = 0; i < WARMUP + ITERS; i++) {
        FILE *f = fopen(path, "w");
        if (!f) { perror("fopen"); exit(1); }
        /* Big stdio buffer so fwrite really does stay in userspace. */
        static char sbuf[2 * MB];
        setvbuf(f, sbuf, _IOFBF, sizeof sbuf);

        uint64_t t0 = now_ns();
        fwrite(buf, 1, MB, f);
        uint64_t t1 = now_ns();

        fclose(f);   /* the real syscall happens here, not above */
        if (i >= WARMUP) out[i - WARMUP] = t1 - t0;
    }
}

/* Path B: write(). Crosses into the kernel, lands in page cache. */
static void measure_write(const char *path, uint64_t *out, char *buf)
{
    for (int i = 0; i < WARMUP + ITERS; i++) {
        int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
        if (fd < 0) { perror("open"); exit(1); }

        uint64_t t0 = now_ns();
        ssize_t n = write(fd, buf, MB);
        uint64_t t1 = now_ns();
        if (n != MB) { perror("write"); exit(1); }

        close(fd);
        if (i >= WARMUP) out[i - WARMUP] = t1 - t0;
    }
}

/* Path C: write() + fsync(). Now the bytes have to reach the media. */
static void measure_write_fsync(const char *path, uint64_t *out, char *buf)
{
    for (int i = 0; i < WARMUP + ITERS; i++) {
        int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
        if (fd < 0) { perror("open"); exit(1); }

        uint64_t t0 = now_ns();
        if (write(fd, buf, MB) != MB) { perror("write"); exit(1); }
        if (fsync(fd) != 0) { perror("fsync"); exit(1); }
        uint64_t t1 = now_ns();

        close(fd);
        if (i >= WARMUP) out[i - WARMUP] = t1 - t0;
    }
}

/* Path D: O_DIRECT. Bypass the page cache entirely. Returns 0 if the
 * filesystem refuses O_DIRECT (tmpfs and some overlayfs setups do). */
static int measure_odirect(const char *path, uint64_t *out, char *buf)
{
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_DIRECT, 0644);
    if (fd < 0) {
        if (errno == EINVAL || errno == ENOTSUP) return 0;
        perror("open O_DIRECT");
        return 0;
    }
    close(fd);

    for (int i = 0; i < WARMUP + ITERS; i++) {
        fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_DIRECT, 0644);
        if (fd < 0) { perror("open O_DIRECT"); exit(1); }

        uint64_t t0 = now_ns();
        ssize_t n = write(fd, buf, MB);
        uint64_t t1 = now_ns();
        if (n != MB) { perror("O_DIRECT write"); close(fd); return 0; }

        close(fd);
        if (i >= WARMUP) out[i - WARMUP] = t1 - t0;
    }
    return 1;
}

int main(void)
{
    const char *dir = scratch_dir();
    char path[1024];
    snprintf(path, sizeof path, "%s/.perfbook_01.tmp", dir);

    printf("\n01 · Where is your megabyte?\n");
    printf("    1 MB written four ways. Same intent, four different answers.\n\n");
    print_environment(dir);

    char *buf   = make_buffer(MB, 0);
    char *abuf  = make_buffer(MB, 1);
    uint64_t *v = malloc(ITERS * sizeof *v);

    printf("measured (lower is not better here, it means less happened)\n");

    measure_fwrite(path, v, buf);
    print_stats("fwrite() to userspace buf", summarize(v, ITERS));

    measure_write(path, v, buf);
    print_stats("write() to page cache", summarize(v, ITERS));

    measure_write_fsync(path, v, buf);
    stats_t fs = summarize(v, ITERS);
    print_stats("write() + fsync() to media", fs);

    if (measure_odirect(path, v, abuf))
        print_stats("O_DIRECT write", summarize(v, ITERS));
    else
        printf("  %-28s unsupported on this filesystem\n", "O_DIRECT write");

    /* The floor test, printed so the reader can apply it. */
    printf("\ntheoretical floors for 1 MB (chapter 1's axioms)\n");
    printf("  %-28s %s\n", "memory copy @ 10 GB/s",  fmt_ns(100000));
    printf("  %-28s %s\n", "NVMe @ 2 GB/s",          fmt_ns(500000));
    printf("  %-28s %s\n", "spinning disk @ 150 MB/s", fmt_ns(6700000));

    printf("\nread it this way\n");
    printf("  Any row far below the memcpy floor did not move a megabyte.\n");
    printf("  It moved a pointer, or queued the work, and returned.\n");
    printf("  The only row that touched the device is the fsync one.\n\n");

    unlink(path);
    free(buf); free(abuf); free(v);
    return 0;
}
