/* 01_write_latency - "You write four kilobytes. It says success in a few
 * microseconds. Where is your data?"
 *
 * The chapter "Success, Too Soon" claims a small write() returns long
 * before any drive could have answered. This measures four paths that all
 * look like "write 4 KB to a file" and prints them next to the floors, so
 * you can apply the floor test yourself.
 *
 * The floor test: if a measurement beats the fastest the work could
 * possibly go, the work did not happen. A row far below the drive's round
 * trip never reached the drive.
 *
 * Every path opens its file once and appends, the way a log does. Opening
 * and truncating the file on every iteration would time the filesystem's
 * allocator and its truncate heuristics instead of the write.
 */
#include "common.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <errno.h>

#define BLOCK 4096

enum { ITERS = 1000, WARMUP = 50 };

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

static int open_or_die(const char *path, int extra)
{
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | extra, 0644);
    if (fd < 0) { perror("open"); exit(1); }
    return fd;
}

/* Path A: stdio with a buffer you asked for. fwrite() copies into the
 * process's own memory and makes no syscall until the buffer fills. */
static void measure_fwrite(const char *path, uint64_t *out, char *buf)
{
    static char sbuf[64 * BLOCK];
    FILE *f = fopen(path, "w");
    if (!f) { perror("fopen"); exit(1); }
    setvbuf(f, sbuf, _IOFBF, sizeof sbuf);

    for (int i = 0; i < WARMUP + ITERS; i++) {
        uint64_t t0 = now_ns();
        fwrite(buf, 1, BLOCK, f);
        uint64_t t1 = now_ns();
        if (i >= WARMUP) out[i - WARMUP] = t1 - t0;
    }
    fclose(f);   /* the syscalls happen here and on every 64th write */
}

/* Path B: write(). Crosses into the kernel, lands in the page cache. */
static void measure_write(const char *path, uint64_t *out, char *buf)
{
    int fd = open_or_die(path, 0);
    for (int i = 0; i < WARMUP + ITERS; i++) {
        uint64_t t0 = now_ns();
        ssize_t n = write(fd, buf, BLOCK);
        uint64_t t1 = now_ns();
        if (n != BLOCK) { perror("write"); exit(1); }
        if (i >= WARMUP) out[i - WARMUP] = t1 - t0;
    }
    close(fd);
}

/* Path C: write() + fsync(). Now the bytes have to reach the media. */
static void measure_write_fsync(const char *path, uint64_t *out, char *buf)
{
    int fd = open_or_die(path, 0);
    for (int i = 0; i < WARMUP + ITERS; i++) {
        uint64_t t0 = now_ns();
        if (write(fd, buf, BLOCK) != BLOCK) { perror("write"); exit(1); }
        if (fsync(fd) != 0) { perror("fsync"); exit(1); }
        uint64_t t1 = now_ns();
        if (i >= WARMUP) out[i - WARMUP] = t1 - t0;
    }
    close(fd);
}

/* Path D: O_DIRECT. Skips the page cache and goes to the drive, which may
 * still hold it in its own volatile cache. Returns 0 if the filesystem
 * refuses O_DIRECT (tmpfs and some overlayfs setups do). */
static int measure_odirect(const char *path, uint64_t *out, char *buf)
{
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_DIRECT, 0644);
    if (fd < 0) return 0;

    for (int i = 0; i < WARMUP + ITERS; i++) {
        uint64_t t0 = now_ns();
        ssize_t n = write(fd, buf, BLOCK);
        uint64_t t1 = now_ns();
        if (n != BLOCK) { close(fd); return 0; }
        if (i >= WARMUP) out[i - WARMUP] = t1 - t0;
    }
    close(fd);
    return 1;
}

int main(void)
{
    const char *dir = scratch_dir();
    char path[1024];
    snprintf(path, sizeof path, "%s/.perfbook_01.tmp", dir);

    printf("\n01 · Success, too soon\n");
    printf("    4 KB written four ways. Same intent, four different answers.\n\n");
    print_environment(dir);

    char *buf   = make_buffer(BLOCK, 0);
    char *abuf  = make_buffer(BLOCK, 1);
    uint64_t *v = malloc(ITERS * sizeof *v);

    printf("measured (lower is not better here, it means less happened)\n");

    measure_fwrite(path, v, buf);
    print_stats("fwrite() to userspace buf", summarize(v, ITERS));

    measure_write(path, v, buf);
    print_stats("write() to page cache", summarize(v, ITERS));

    if (measure_odirect(path, v, abuf))
        print_stats("O_DIRECT write to drive", summarize(v, ITERS));
    else
        printf("  %-28s unsupported on this filesystem\n", "O_DIRECT write to drive");

    measure_write_fsync(path, v, buf);
    print_stats("write() + fsync() to media", summarize(v, ITERS));

    /* The floor test, printed so the reader can apply it. */
    printf("\nfloors for 4 KB on the reference machine (chapter 1's axioms)\n");
    printf("  %-28s %s\n", "empty system call",          fmt_ns(100));
    printf("  %-28s %s\n", "round trip to the drive",    fmt_ns(20000));
    printf("  %-28s %s\n", "durable: trip and a flush",  fmt_ns(100000));

    printf("\nread it this way\n");
    printf("  A row far below the durable trip is not durable, whatever it said.\n");
    printf("  A row below the drive's round trip never reached the drive.\n");
    printf("  Nothing that enters the kernel can beat an empty system call.\n");
    printf("  Only the fsync row asked the drive to make the bytes durable.\n\n");

    unlink(path);
    free(buf); free(abuf); free(v);
    return 0;
}
