/* 06_crc_zero_seed - the trap chapter 6 sets for the checksum itself.
 *
 * A zero-seeded CRC register produces an all-zero remainder for an
 * all-zero payload. Zeroed blocks are one of the most common shapes a
 * torn write takes, so the one check you added to catch corruption
 * waves through the most common corruption there is.
 *
 * No timing here. This is a correctness demonstration and it is
 * deterministic: it prints the same thing on every machine, which is
 * exactly what makes it checkable.
 */
#include "common.h"

/* CRC-32 (IEEE 802.3), reflected, polynomial 0xEDB88320.
 * `seed` is the initial register value. The standard says 0xFFFFFFFF;
 * the whole point of this program is what happens when it is 0. */
static uint32_t crc32_seeded(const uint8_t *data, size_t len, uint32_t seed)
{
    uint32_t crc = seed;
    for (size_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int b = 0; b < 8; b++)
            crc = (crc >> 1) ^ (0xEDB88320u & (uint32_t)(-(int32_t)(crc & 1)));
    }
    return crc;
}

/* A record as it would sit in a log: header, payload, trailing CRC. */
typedef struct {
    uint8_t  payload[64];
    uint32_t stored_crc;
} record_t;

static int verify(const record_t *r, uint32_t seed)
{
    return crc32_seeded(r->payload, sizeof r->payload, seed) == r->stored_crc;
}

static void show(const char *what, const record_t *r, uint32_t seed, int expect_reject)
{
    uint32_t computed = crc32_seeded(r->payload, sizeof r->payload, seed);
    int accepted = (computed == r->stored_crc);
    const char *verdict = accepted ? "ACCEPTED" : "rejected";
    const char *ok = (accepted == !expect_reject) ? " " : "  <-- WRONG";

    printf("    %-34s stored %08x  computed %08x  %s%s\n",
           what, r->stored_crc, computed, verdict, ok);
}

int main(void)
{
    printf("\n06 · Seed the register nonzero\n");
    printf("    Why an all-zero torn write sails through a zero-seeded CRC.\n\n");

    /* A real record, written correctly. */
    record_t good;
    for (size_t i = 0; i < sizeof good.payload; i++)
        good.payload[i] = (uint8_t)(i * 7 + 1);

    /* The same block after a torn write left it zero-filled. The
     * filesystem returned zeros for storage that was allocated but
     * never written, so payload AND trailer are both zero. */
    record_t torn;
    memset(torn.payload, 0, sizeof torn.payload);
    torn.stored_crc = 0;

    printf("  with seed 0x00000000 (the trap)\n");
    good.stored_crc = crc32_seeded(good.payload, sizeof good.payload, 0);
    show("intact record", &good, 0, 0);
    show("all-zero torn write", &torn, 0, 1);

    printf("\n  with seed 0xFFFFFFFF (the standard)\n");
    good.stored_crc = crc32_seeded(good.payload, sizeof good.payload, 0xFFFFFFFFu);
    show("intact record", &good, 0xFFFFFFFFu, 0);
    show("all-zero torn write", &torn, 0xFFFFFFFFu, 1);

    /* Show it is not a fluke of one length: a zero-seeded CRC returns
     * zero for a zero payload of ANY length. */
    printf("\n  zero-seeded CRC of an all-zero buffer, by length\n    ");
    uint8_t zeros[4096] = {0};
    for (size_t len = 1; len <= 4096; len *= 8)
        printf("%zuB:%08x  ", len, crc32_seeded(zeros, len, 0));
    printf("\n    Always zero. The leading bit is never 1, so the divisor\n");
    printf("    never gets XORed in, so the register never changes.\n");

    /* The verdict, computed rather than asserted. */
    int trap  = verify(&torn, 0);              /* accepted => trap present */
    int fixed = verify(&torn, 0xFFFFFFFFu);    /* accepted => still broken */

    printf("\n  result\n");
    printf("    zero seed accepts the corrupt record:      %s\n", trap  ? "yes" : "no");
    printf("    0xFFFFFFFF seed accepts the corrupt record: %s\n", fixed ? "yes" : "no");

    if (trap && !fixed) {
        printf("\n    Rule 8 holds. The fix is one line and it is the\n");
        printf("    difference between catching this and shipping it.\n\n");
        return 0;
    }
    printf("\n    Unexpected: this build does not reproduce the trap.\n\n");
    return 1;
}
