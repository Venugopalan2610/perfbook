/* 02_ladder_survival - pinpoint where the bytes are, by killing the
 * process that wrote them.
 *
 * Chapter 2 says a byte lives on one of four rungs, and that what
 * kills it depends entirely on which rung it is on. That is testable
 * for the first two rungs without any special hardware:
 *
 *   rung 1, userspace buffer : dies with the process
 *   rung 2, page cache       : survives the process, dies with the OS
 *
 * We kill the writer with SIGKILL at three different moments and see
 * what is left. SIGKILL runs no atexit handler, flushes no stdio
 * buffer, and unwinds nothing. It is the honest version of "the
 * process went away."
 *
 * This lab is deterministic. The byte counts below are the same on
 * every Linux machine, which is what makes it a check rather than an
 * anecdote. Rungs 3 and 4 need the power cut that chapter 2 is about,
 * and we deliberately do not fake it.
 */
#include "lab.h"
#include <fcntl.h>
#include <signal.h>
#include <sys/wait.h>
#include <sys/stat.h>

enum { PAYLOAD = 64 * 1024 };

/* Fork a writer, have it die by SIGKILL at the requested moment, and
 * report how many bytes of the file outlived it. */
static long long survives_sigkill(const char *path, int do_fflush, int do_fsync)
{
    unlink(path);

    pid_t pid = fork();
    if (pid < 0) { perror("fork"); exit(2); }

    if (pid == 0) {
        char *buf = malloc(PAYLOAD);
        if (!buf) _exit(3);
        memset(buf, 'x', PAYLOAD);

        FILE *f = fopen(path, "w");
        if (!f) _exit(4);
        /* A buffer larger than the payload, so fwrite cannot be forced
         * into an early flush by running out of room. */
        static char sbuf[2 * PAYLOAD];
        setvbuf(f, sbuf, _IOFBF, sizeof sbuf);

        fwrite(buf, 1, PAYLOAD, f);          /* rung 1: our own memory */
        if (do_fflush) fflush(f);            /* rung 2: the kernel's   */
        if (do_fsync)  fsync(fileno(f));     /* rung 3/4: the device   */

        raise(SIGKILL);                      /* no cleanup, no flush   */
        _exit(5);
    }

    int status = 0;
    waitpid(pid, &status, 0);
    if (!WIFSIGNALED(status) || WTERMSIG(status) != SIGKILL) {
        fprintf(stderr, "child did not die by SIGKILL as expected\n");
        exit(2);
    }

    struct stat st;
    if (stat(path, &st) != 0) return 0;      /* file never appeared */
    return (long long)st.st_size;
}

int main(void)
{
    const char *dir = scratch_dir();
    char path[1024], obs[64], bound[64];
    snprintf(path, sizeof path, "%s/.perfbook_02.tmp", dir);

    lab_begin("02 · Which rung is your data on?",
              "The Ladder",
              "SIGKILL the writer at three moments and see what is left.");
    print_environment(dir);

    printf("claims\n");

    /* Rung 1. fwrite alone never leaves the process. */
    long long a = survives_sigkill(path, 0, 0);
    snprintf(obs,   sizeof obs,   "%lld bytes", a);
    snprintf(bound, sizeof bound, "0 bytes");
    lab_check("userspace-buffer-dies",
              "fwrite alone: the kernel never saw it, so SIGKILL loses all of it",
              obs, bound, a == 0);

    /* Rung 2. One fflush is the whole difference. */
    long long b = survives_sigkill(path, 1, 0);
    snprintf(obs,   sizeof obs,   "%lld bytes", b);
    snprintf(bound, sizeof bound, "%d bytes", PAYLOAD);
    lab_check("page-cache-survives-process",
              "after fflush: the kernel holds it, so SIGKILL loses nothing",
              obs, bound, b == PAYLOAD);

    /* Rung 3/4. fsync changes durability, not process-crash survival. */
    long long c = survives_sigkill(path, 1, 1);
    snprintf(obs,   sizeof obs,   "%lld bytes", c);
    snprintf(bound, sizeof bound, "%d bytes", PAYLOAD);
    lab_check("fsync-adds-nothing-here",
              "fsync survives SIGKILL too, and buys nothing this test can see",
              obs, bound, c == PAYLOAD);

    printf("\nwhat this located, and what it did not\n");
    printf("  The boundary between rung 1 and rung 2 is one fflush, and\n");
    printf("  it is worth %d bytes of acknowledged data.\n", PAYLOAD);
    printf("\n");
    printf("  Notice the third check. fsync passed, exactly like the one\n");
    printf("  before it, and proved nothing the second did not. A test\n");
    printf("  that cannot reach rung 3 cannot tell you anything about\n");
    printf("  rung 3, no matter how many times you run it. That is Rule 4,\n");
    printf("  and this lab is an instance of the mistake it warns about.\n");
    printf("\n");
    printf("  To separate rungs 3 and 4 you need the wall socket, an IPMI\n");
    printf("  power cycle or a managed PDU, and a second machine to check\n");
    printf("  from. No process running on this one can do it honestly.\n");

    unlink(path);
    return lab_end(dir);
}
