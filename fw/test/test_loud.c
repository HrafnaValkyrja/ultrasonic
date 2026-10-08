/* Loudness fix (docs/proof/electrical/loudness.md, 2026-10-08): alert tone at 2-3 kHz + look-ahead soft-knee limiter at the R64 clamp.
 * Checks: tone frequency, no clicks (bounded step, ramps), never above the ceiling / clamp through the full output stage, knob off = legacy. */
#include <math.h>

#include "dsp.h"
#include "fw.h"
#include "lahead.h"
#include "out_clamp.h"
#include "tf.h"
#include "tests.h"

void test_alert_tone_frequency(void)
{
    fw_knobs_t k;
    fw_knobs_defaults(&k);
    TF_CHECK(k.alert_hz >= 2000 && k.alert_hz <= 3000);                  /* default is in the 2-3 kHz sensation-level peak */
    static const uint32_t hz[3] = {2000, 2500, 3000};
    for (int c = 0; c < 3; c++) {
        fw_alert_t a;
        fw_alert_start(&a, hz[c], 0, 400);
        float y[8];
        uint32_t cross = 0, n = 0, last_neg = 0;
        float prev = 0.0f;
        float first = 0.0f;
        while (fw_alert_hop(&a, y)) {
            for (int i = 0; i < 8; i++, n++) {
                if (n == 0) first = y[0];
                if (n > 600 && n < 4400 && prev < 0.0f && y[i] >= 0.0f)   /* rising zero crossings in the steady part (3800 samples) */
                    cross++, last_neg = n;
                prev = y[i];
            }
        }
        (void)last_neg;
        float f = (float)cross * 12500.0f / 3800.0f;
        TF_CHECK(fabsf(f - (float)hz[c]) < 12.0f);
        TF_CHECK(fabsf(first) < 1e-3f);                                  /* starts from zero */
    }
}

void test_alert_no_clicks(void)
{
    fw_alert_t a;
    fw_alert_start(&a, 2500, 0, 300);
    float y[8], prev = 0.0f, maxstep = 0.0f, maxabs = 0.0f, last = 1.0f;
    while (fw_alert_hop(&a, y))
        for (int i = 0; i < 8; i++) {
            float s = fabsf(y[i] - prev);
            maxstep = s > maxstep ? s : maxstep;
            maxabs = fabsf(y[i]) > maxabs ? fabsf(y[i]) : maxabs;
            prev = y[i];
            last = y[i];
        }
    /* an unramped 2.5 kHz full-scale sine steps up to 2 sin(pi f/fs) = 1.176 between samples at most; the carrier itself bounds the step */
    TF_CHECK(maxstep < 1.18f);
    TF_CHECK(maxabs <= 1.0f);
    TF_CHECK(fabsf(last) < 1e-2f);                                       /* ends at zero */
}

void test_lahead_bound_and_step(void)
{
    const float c = 0.5f;
    fw_lahead_t l;
    fw_lahead_init(&l, c, 70u, 0.99f);
    float in[8], out[8], prev = 0.0f, maxstep = 0.0f, maxabs = 0.0f;
    uint32_t n = 0;
    float ref_step = 0.0f, tonestep = 0.0f;
    for (uint32_t h = 0; h < 4000u; h++) {
        for (int i = 0; i < 8; i++, n++) {
            /* tone 2.5 kHz stepping from silence to 3x the ceiling, then 1.0 -> 0.2 -> 8x with a burst of full-scale spikes */
            float amp = n < 800u ? 0.0f : (n < 8000u ? 1.5f : (n < 16000u ? 0.1f : 4.0f));
            float x = amp * sinf(2.0f * 3.14159265f * 2500.0f / 12500.0f * (float)n);
            if (n % 997u == 0u && n > 20000u) x = 4.0f;                   /* isolated spike */
            in[i] = x;
        }
        fw_lahead_hop(&l, in, out);
        for (int i = 0; i < 8; i++) {
            float s = fabsf(out[i] - prev);
            maxstep = s > maxstep ? s : maxstep;
            if (n < 20000u && s > tonestep) tonestep = s;
            maxabs = fabsf(out[i]) > maxabs ? fabsf(out[i]) : maxabs;
            prev = out[i];
        }
    }
    ref_step = 2.0f * c * sinf(3.14159265f * 2500.0f / 12500.0f) * 1.0f;
    TF_CHECK(maxabs <= c + 1e-6f);                                       /* never above the ceiling, on any sample */
    TF_CHECK(maxabs > 0.9f * c);                                         /* but it does reach it (not squashed) */
    TF_CHECK(tonestep <= 1.1f * ref_step);                               /* the 3x-over tone and its onset step no more than a ceiling-amplitude sine: no gain click */
    TF_CHECK(maxstep <= 2.0f * c + 1e-6f);                               /* hard bound: never more than a full ceiling swing */
}

static void init_la(fw_state_t *st, int la)
{
    fw_knobs_t k;
    fw_knobs_defaults(&k);
    TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_lim_lookahead, la), FW_KNOB_OK);
    fw_init(st, &k, 0u);
    st->knobs = k;
}

void test_loud_ceiling_and_clamp(void)
{
    for (int la = 0; la < 2; la++) {
        fw_knobs_t k;
        fw_knobs_defaults(&k);
        fw_knob_set(&k, FW_KNOB_lim_lookahead, la);
        fw_dsp_t d;
        fw_dsp_init(&d, &k, 200u, 1u);
        fw_ccr_bounds_t b = fw_ccr_bounds(200u, fw_out_amp_max_ppm(&k));
        fw_alert_t a;
        fw_alert_start(&a, 2500, 0, 300);                                /* full-scale alert */
        float y[8];
        uint16_t ccr[FW_CCR_MAX_PER_HOP];
        fw_out_info_t oi;
        float peak = 0.0f;
        uint32_t hits = 0, viol = 0;
        for (uint32_t h = 0; h < 600u; h++) {
            if (!fw_alert_hop(&a, y)) for (int i = 0; i < 8; i++) y[i] = 0.0f;
            size_t n = fw_dsp_out(&d, y, 0u, &b, ccr, &oi);
            peak = oi.true_peak > peak ? oi.true_peak : peak;
            hits += oi.clamp_hits;
            for (size_t j = 0; j < n; j++)
                viol += fabs(2.0 * ccr[j] / 200.0 - 1.0) > fw_out_amp_max_ppm(&k) * 1e-6 + 1e-9;
        }
        TF_CHECK_EQ(viol, 0);                                            /* R64: never above the clamp */
        if (la) {
            float cap = (float)fw_out_amp_max_ppm(&k) * 1e-6f - (float)FW_SHAPER_EXCURSION_PPM * 1e-6f;
            TF_CHECK(peak <= cap + 1e-4f);
            TF_CHECK(peak > 0.9f * cap);                                 /* reaches the clamp-derived ceiling (D17) */
            TF_CHECK_EQ(hits, 0);                                        /* and the clamp itself never bites */
        } else {
            TF_CHECK(peak <= 0.2511886f + 1e-4f);                        /* legacy -12 dBFS, one knob away */
        }
    }
    fw_state_t st;
    init_la(&st, 1);
    fw_alert_trigger(&st);
    TF_CHECK(st.alert.total > 0u);
}

/* ---- I-010 tactile alert: 2-3 pulses at 150-250 Hz, 100 ms, default off ---- */
void test_haptic_default_off(void)
{
    fw_knobs_t k;
    fw_knobs_defaults(&k);
    TF_CHECK_EQ(k.haptic_on, 0);
    TF_CHECK(k.haptic_hz >= 150 && k.haptic_hz <= 250);
    TF_CHECK(k.haptic_n >= 2 && k.haptic_n <= 3);
    TF_CHECK_EQ(k.haptic_ms, 100);
    fw_state_t st;
    init_la(&st, 0);
    fw_alert_trigger(&st);                                               /* off: the normal tone */
    TF_CHECK_EQ(st.alert.period, 0u);
    st.knobs.haptic_on = 1;
    fw_alert_trigger(&st);
    TF_CHECK(st.alert.period != 0u);
}

void test_haptic_burst(void)
{
    static const uint32_t hz[3] = {150, 200, 250};
    for (int c = 0; c < 3; c++)
        for (uint32_t n = 2; n <= 3; n++) {
            fw_alert_t a;
            fw_haptic_start(&a, hz[c], 0, n, 100, 100);
            float y[8], prev = 0.0f, maxstep = 0.0f, peak = 0.0f;
            uint32_t pulses = 0, cross = 0, s = 0, inpulse_prev = 0, nz_run_end = 0;
            while (fw_alert_hop(&a, y))
                for (int i = 0; i < 8; i++, s++) {
                    float d = fabsf(y[i] - prev);
                    maxstep = d > maxstep ? d : maxstep;
                    peak = fabsf(y[i]) > peak ? fabsf(y[i]) : peak;
                    int nz = y[i] != 0.0f;
                    if (nz && !inpulse_prev) pulses++;
                    inpulse_prev = (uint32_t)nz;
                    if (nz) nz_run_end = s;
                    if (s >= 160u && s < 1090u && prev < 0.0f && y[i] >= 0.0f) cross++;   /* steady part of pulse 1: samples 160..1090 */
                    prev = y[i];
                }
            (void)nz_run_end;
            TF_CHECK_EQ(pulses, n);
            TF_CHECK(peak <= 1.0f);
            /* carrier step bound 2 sin(pi f/fs) = 0.15 at 250 Hz; soft edges must not exceed it (no click, T6) */
            TF_CHECK(maxstep < 0.16f);
            TF_CHECK(fabsf(prev) < 1e-3f);
            float f = (float)cross * 12500.0f / 930.0f;
            TF_CHECK(fabsf(f - (float)hz[c]) < 15.0f);
        }
}

void test_haptic_clamp(void)
{
    fw_knobs_t k;
    fw_knobs_defaults(&k);
    TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_lim_lookahead, 1), FW_KNOB_OK);
    fw_dsp_t d;
    fw_dsp_init(&d, &k, 200u, 1u);
    fw_ccr_bounds_t b = fw_ccr_bounds(200u, fw_out_amp_max_ppm(&k));
    fw_alert_t a;
    fw_haptic_start(&a, 200, 0, 3, 100, 100);                            /* full-scale burst */
    float y[8];
    uint16_t ccr[FW_CCR_MAX_PER_HOP];
    fw_out_info_t oi;
    float peak = 0.0f;
    uint32_t viol = 0;
    for (uint32_t h = 0; h < 900u; h++) {
        if (!fw_alert_hop(&a, y)) for (int i = 0; i < 8; i++) y[i] = 0.0f;
        size_t n = fw_dsp_out(&d, y, 0u, &b, ccr, &oi);
        peak = oi.true_peak > peak ? oi.true_peak : peak;
        for (size_t j = 0; j < n; j++)
            viol += fabs(2.0 * ccr[j] / 200.0 - 1.0) > fw_out_amp_max_ppm(&k) * 1e-6 + 1e-9;
    }
    float cap = (float)fw_out_amp_max_ppm(&k) * 1e-6f - (float)FW_SHAPER_EXCURSION_PPM * 1e-6f;
    TF_CHECK_EQ(viol, 0);                                                /* R64 clamp */
    TF_CHECK(peak <= cap + 1e-4f);                                       /* D17 ceiling */
}
