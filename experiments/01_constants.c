/* 01_constants - the band in the chapter "Success, Too Soon".
 *
 * The chapter places a small write() between floors: a bare function call
 * and an empty system call below it, a copy of 4 KB in memory beside it,
 * and a round trip to a drive far above it. This prints the first three
 * for your machine. The fourth is the chapter "The Barrier"'s lab.
 *
 * Every copy is followed by a compiler barrier on its destination. Without
 * it, the compiler sees that nothing reads the copy, deletes it, and this
 * program reports memory moved in zero time: the floor test from the same
 * chapter, failing on the program that was meant to illustrate it. That
 * happened once, while this lab was being written.
 */
#include "common.h"
#include <sys/syscall.h>

#define BLOCK 4096

enum { CALLS = 2000000, SYSCALLS = 200000, COPIES = 200000 };

__attribute__((noinline)) static int bump(int x)
{
    __asm__ volatile("");
    return x + 1;
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

    /* 4 KB is far too short to time one copy against the clock, so time
     * many and divide. Same destination each time: this is the copy a
     * write() makes into a page the kernel already has. */
    static char src[BLOCK], dst[BLOCK];
    memset(src, 'x', BLOCK);
    t0 = now_ns();
    for (int i = 0; i < COPIES; i++) {
        memcpy(dst, src, BLOCK);
        __asm__ volatile("" :: "r"(dst) : "memory");
    }
    double copy_ns = (double)(now_ns() - t0) / COPIES;

    printf("\n01 · The band around a small write\n\n");
    printf("  plain function call          %8.2f ns\n", call_ns);
    printf("  null syscall (getppid)       %8.0f ns\n", syscall_ns);
    printf("  4 KB memcpy                  %8.0f ns  (%.0f GB/s)\n\n",
           copy_ns, BLOCK / copy_ns);
    return acc == -1;
}
