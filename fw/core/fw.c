/* fw/core/fw.c: entry points (pure: state + args + injected time). */
#include "fw.h"

#include <string.h>

#include "crc32.h"
#include "dsp_math.h"
#include "out_clamp.h"
#include "variant_config.h"

static void apply_knobs(fw_state_t *st)
{
    int32_t eff = 200;
    st->arr = fw_arr_for_khz(st->knobs.pwm_khz, (uint32_t)st->knobs.clock_plan, &eff);
    st->pwm_reps = (uint32_t)eff / 200u;
    st->dt_rise = fw_dead_ticks((uint32_t)st->knobs.dead_time_rise_ticks, (uint32_t)st->knobs.clock_plan);
    st->dt_fall = fw_dead_ticks((uint32_t)st->knobs.dead_time_fall_ticks, (uint32_t)st->knobs.clock_plan);
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
    fw_dsp_init(&st->dsp, &st->knobs, st->arr, st->pwm_reps);
    fw_sys_init(&st->sys, &st->knobs, now_us);
    fw_idle_init(&st->idle);
}

/* volume tick pattern (spec D3): vol_idx + 1 ticks of 15 ms (sin^2 envelope) every 100 ms at tick_hz / tick_cdb, added to the algorithm
 * output so it passes the same squelch, true-peak limiter and FWSIM-R64 clamp as everything else (FWSIM-R29) */
#define TICK_ON 188u
#define TICK_PERIOD 1250u
static void tick_add(fw_state_t *st, float y8[FW_DSP_OUT_N])
{
    fw_sys_t *s = &st->sys;
    if (s->tick_left == 0u)
        return;
    float amp = fw_db20_to_lin((float)st->knobs.tick_cdb * 0.01f);
    uint32_t inc = (uint32_t)((((uint64_t)(uint32_t)st->knobs.tick_hz << 32) + 6250u) / 12500u);
    for (uint32_t i = 0; i < FW_DSP_OUT_N && s->tick_left; i++) {
        if (s->tick_pos < TICK_ON) {
            float w = fw_sin_turns((uint32_t)(((uint64_t)s->tick_pos << 31) / TICK_ON));   /* sin(pi pos / L) */
            s->tick_ph += inc;
            y8[i] += amp * w * w * fw_sin_turns(s->tick_ph);
        }
        if (++s->tick_pos >= TICK_PERIOD) {
            s->tick_pos = 0u;
            s->tick_left--;
        }
    }
}

static void sync_volume(fw_state_t *st)
{
    if (st->sys.mode == (uint32_t)FW_ST_FULL)        /* the live mode drives the DSP gate (D12) */
        st->dsp.transient = 0u;
    else if (st->sys.mode == (uint32_t)FW_ST_TRANSIENT)
        st->dsp.transient = 1u;
    int32_t v = fw_sys_volume_offset_cdb(&st->sys, &st->knobs);
    if (v != st->vol_offset_cdb) {
        st->vol_offset_cdb = v;
        fw_dsp_set_gain_cdb(&st->dsp, st->knobs.volume_cdb + v);
    }
}

fw_outputs_t fw_outputs(const fw_state_t *st)
{
    return fw_sys_outputs(&st->sys);
}

static size_t hop_pcm(fw_state_t *st, const float pcm[FW_HOP_N], uint16_t *ccr, fw_taps_t *taps)
{
    float y8[FW_DSP_OUT_N];
    fw_out_info_t oi;
    if (taps != NULL)
        memset(taps, 0, sizeof *taps);
    /* look-back (spec C9 'the look-back buffer covers the wake-up'): with the idle detector on, the algorithm runs FW_IDLE_LOOKBACK hops
     * behind the detector, so a call that wakes the pod is still ahead of the algorithm (+7.7 ms latency); off: no delay (L1 alignment) */
    const float *apcm = pcm;
    if (st->knobs.idle_enable) {
        uint32_t slot = st->lb_head;
        for (uint32_t i = 0; i < FW_HOP_N; i++) {
            float x = st->lb[slot][i];
            st->lb[slot][i] = pcm[i];
            st->lb_out[i] = x;
        }
        st->lb_head = slot + 1u >= FW_IDLE_LOOKBACK ? 0u : slot + 1u;
        apcm = st->lb_out;
    }
    fw_dsp_pcm_push(&st->dsp, apcm);
    /* idle detector (spec C9): every 8 hops while listening or idle; Transient -> IDLE when quiet, IDLE -> back on activity */
    uint32_t m = st->sys.mode;
    if (st->knobs.idle_enable && (m == (uint32_t)FW_ST_FULL || m == (uint32_t)FW_ST_TRANSIENT || m == (uint32_t)FW_ST_IDLE) &&
        fw_idle_hop(&st->idle, &st->dsp, pcm)) {
        if (st->idle.active && m == (uint32_t)FW_ST_IDLE)
            fw_sys_fsm(&st->sys, &st->knobs, FW_FE_WAKE, st->now_us);
        else if (!st->idle.active && m != (uint32_t)FW_ST_IDLE && st->idle.frames > st->idle.hang_hops)
            fw_sys_fsm(&st->sys, &st->knobs, FW_FE_QUIET, st->now_us);
    }
    fw_outputs_t o = fw_sys_outputs(&st->sys);
    if (st->sys.mode == (uint32_t)FW_ST_IDLE) {                  /* IDLE: the algorithm sleeps (power model: 16 MHz detector only) */
        for (uint32_t i = 0; i < FW_DSP_OUT_N; i++)
            y8[i] = 0.0f;
    } else {
        fw_dsp_algo(&st->dsp, apcm, y8, taps ? taps->band_energy : NULL, taps ? taps->floor : NULL);
    }
    tick_add(st, y8);
    fw_ccr_bounds_t b = fw_ccr_bounds((uint16_t)st->arr, st->amp_max_ppm);
#if FW_VAR_DOCKED_OUTPUT_MAX
    if (o.selftest) {
        size_t nr = fw_selftest_hop(st, y8, &b, ccr, &oi.clamp_hits);   /* replaces the DSP output (tone, or raw bring-up drive) */
        if (nr != 0u) {
            st->clamp_hits += oi.clamp_hits;
            st->hop_count++;
            if (taps != NULL) {
                taps->n_ccr = (uint32_t)nr;
                taps->clamp_hits = oi.clamp_hits;
            }
            return nr;
        }
    }
#endif
    size_t n = fw_dsp_out(&st->dsp, y8, (st->squelched || !o.output_enable) ? 1u : 0u, &b, ccr, &oi);
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
    size_t n = (size_t)FW_HOP_N * st->pwm_reps;
    if (in == NULL || ccr == NULL || ccr_cap < n)
        return 0u;
    float pcm[FW_HOP_N];
    for (size_t i = 0; i < FW_HOP_N; i++)
        pcm[i] = (float)in[i];                 /* exact: 24-bit sample << 8 fits the float32 mantissa */
    return hop_pcm(st, pcm, ccr, taps);
}

size_t fw_hop_d2(fw_state_t *st, const int32_t in400[2u * FW_HOP_N], uint16_t *ccr, size_t ccr_cap, fw_taps_t *taps)
{
    size_t n = (size_t)FW_HOP_N * st->pwm_reps;
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
    fw_sys_poll(&st->sys, &st->knobs, st->now_us);
    sync_volume(st);
}

#if FW_VAR_DOCKED_OUTPUT_MAX
/* ECR-0009 variant (a) self-test drive: a tone capped at selftest_cap_cdb through the normal output stage (ceiling, shaper, FWSIM-R64
 * clamp), or the raw bring-up drive (constant V_diff/Vdd) straight through fw_ccr_from_amp (FWSIM-R64 clamp only). Variant (b): absent. */
size_t fw_selftest_hop(fw_state_t *st, float y8[FW_DSP_OUT_N], const fw_ccr_bounds_t *b, uint16_t *ccr, uint32_t *hits)
{
    fw_sys_t *s = &st->sys;
    size_t n = (size_t)FW_HOP_N * st->pwm_reps;
    *hits = 0u;
    if (s->st_raw_active) {
        float a = (float)s->st_raw_q15 * 0x1p-15f;
        for (size_t i = 0; i < n; i++)
            ccr[i] = fw_ccr_from_amp(a, b, hits);
        return n;
    }
    int32_t cdb = s->st_amp_cdb < st->knobs.selftest_cap_cdb ? s->st_amp_cdb : st->knobs.selftest_cap_cdb;
    float amp = fw_db20_to_lin((float)cdb * 0.01f);
    uint32_t inc = (uint32_t)((((uint64_t)s->st_freq_hz << 32) + 6250u) / 12500u);
    for (uint32_t i = 0; i < FW_DSP_OUT_N; i++) {
        s->st_ph += inc;
        y8[i] = amp * fw_sin_turns(s->st_ph);
    }
    fw_out_info_t oi;
    size_t m = fw_dsp_out(&st->dsp, y8, 0u, b, ccr, &oi);
    *hits = oi.clamp_hits;
    return m;
}
#endif

void fw_event(fw_state_t *st, fw_event_id_t id, int32_t arg, uint64_t now_us)
{
    fw_poll(st, now_us);
    if ((uint32_t)id >= (uint32_t)FW_EV_COUNT)
        return;
    st->event_count[id]++;
    st->last_event = (uint32_t)id;
    st->last_arg = arg;
    fw_sys_t *s = &st->sys;
    switch (id) {
    case FW_EV_VBUS_ON:
    case FW_EV_VBUS_OFF:
        st->vbus = id == FW_EV_VBUS_ON ? 1u : 0u;
        if (!st->vbus)
        {
            st->usb_enumerated = 0u;                /* a dumb charger after a host must start again at 100 mA */
            st->usb_suspended = 0u;
        }
        fw_sys_vbus_edge(s, st->vbus, st->now_us);
        break;
    case FW_EV_BTN_EDGE:
        fw_sys_btn_edge(s, arg != 0 ? 1u : 0u, st->now_us);
        break;
    case FW_EV_BREAK:
        s->brk_latched = 1u;
        s->brk_events++;
        s->brk_us = st->now_us;
        fw_sys_fsm(s, &st->knobs, FW_FE_FAULT, st->now_us);
        break;
    case FW_EV_QUIET:
        fw_sys_fsm(s, &st->knobs, FW_FE_QUIET, st->now_us);
        break;
    case FW_EV_WAKE:
        fw_sys_fsm(s, &st->knobs, FW_FE_WAKE, st->now_us);
        break;
    case FW_EV_USB_ENUMERATED:
        st->usb_enumerated = arg == 1 ? 1u : 0u;
        st->usb_suspended = arg == 2 ? 1u : 0u;
        break;
    case FW_EV_DFU_ABORT:
        fw_sys_fsm(s, &st->knobs, FW_FE_DFU_ABORT, st->now_us);
        break;
    default:
        break;
    }
    fw_sys_poll(s, &st->knobs, st->now_us);
    sync_volume(st);
}

void fw_brk_clear_done(fw_state_t *st)
{
    st->sys.brk_clear_req = 0u;
}

size_t fw_cdc_rx(fw_state_t *st, const uint8_t *buf, size_t len, uint8_t *reply, size_t reply_cap)
{
    st->cdc_bytes += (uint32_t)len;
    uint8_t r = 0x15u;                                            /* NACK */
    if (buf != NULL && len >= 3u && buf[0] == 0xA5u && (size_t)buf[2] + 3u <= len) {
        const uint8_t *p = &buf[3];
        uint8_t type = buf[1], n = buf[2];
        fw_sys_t *s = &st->sys;
        switch (type) {
        case 0x01u:                                               /* ST_ARM {int16 amp_cdb, uint16 freq_hz} */
            if (n == 4u) {
                s->st_amp_cdb = (int16_t)((uint16_t)p[0] | (uint16_t)((uint16_t)p[1] << 8));
                s->st_freq_hz = (uint32_t)p[2] | (uint32_t)p[3] << 8;
                if (s->st_freq_hz > 6000u)
                    s->st_freq_hz = 6000u;
                s->st_raw_active = 0u;
                uint32_t before = s->mode;
                fw_sys_fsm(s, &st->knobs, FW_FE_ST_ARM, st->now_us);
                r = (s->mode == (uint32_t)FW_ST_DOCKED_SELFTEST || before == (uint32_t)FW_ST_DOCKED_SELFTEST) ? 0x06u : 0x15u;
            }
            break;
        case 0x02u:
            fw_sys_fsm(s, &st->knobs, FW_FE_ST_STOP, st->now_us);
            r = 0x06u;
            break;
        case 0x03u:                                               /* RAW {int16 q15}: bring-up drive, self-test state only */
            if (n == 2u && s->mode == (uint32_t)FW_ST_DOCKED_SELFTEST) {
                s->st_raw_q15 = (int16_t)((uint16_t)p[0] | (uint16_t)((uint16_t)p[1] << 8));
                s->st_raw_active = 1u;
                r = 0x06u;
            }
            break;
        case 0x04u:
            fw_sys_fsm(s, &st->knobs, FW_FE_DFU_REQ, st->now_us);
            r = s->mode == (uint32_t)FW_ST_DFU_PENDING ? 0x06u : 0x15u;
            break;
        default:
            break;
        }
    }
    if (reply != NULL && reply_cap >= 1u) {
        reply[0] = r;
        return 1u;
    }
    return 0u;
}

uint32_t fw_state_hash(const fw_state_t *st)
{
    return fw_crc32_update(0u, st, sizeof *st);
}
