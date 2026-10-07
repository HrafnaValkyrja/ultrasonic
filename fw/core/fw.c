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
}

size_t fw_hop(fw_state_t *st, const int32_t in[FW_HOP_N], uint16_t *ccr, size_t ccr_cap, fw_taps_t *taps)
{
    size_t n = (size_t)FW_HOP_N * 200u / st->arr;
    if (ccr == NULL || ccr_cap < n)
        return 0u;
    (void)in;                                  /* DSP (FWSIM-R13/R14) lands here; until then: silence */
    fw_ccr_bounds_t b = fw_ccr_bounds((uint16_t)st->arr, st->amp_max_ppm);
    uint32_t hits = 0u;
    for (size_t i = 0; i < n; i++)
        ccr[i] = fw_ccr_from_amp(0.0f, &b, &hits);
    st->clamp_hits += hits;
    st->hop_count++;
    if (taps != NULL) {
        memset(taps, 0, sizeof *taps);
        taps->squelch_state = st->squelched;
        taps->n_ccr = (uint32_t)n;
        taps->clamp_hits = hits;
    }
    return n;
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
