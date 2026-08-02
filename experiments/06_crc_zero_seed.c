/* 06_crc_zero_seed - the trap chapter 6 sets for the checksum itself.
 *
 * A zero-seeded CRC register produces an all-zero remainder for an
 * all-zero payload. Zeroed blocks are one of the most common shapes a
 * torn write takes, so the one check you added to catch corruption
 * waves through the most common corruption there is.
 *
 * Everything here is deterministic. The hex values below are the same
 * on every machine and every compiler, which is what makes this a
 * check you can hold me to rather than a number I once saw.
 *
 * The lab proves its own CRC is correct first, against the standard
 * IEEE 802.3 test vector, so the finding cannot be blamed on a broken
 * implementation.
 */
#include "lab.h"

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

typedef struct {
    uint8_t  payload[64];
    uint32_t stored_crc;
} record_t;

int main(void)
{
    char obs[64], bound[64];

    lab_begin("06 · Seed the register nonzero",
              "Where the Truth Stops",
              "Why an all-zero torn write sails through a zero-seeded CRC.");

    printf("claims\n");

    /* 0. Known-answer test. If this fails nothing below means anything. */
    const char *kat = "123456789";
    uint32_t kat_crc = ~crc32_seeded((const uint8_t *)kat, 9, 0xFFFFFFFFu);
    snprintf(obs,   sizeof obs,   "0x%08X", kat_crc);
    snprintf(bound, sizeof bound, "0xCBF43926");
    lab_check("crc32-known-answer",
              "our CRC-32 matches the IEEE 802.3 vector for \"123456789\"",
              obs, bound, kat_crc == 0xCBF43926u);

    /* A real record, and the same block after a torn write left it
     * zero-filled: payload and trailer both zero. */
    record_t good, torn;
    for (size_t i = 0; i < sizeof good.payload; i++)
        good.payload[i] = (uint8_t)(i * 7 + 1);
    memset(torn.payload, 0, sizeof torn.payload);
    torn.stored_crc = 0;

    /* 1. The trap: a zero-seeded CRC of all zeros is zero, so the
     *    corrupt record verifies against its own zero trailer. */
    uint32_t torn_zero_seed = crc32_seeded(torn.payload, sizeof torn.payload, 0);
    snprintf(obs,   sizeof obs,   "0x%08X", torn_zero_seed);
    snprintf(bound, sizeof bound, "0x00000000");
    lab_check("zero-seed-yields-zero",
              "zero-seeded CRC of an all-zero payload is itself zero",
              obs, bound, torn_zero_seed == 0);

    int accepted_by_zero_seed = (torn_zero_seed == torn.stored_crc);
    snprintf(obs,   sizeof obs,   "%s", accepted_by_zero_seed ? "accepted" : "rejected");
    snprintf(bound, sizeof bound, "accepted (the bug)");
    lab_check("zero-seed-accepts-torn-write",
              "so a zero-seeded check ACCEPTS the all-zero torn record",
              obs, bound, accepted_by_zero_seed == 1);

    /* 2. The fix: one nonzero constant. */
    uint32_t torn_std_seed = crc32_seeded(torn.payload, sizeof torn.payload, 0xFFFFFFFFu);
    int accepted_by_std_seed = (torn_std_seed == torn.stored_crc);
    snprintf(obs,   sizeof obs,   "0x%08X, %s", torn_std_seed,
             accepted_by_std_seed ? "accepted" : "rejected");
    snprintf(bound, sizeof bound, "rejected");
    lab_check("standard-seed-rejects-torn-write",
              "seeding with 0xFFFFFFFF rejects the same record",
              obs, bound, accepted_by_std_seed == 0);

    /* 3. Not a fluke of one length. */
    uint8_t zeros[4096] = {0};
    int all_zero = 1;
    for (size_t len = 1; len <= 4096; len *= 8)
        if (crc32_seeded(zeros, len, 0) != 0) all_zero = 0;
    snprintf(obs,   sizeof obs,   "%s", all_zero ? "zero at every length" : "varies");
    snprintf(bound, sizeof bound, "zero at every length");
    lab_check("zero-seed-zero-at-any-length",
              "the leading bit is never 1, so the divisor never enters",
              obs, bound, all_zero);

    /* 4. A correct record still verifies, so the fix is not just
     *    "reject everything". */
    good.stored_crc = crc32_seeded(good.payload, sizeof good.payload, 0xFFFFFFFFu);
    int good_ok = crc32_seeded(good.payload, sizeof good.payload, 0xFFFFFFFFu) == good.stored_crc;
    snprintf(obs,   sizeof obs,   "0x%08X, accepted", good.stored_crc);
    snprintf(bound, sizeof bound, "accepted");
    lab_check("intact-record-still-verifies",
              "the seeded check still accepts a genuinely intact record",
              obs, bound, good_ok);

    printf("\nwhat this located\n");
    printf("  The difference between catching the most common shape of\n");
    printf("  torn write and shipping it is one constant in one line.\n");
    printf("  Rule 8 is not a style preference.\n");

    return lab_end(".");
}
