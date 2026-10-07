/* fw/core/fw.c: entry points (pure: state + args + injected time). */
#include "fw.h"

#include <string.h>

#include "crc32.h"
#include "out_clamp.h"
#include "variant_config.h"

static void apply_knobs(fw_state_t *st)
{
    st->arr = fw_arr_for_khz(st->knobs.pwm_khz);
    st->amp_max_ppm = fw_out_amp_max_ppm(&st->knobs);
}

void fw_init(fw_state_t *st, const fw_knobs_t *knobs, uint64_t now_us)
{
    memset(st, 0, sizeof *st);                 /* padding too: the state hash covers every byte */
    st->abi = FW_ABI_VERSION;
    st->knobs = *knobs;
    (void)fw_knobs_sanitize(&st->knobs);
    st->now_us = now_us;
    st->boot_us = now_us;
    st->squelched = 1u;
    apply_knobs(st);
    fw_dsp_init(&st->dsp, &st->knobs, st->arr);
}

static size_t hop_pcm(fw_state_t *st, const float pcm[FW_HOP_N], uint16_t *ccr, fw_taps_t *taps)
{
    float y8[FW_DSP_OUT_N];
    fw_out_info_t oi;
    if (taps != NULL)
        memset(taps, 0, sizeof *taps);
    fw_dsp_algo(&st->dsp, pcm, y8, taps ? taps->band_energy : NULL, taps ? taps->floor : NULL);
    fw_ccr_bounds_t b = fw_ccr_bounds((uint16_t)st->arr, st->amp_max_ppm);
    size_t n = fw_dsp_out(&st->dsp, y8, st->squelched, &b, ccr, &oi);
    st->clamp_hits += oi.clamp_hits;
    st->hop_count++;
    if (taps != NULL) {
        memcpy(taps->dsp_out, y8, sizeof y8);
        taps->pre_q_true_peak = oi.true_peak;
        memcpy(taps->shaper_norm, oi.shaper_norm, sizeof taps->shaper_norm);
        taps->squelch_state = oi.squelched;
        taps->n_ccr = (uint32_t)n;
        taps->clamp_hits = oi.clamp_hits;
    }
    return n;
}

size_t fw_hop(fw_state_t *st, const int32_t in[FW_HOP_N], uint16_t *ccr, size_t ccr_cap, fw_taps_t *taps)
{
    size_t n = (size_t)FW_HOP_N * 200u / st->arr;
    if (in == NULL || ccr == NULL || ccr_cap < n)
        return 0u;
    float pcm[FW_HOP_N];
    for (size_t i = 0; i < FW_HOP_N; i++)
        pcm[i] = (float)in[i];                 /* exact: 24-bit sample << 8 fits the float32 mantissa */
    return hop_pcm(st, pcm, ccr, taps);
}

size_t fw_hop_d2(fw_state_t *st, const int32_t in400[2u * FW_HOP_N], uint16_t *ccr, size_t ccr_cap, fw_taps_t *taps)
{
    size_t n = (size_t)FW_HOP_N * 200u / st->arr;
    if (in400 == NULL || ccr == NULL || ccr_cap < n)
        return 0u;
    float pcm[FW_HOP_N];
    fw_dsp_halfband(&st->dsp, in400, pcm);
    return hop_pcm(st, pcm, ccr, taps);
}

int fw_set_noise_cal(fw_state_t *st, const float *band_energy, uint32_t n)
{
    return fw_dsp_set_noise(&st->dsp, band_energy, n);
}

void fw_poll(fw_state_t *st, uint64_t now_us)
{
    if (now_us > st->now_us)
        st->now_us = now_us;                   /* time never runs backwards inside the state */
    if (st->squelched && st->now_us - st->boot_us >= (uint64_t)st->knobs.power_on_hold_ms * 1000u)
        st->squelched = 0u;
}

void fw_event(fw_state_t *st, fw_event_id_t id, int32_t arg, uint64_t now_us)
{
    fw_poll(st, now_us);
    if ((uint32_t)id >= (uint32_t)FW_EV_COUNT)
        return;
    st->event_count[id]++;
    st->last_event = (uint32_t)id;
    st->last_arg = arg;
    if (id == FW_EV_VBUS_ON)
        st->vbus = 1u;
    else if (id == FW_EV_VBUS_OFF)
        st->vbus = 0u;
}

size_t fw_cdc_rx(fw_state_t *st, const uint8_t *buf, size_t len, uint8_t *reply, size_t reply_cap)
{
    (void)buf;
    (void)reply;
    (void)reply_cap;
    st->cdc_bytes += (uint32_t)len;
    return 0u;
}

uint32_t fw_state_hash(const fw_state_t *st)
{
    return fw_crc32_update(0u, st, sizeof *st);
}
