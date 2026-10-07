/* FWSIM-R9 / R10 / R3: fw_hop ABI and the silence stub. */
#include <string.h>

#include "fake.h"
#include "fw.h"
#include "tf.h"
#include "tests.h"

static void init_with_khz(fw_state_t *st, int32_t khz)
{
    fw_knobs_t k;
    fw_knobs_defaults(&k);
    TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_pwm_khz, khz), FW_KNOB_OK);
    fw_init(st, &k, 1000u);
}

void test_abi_hop_lengths(void)
{
    static const int32_t khz[3] = {200, 400, 800};
    static const uint16_t arr[3] = {200, 100, 50};
    int32_t in[FW_HOP_N];
    uint16_t ccr[FW_CCR_MAX_PER_HOP + 1];
    fw_taps_t taps;
    memset(in, 0, sizeof in);
    TF_CHECK_EQ(FW_ABI_VERSION, 1);
    TF_CHECK_EQ(FW_HOP_N, 128);
    for (int i = 0; i < 3; i++) {
        fw_state_t st;
        init_with_khz(&st, khz[i]);
        TF_CHECK_EQ(st.arr, arr[i]);
        size_t want = 128u * 200u / arr[i];
        ccr[want] = 0xBEEF;
        TF_CHECK_EQ(fw_hop(&st, in, ccr, FW_CCR_MAX_PER_HOP, &taps), want);
        TF_CHECK_EQ(taps.n_ccr, want);
        TF_CHECK_EQ(ccr[want], 0xBEEF);                 /* no write past n */
        for (size_t j = 0; j < want; j++)
            if (ccr[j] != arr[i] / 2u) { TF_CHECK_EQ(ccr[j], arr[i] / 2u); break; }   /* silence = centre (V_diff 0) */
        TF_CHECK_EQ(taps.squelch_state, 1);             /* power-on hold (e2e F4) */
        TF_CHECK_EQ(taps.clamp_hits, 0);
        /* too-small buffer: nothing written, 0 returned */
        uint16_t small[4] = {7, 7, 7, 7};
        TF_CHECK_EQ(fw_hop(&st, in, small, 4, NULL), 0);
        TF_CHECK_EQ(small[0], 7);
        TF_CHECK_EQ(fw_hop(&st, in, NULL, 1000, NULL), 0);
    }
}

void test_abi_pure(void)
{
    /* entry points call no HAL function (FWSIM-R3): the fake call log stays empty */
    fake_reset();
    fw_state_t st;
    fw_knobs_t k;
    int32_t in[FW_HOP_N] = {0};
    uint16_t ccr[FW_CCR_MAX_PER_HOP];
    uint8_t buf[4] = {1, 2, 3, 4};
    fw_knobs_defaults(&k);
    fw_init(&st, &k, 5u);
    (void)fw_hop(&st, in, ccr, FW_CCR_MAX_PER_HOP, NULL);
    fw_poll(&st, 10u);
    fw_event(&st, FW_EV_BUTTON_SHORT, 1, 20u);
    (void)fw_cdc_rx(&st, buf, sizeof buf, NULL, 0u);
    (void)fw_state_hash(&st);
    TF_CHECK_EQ(fake_log_len(), 0);
}

void test_abi_power_on_hold(void)
{
    fw_state_t st;
    fw_knobs_t k;
    fw_knobs_defaults(&k);
    fw_init(&st, &k, 1000000u);
    fw_poll(&st, 1000000u + 299999u);
    TF_CHECK_EQ(st.squelched, 1);
    fw_poll(&st, 1000000u + 300000u);
    TF_CHECK_EQ(st.squelched, 0);
    fw_poll(&st, 5u);                                    /* time never runs backwards in the state */
    TF_CHECK_EQ(st.now_us, 1300000u);
}
