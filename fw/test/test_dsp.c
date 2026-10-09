/* FWSIM-R13 / R14 / R4: DSP chain host unit tests (the numeric comparison against sim/dsp lives in sim/fw/gen_vectors.py, L1). */
#include <math.h>
#include <string.h>

#include "dsp_math.h"
#include "fw.h"
#include "tf.h"
#include "tests.h"

static void init_k(fw_state_t *st, int32_t algo, int32_t bvar, int32_t khz, int32_t transient)
{
    fw_knobs_t k;
    fw_knobs_defaults(&k);
    TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_algo, algo), FW_KNOB_OK);
    TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_b_variant, bvar), FW_KNOB_OK);
    TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_pwm_khz, khz), FW_KNOB_OK);
    TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_transient_only, transient), FW_KNOB_OK);
    fw_init(st, &k, 0u);
}

static void tone_hop(int32_t *in, double *ph, double f, double amp)
{
    for (uint32_t i = 0; i < FW_HOP_N; i++) {
        *ph += 2.0 * 3.14159265358979 * f / 200e3;
        in[i] = (int32_t)lrint(amp * sin(*ph) * 8388607.0) * 256;
    }
}

void test_dsp_math(void)
{
    double e_log = 0, e_exp = 0, e_om = 0, e_sin = 0;
    for (int i = -3000; i <= 3000; i++) {
        float x = powf(10.0f, (float)i / 100.0f);
        e_log = fmax(e_log, fabs((double)fw_log2f(x) - log2((double)x)));
        float y = (float)i / 50.0f;
        e_exp = fmax(e_exp, fabs((double)fw_exp2f(y) / exp2((double)y) - 1.0));
        float z = powf(10.0f, (float)i / 1000.0f - 3.0f);
        if (z < 20.0f)
            e_om = fmax(e_om, fabs((double)fw_om_exp(z) / -expm1(-(double)z) - 1.0));
    }
    for (uint32_t p = 0; p < 4096u; p++) {
        uint32_t ph = p * 1048573u;
        e_sin = fmax(e_sin, fabs((double)fw_sin_turns(ph) - sin(2.0 * 3.14159265358979 * (double)ph / 4294967296.0)));
    }
    TF_CHECK(e_log <= 6e-6);           /* abs err on |log2| <= 100: float32 ulp-limited (ulp(100) = 7.6e-6) */
    TF_CHECK(e_exp <= 3e-7);
    TF_CHECK(e_om <= 1e-6);
    TF_CHECK(e_sin <= 6e-6);
    TF_CHECK_EQ(fw_log2f(0.0f), -126);
    TF_CHECK_EQ(fw_log2f(-1.0f), -126);
}

/* silence after the power-on hold: squelched, CCR exactly ARR/2 on every period, shaper state zero (F2), all PWM rates */
void test_dsp_silence_exact_centre(void)
{
    static const int32_t khz[3] = {200, 400, 800};
    for (int a = 0; a < 3; a++)
        for (int algo = 1; algo <= 2; algo++) {
            fw_state_t st;
            init_k(&st, algo, 0, khz[a], 1);
            int32_t in[FW_HOP_N];
            uint16_t ccr[FW_CCR_MAX_PER_HOP];
            fw_taps_t t;
            memset(in, 0, sizeof in);
            uint32_t bad = 0;
            for (uint32_t h = 0; h < 800u; h++) {
                fw_poll(&st, (uint64_t)h * 640u);
                size_t n = fw_hop(&st, in, ccr, FW_CCR_MAX_PER_HOP, &t);
                for (size_t j = 0; j < n; j++)
                    bad += ccr[j] != st.arr / 2u;
                bad += t.squelch_state != 1u || t.shaper_norm[0] != 0.0f;
            }
            TF_CHECK_EQ(bad, 0);
        }
}

/* F2 (FWSIM-R14): steady whines only (transient mode): gated by the floor; after the power-on hold CCR == ARR/2 on >= 99.9 % */
void test_dsp_whines_only_squelched(void)
{
    for (int32_t bvar = 0; bvar <= 1; bvar++) {
        fw_state_t st;
        init_k(&st, 2, bvar, 200, 1);
        int32_t in[FW_HOP_N];
        uint16_t ccr[FW_CCR_MAX_PER_HOP];
        double p1 = 0, p2 = 0;
        uint64_t tot = 0, centre = 0;
        for (uint32_t h = 0; h < 4000u; h++) {
            int32_t a[FW_HOP_N], b[FW_HOP_N];
            tone_hop(a, &p1, 25e3, 0.01);
            tone_hop(b, &p2, 33.3e3, 0.005);
            for (uint32_t i = 0; i < FW_HOP_N; i++)
                in[i] = a[i] + b[i];
            fw_poll(&st, (uint64_t)h * 640u);
            size_t n = fw_hop(&st, in, ccr, FW_CCR_MAX_PER_HOP, NULL);
            if (h >= 470u)
                for (size_t j = 0; j < n; j++) {
                    tot++;
                    centre += ccr[j] == 100u;
                }
        }
        TF_CHECK(centre * 1000u >= tot * 999u);
    }
}

/* full mode: a steady 40 kHz tone comes out near map_freq(40 kHz) = 2400 Hz, below the ceiling, not squelched */
void test_dsp_tone_passes_full_mode(void)
{
    for (int32_t bvar = 0; bvar <= 1; bvar++) {
        fw_state_t st;
        init_k(&st, 2, bvar, 200, 0);
        int32_t in[FW_HOP_N];
        uint16_t ccr[FW_CCR_MAX_PER_HOP];
        fw_taps_t t;
        double ph = 0, zc_prev = 0;
        uint32_t zc = 0, ns = 0;
        float pk = 0.0f;
        for (uint32_t h = 0; h < 1600u; h++) {
            tone_hop(in, &ph, 40e3, 0.003);
            fw_poll(&st, (uint64_t)h * 640u);
            (void)fw_hop(&st, in, ccr, FW_CCR_MAX_PER_HOP, &t);
            if (h >= 800u)
                for (uint32_t s = 0; s < 8u; s++) {
                    double y = (double)t.dsp_out[s];
                    zc += (y >= 0) != (zc_prev >= 0);
                    zc_prev = y;
                    ns++;
                }
            pk = t.pre_q_true_peak > pk ? t.pre_q_true_peak : pk;
        }
        double f = zc / 2.0 / (ns / 12500.0);
        TF_CHECK(f > 2300.0 && f < 2500.0);
        TF_CHECK(t.squelch_state == 0u);
        TF_CHECK(pk > 0.001f && pk <= 0.2511887f);
    }
}

/* variants and front ends: slim B frames every other hop (band taps change only on odd hops); D2 entry point lengths */
void test_dsp_variants(void)
{
    fw_state_t st;
    init_k(&st, 2, 1, 200, 1);
    TF_CHECK_EQ(st.dsp.nb, 16);
    TF_CHECK_EQ(st.dsp.ramp_len, 16);
    int32_t in[FW_HOP_N], in400[2 * FW_HOP_N];
    uint16_t ccr[FW_CCR_MAX_PER_HOP];
    fw_taps_t t;
    double ph = 0;
    float prev = -1.0f;
    uint32_t changes_even = 0;
    for (uint32_t h = 0; h < 40u; h++) {
        tone_hop(in, &ph, 30e3 + 500.0 * h, 0.01);
        (void)fw_hop(&st, in, ccr, FW_CCR_MAX_PER_HOP, &t);
        if (h >= 2u && (h & 1u) == 0u && t.band_energy[5] != prev)
            changes_even++;
        prev = t.band_energy[5];
        TF_CHECK_EQ(t.band_energy[20], 0.0f);          /* bands 16..27 unused in slim */
    }
    TF_CHECK_EQ(changes_even, 0);
    init_k(&st, 2, 0, 400, 1);
    TF_CHECK_EQ(st.dsp.nb, 28);
    memset(in400, 0, sizeof in400);
    TF_CHECK_EQ(fw_hop_d2(&st, in400, ccr, FW_CCR_MAX_PER_HOP, &t), 256);
    TF_CHECK_EQ(fw_hop_d2(&st, in400, ccr, 100, &t), 0);
    float nb[28] = {0};
    TF_CHECK_EQ(fw_set_noise_cal(&st, nb, 16u), -1);   /* spec B wants 28 */
    TF_CHECK_EQ(fw_set_noise_cal(&st, nb, 28u), 0);
    TF_CHECK_EQ(fw_set_noise_cal(&st, NULL, 28u), -1);
}

/* FWSIM-R15 (short run; the 1.36e6-hop run is fwsim dsp.ceiling_property): full-scale input never lifts the true peak above
 * the ceiling, and the CCR excursion stays within the shaper bound */
void test_dsp_ceiling_short(void)
{
    fw_state_t st;
    init_k(&st, 2, 0, 200, 0);
    int32_t in[FW_HOP_N];
    uint16_t ccr[FW_CCR_MAX_PER_HOP];
    fw_taps_t t;
    double ph = 0;
    uint32_t bad = 0;
    for (uint32_t h = 0; h < 3000u; h++) {
        tone_hop(in, &ph, 20e3 + 20.0 * h, 0.999);
        fw_poll(&st, (uint64_t)h * 640u);
        size_t n = fw_hop(&st, in, ccr, FW_CCR_MAX_PER_HOP, &t);
        bad += t.pre_q_true_peak > st.dsp.lim_c + 1e-6f;   /* D17 A + L: lim_c = R64 clamp - shaper excursion (0.2511886 with lim_lookahead = 0) */
        for (size_t j = 0; j < n; j++)
            bad += fabs(2.0 * ccr[j] / 200.0 - 1.0) > (double)st.dsp.lim_c + 0.11505 + 1e-9;
        bad += t.clamp_hits;
    }
    TF_CHECK_EQ(bad, 0);
}
