/* 01_constants - the band in chapter 1, section 1.5.
 *
 * Chapter 1 places twenty-five microseconds between two floors: a bare
 * function call below it, a DRAM-bandwidth copy of a megabyte above it.
 * It also claims that a megabyte copied into a buffer that is already
 * hot in the CPU cache moves several times faster than one copied into
 * main memory. This prints all four numbers for your machine.
 *
 * Every copy is followed by a compiler barrier on its destination. Without
 * it, the compiler sees that nothing reads the copy, deletes it, and this
 * program reports a megabyte moved in zero time: the floor test from the
 * same chapter, failing on the program that was meant to illustrate it.
 */
#include "common.h"
#include <sys/syscall.h>

#define MB (1024 * 1024)

enum { CALLS = 2000000, SYSCALLS = 200000, COPIES = 201 };

__attribute__((noinline)) static int bump(int x)
{
    __asm__ volatile("");
    return x + 1;
}

/* Median ns to copy 1 MB from src into the destination that pick() names. */
static uint64_t median_copy_ns(const char *src, char *(*pick)(int, void *), void *ctx)
{
    static uint64_t t[COPIES];
    for (int i = 0; i < COPIES; i++) {
        char *dst = pick(i, ctx);
        uint64_t t0 = now_ns();
        memcpy(dst, src, MB);
        __asm__ volatile("" :: "r"(dst) : "memory");
        t[i] = now_ns() - t0;
    }
    qsort(t, COPIES, sizeof t[0], cmp_u64);
    return t[COPIES / 2];
}

/* Hot: the same 1 MB destination every time, so it stays in L2/L3. */
static char *pick_hot(int i, void *ctx) { (void)i; return ctx; }

/* Cold: walk a 1 GB arena, far larger than any cache, so the
 * destination is never already cached. */
static char *pick_cold(int i, void *ctx)
{
    const size_t arena = 1UL << 30;
    return (char *)ctx + ((size_t)i * 3 * MB) % (arena - MB);
}

int main(void)
{
    volatile int acc = 0;
    uint64_t t0 = now_ns();
    for (int i = 0; i < CALLS; i++) acc = bump(acc);
    double call_ns = (double)(now_ns() - t0) / CALLS;

    t0 = now_ns();
    for (int i = 0; i < SYSCALLS; i++) syscall(SYS_getppid);
    double syscall_ns = (double)(now_ns() - t0) / SYSCALLS;

    char *src = malloc(MB), *hot = malloc(MB), *arena = malloc(1UL << 30);
    if (!src || !hot || !arena) { perror("malloc"); return 1; }
    memset(src, 'x', MB);
    memset(hot, 0, MB);
    memset(arena, 0, 1UL << 30);   /* fault every page in before timing */

    uint64_t hot_ns = median_copy_ns(src, pick_hot, hot);
    uint64_t cold_ns = median_copy_ns(src, pick_cold, arena);

    printf("\n01 · The band around twenty-five microseconds\n\n");
    printf("  plain function call          %8.2f ns\n", call_ns);
    printf("  null syscall (getppid)       %8.0f ns\n", syscall_ns);
    printf("  1 MB memcpy, cache-hot dst   %8.1f µs  (%.0f GB/s)\n",
           hot_ns / 1e3, (double)MB / hot_ns);
    printf("  1 MB memcpy, cold dst        %8.1f µs  (%.0f GB/s)\n\n",
           cold_ns / 1e3, (double)MB / cold_ns);
    return acc == -1;
}
