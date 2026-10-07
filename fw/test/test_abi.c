/* FWSIM-R9 / R10 / R3: fw_hop ABI and the silence stub. */
#include <string.h>

#include "fake.h"
#include "fw.h"
#include "out_clamp.h"
#include "knobs_def.h"
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
    /* the one exemption: the FMAC math accelerator (pure function of its arguments, hal_fmac.h) */
    uint32_t non_fmac = 0;
    for (uint32_t i = 0; i < fake_log_len(); i++)
        non_fmac += fake_log_at(i)->fn != (uint16_t)FAKE_FN_hal_fmac_fir_bank;
    TF_CHECK_EQ(non_fmac, 0);
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

/* FWSIM-R25 / R46: PWM timing at every clock plan. f_pwm = HCLK / (2 ARR) must be an exact integer multiple R of fs_pcm = HCLK / 400
 * (DMA bursts of 128 R periods per hop), ARR >= HC_ARR_MIN; an illegal rate falls back to the nearest lower legal one; dead time in ns
 * never shorter than the knob's P80 ticks; hop length = 128 R; the fake HAL plan clock equals the core table. */
void test_pwm_per_plan(void)
{
    /* expected ARR per plan for 200 / 400 / 800 kHz; 0 = falls back to 400 kHz */
    static const struct { uint32_t plan, b; uint16_t arr[3]; } t[8] = {
        {HAL_CLK_P80, 200u, {200u, 100u, 50u}},  {HAL_CLK_P160, 400u, {400u, 200u, 100u}},
        {HAL_CLK_P64, 160u, {160u, 80u, 0u}},    {HAL_CLK_P48, 120u, {120u, 60u, 0u}},
        {HAL_CLK_P112, 280u, {280u, 140u, 70u}}, {HAL_CLK_P104, 260u, {260u, 130u, 65u}},
        {HAL_CLK_P72, 180u, {180u, 90u, 0u}},    {HAL_CLK_P52, 130u, {130u, 65u, 0u}},
    };
    static const int32_t khz[3] = {200, 400, 800};
    int32_t in[FW_HOP_N];
    uint16_t ccr[FW_CCR_MAX_PER_HOP];
    fw_taps_t taps;
    memset(in, 0, sizeof in);
    for (int p = 0; p < 8; p++) {
        uint32_t hz = fw_plan_hclk_hz(t[p].plan);
        TF_CHECK_EQ((hz + 200000u) / 400000u, t[p].b);                  /* HCLK = B x 400 kHz within the MSIS rounding */
        TF_CHECK(hal_clock_set_plan((hal_clock_plan_t)t[p].plan) == HAL_OK);
        TF_CHECK_EQ(hal_clock_hclk_hz(), hz);                            /* fake HAL and core agree */
        for (int r = 0; r < 3; r++) {
            fw_knobs_t k;
            fw_knobs_defaults(&k);
            TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_pwm_khz, khz[r]), FW_KNOB_OK);
            TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_clock_plan, (int32_t)t[p].plan), FW_KNOB_OK);
            TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_dead_time_rise_ticks, 3), FW_KNOB_OK);
            fw_state_t st;
            fw_init(&st, &k, 1000u);
            uint32_t want_arr = t[p].arr[r] ? t[p].arr[r] : t[p].arr[1], want_reps = t[p].arr[r] ? (1u << r) : 2u;
            TF_CHECK_EQ(st.arr, want_arr);
            TF_CHECK_EQ(st.pwm_reps, want_reps);
            TF_CHECK_EQ(st.arr * st.pwm_reps, t[p].b);                   /* f_pwm = R x fs_pcm exactly */
            TF_CHECK(st.arr >= HC_ARR_MIN);
            TF_CHECK((uint64_t)st.dt_rise * 80009000u >= 3u * (uint64_t)hz);   /* >= 37.5 ns at every plan */
            TF_CHECK((uint64_t)(st.dt_rise - 1u) * 80009000u < 3u * (uint64_t)hz);   /* and the shortest such */
            TF_CHECK_EQ(fw_hop(&st, in, ccr, FW_CCR_MAX_PER_HOP, &taps), 128u * want_reps);
            TF_CHECK_EQ(ccr[0], want_arr / 2u);
        }
    }
    (void)hal_clock_set_plan(HAL_CLK_P80);
}
