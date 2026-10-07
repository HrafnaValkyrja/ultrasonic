/* FWSIM-R3: entry points are pure functions of (fw_state_t, args, injected time): the same event script replayed 1000x gives the
 * identical state hash after every step. */
#include <string.h>

#include "fw.h"
#include "tf.h"
#include "tests.h"

#define STEPS 200u
#define REPLAYS 1000u

static uint32_t rng(uint32_t *s)
{
    uint32_t x = *s;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return *s = x;
}

/* run the script for `seed`; write the per-step hashes; return the final hash */
static uint32_t run_script(uint32_t seed, uint32_t *hashes)
{
    fw_state_t st;
    fw_knobs_t k;
    int32_t in[FW_HOP_N];
    uint16_t ccr[FW_CCR_MAX_PER_HOP];
    fw_taps_t taps;
    uint8_t cdc[16];
    uint64_t t = 1000u;
    uint32_t s = seed;
    fw_knobs_defaults(&k);
    fw_init(&st, &k, t);
    for (uint32_t i = 0; i < STEPS; i++) {
        uint32_t r = rng(&s);
        t += 1u + (r >> 20);                                    /* injected time: 1..4096 us */
        switch (r % 4u) {
        case 0:
            for (uint32_t j = 0; j < FW_HOP_N; j++)
                in[j] = (int32_t)(rng(&s) & 0xFFFFFF00u);       /* 24-bit left-aligned DR words */
            (void)fw_hop(&st, in, ccr, FW_CCR_MAX_PER_HOP, &taps);
            break;
        case 1:
            fw_event(&st, (fw_event_id_t)(rng(&s) % (uint32_t)FW_EV_COUNT), (int32_t)rng(&s), t);
            break;
        case 2:
            fw_poll(&st, t);
            break;
        default:
            memset(cdc, (int)(r & 0xFFu), sizeof cdc);
            (void)fw_cdc_rx(&st, cdc, 1u + (r >> 28), NULL, 0u);
            break;
        }
        if (hashes != NULL)
            hashes[i] = fw_state_hash(&st);
    }
    return fw_state_hash(&st);
}

void test_replay_state_hash(void)
{
    static uint32_t ref[STEPS], got[STEPS];
    uint32_t h0 = run_script(0x1234567u, ref), mism = 0;
    for (uint32_t rep = 0; rep < REPLAYS; rep++) {
        uint32_t h = run_script(0x1234567u, got);
        if (h != h0 || memcmp(ref, got, sizeof ref) != 0)
            mism++;
    }
    TF_CHECK_EQ(mism, 0);
    /* sensitivity: another script, or one more poll, changes the hash */
    TF_CHECK(run_script(0x7654321u, NULL) != h0);
    uint32_t distinct = 0;
    for (uint32_t i = 1; i < STEPS; i++)
        distinct += ref[i] != ref[i - 1];
    TF_CHECK(distinct > STEPS / 2u);
}
