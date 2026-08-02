/* lab.h - what turns a benchmark into a lab.
 *
 * A benchmark prints a number. You cannot tell a correct run from a
 * broken one, and you cannot compare your run to mine because our
 * hardware differs.
 *
 * A lab makes claims and checks them. The claims are written as
 * RATIOS and as EXACT invariants, because those survive the change of
 * hardware that absolute latency does not. A 700 µs fsync and a 100 µs
 * fsync are both fine; an fsync that is not at least a few times a
 * buffered write means you are not measuring storage at all.
 *
 * Every lab:
 *   - states each claim before testing it
 *   - exits nonzero if any claim fails
 *   - writes results.json so runs can be diffed across machines
 */
#ifndef LAB_H
#define LAB_H

#include "common.h"

#define LAB_MAX_CHECKS 64

typedef struct {
    char   id[64];
    char   claim[160];
    char   observed[64];
    char   bound[64];
    int    pass;
} check_t;

static check_t  lab_checks[LAB_MAX_CHECKS];
static int      lab_n_checks = 0;
static const char *lab_name = "lab";
static const char *lab_chapter = "";

MAYBE_UNUSED static void lab_begin(const char *name, const char *chapter, const char *subtitle)
{
    lab_name = name;
    lab_chapter = chapter;
    printf("\n%s\n", name);
    printf("    %s\n", subtitle);
    printf("    chapter: %s\n\n", chapter);
}

/* Record one claim and whether the run upheld it. */
MAYBE_UNUSED static void lab_check(const char *id, const char *claim,
                                   const char *observed, const char *bound, int pass)
{
    if (lab_n_checks < LAB_MAX_CHECKS) {
        check_t *c = &lab_checks[lab_n_checks++];
        snprintf(c->id,       sizeof c->id,       "%s", id);
        snprintf(c->claim,    sizeof c->claim,    "%s", claim);
        snprintf(c->observed, sizeof c->observed, "%s", observed);
        snprintf(c->bound,    sizeof c->bound,    "%s", bound);
        c->pass = pass;
    }
    printf("  [%s] %-38s %s\n", pass ? "PASS" : "FAIL", id, claim);
    printf("         observed %-22s expected %s\n", observed, bound);
}

static void json_escape(const char *in, char *out, size_t n)
{
    size_t o = 0;
    for (size_t i = 0; in[i] && o + 2 < n; i++) {
        if (in[i] == '"' || in[i] == '\\') { out[o++] = '\\'; out[o++] = in[i]; }
        else if ((unsigned char)in[i] < 0x20) { out[o++] = ' '; }
        else out[o++] = in[i];
    }
    out[o] = '\0';
}

MAYBE_UNUSED static void lab_capture_env(const char *dir, char *out, size_t n)
{
    char kernel[256] = "", fs[512] = "", virt[64] = "", cmd[1024];
    run_quiet("uname -sr", kernel, sizeof kernel);
    snprintf(cmd, sizeof cmd,
             "findmnt -no FSTYPE,SOURCE,OPTIONS --target '%s' 2>/dev/null", dir);
    run_quiet(cmd, fs, sizeof fs);
    run_quiet("systemd-detect-virt 2>/dev/null || echo unknown", virt, sizeof virt);

    char ek[300], ef[600], ev[80];
    json_escape(kernel, ek, sizeof ek);
    json_escape(fs, ef, sizeof ef);
    json_escape(virt, ev, sizeof ev);
    snprintf(out, n,
        "    \"kernel\": \"%s\",\n"
        "    \"mount\": \"%s\",\n"
        "    \"virtualization\": \"%s\"",
        ek, ef, ev);
}

/* Append this lab's result to results.json (one JSON object per line,
 * so runs concatenate and diff cleanly). Returns process exit code. */
MAYBE_UNUSED static int lab_end(const char *dir)
{
    int failed = 0;
    for (int i = 0; i < lab_n_checks; i++) if (!lab_checks[i].pass) failed++;

    printf("\n  %d checks, %d passed, %d failed\n",
           lab_n_checks, lab_n_checks - failed, failed);
    if (failed)
        printf("  A failure here usually means the environment, not the book.\n"
               "  Check the mount line above: tmpfs and overlayfs both break\n"
               "  the assumptions these claims are written against.\n");
    printf("\n");

    const char *out = getenv("PERFBOOK_RESULTS");
    if (out && *out) {
        FILE *f = fopen(out, "a");
        if (f) {
            char env[1200];
            lab_capture_env(dir, env, sizeof env);
            fprintf(f, "{\n  \"lab\": \"%s\",\n  \"chapter\": \"%s\",\n",
                    lab_name, lab_chapter);
            fprintf(f, "  \"environment\": {\n%s\n  },\n", env);
            fprintf(f, "  \"checks\": [\n");
            for (int i = 0; i < lab_n_checks; i++) {
                char c[400], o[128], b[128];
                json_escape(lab_checks[i].claim, c, sizeof c);
                json_escape(lab_checks[i].observed, o, sizeof o);
                json_escape(lab_checks[i].bound, b, sizeof b);
                fprintf(f, "    {\"id\": \"%s\", \"claim\": \"%s\", "
                           "\"observed\": \"%s\", \"expected\": \"%s\", \"pass\": %s}%s\n",
                        lab_checks[i].id, c, o, b,
                        lab_checks[i].pass ? "true" : "false",
                        i + 1 < lab_n_checks ? "," : "");
            }
            fprintf(f, "  ],\n  \"failed\": %d\n}\n", failed);
            fclose(f);
        }
    }
    return failed ? 1 : 0;
}

#endif /* LAB_H */
