#include "modes.h"

#include <string.h>

#include "variant_config.h"

static const fw_fsm_cell_t fsm[FW_ST_COUNT][FW_FE_COUNT] = FW_FSM_TABLE_INIT;
static const fw_gesture_map_t gmaps[3] = FW_GESTURE_MAPS_INIT;
static const char *const mode_names[FW_ST_COUNT] = FW_FSM_STATE_NAMES;

const char *fw_mode_name(uint32_t m) { return m < (uint32_t)FW_ST_COUNT ? mode_names[m] : "?"; }

static uint32_t default_mode(const fw_knobs_t *k) { return k->transient_only ? (uint32_t)FW_ST_TRANSIENT : (uint32_t)FW_ST_FULL; }

void fw_sys_init(fw_sys_t *s, const fw_knobs_t *k, uint64_t now_us)
{
    memset(s, 0, sizeof *s);
    s->mode = default_mode(k);            /* a reset comes back on at the power-on defaults (D3) */
    s->prev_mode = s->mode;
    s->vol_idx = k->volume_steps / 2;
    s->vbus_edge_us = now_us;
    s->btn_raw_us = now_us;
}

static uint32_t exemption_allowed(const fw_sys_t *s, const fw_knobs_t *k)
{
#if FW_VAR_DOCKED_OUTPUT_MAX
    return k->docked_output != 0 && s->vbus && s->vbus_raw;   /* ECR-0009 variant (a): armed by knob + docked */
#else
    (void)s;
    (void)k;
    return 0u;                                                  /* variant (b): no exemption path exists */
#endif
}

void fw_sys_fsm(fw_sys_t *s, const fw_knobs_t *k, uint32_t ev, uint64_t now_us)
{
    if (ev >= (uint32_t)FW_FE_COUNT || s->mode >= (uint32_t)FW_ST_COUNT)
        return;
    const fw_fsm_cell_t *c = &fsm[s->mode][ev];
    s->steps++;
    if (!c->valid) {
        s->ignored++;
        return;
    }
    if (c->guard == FW_GD_EXEMPTION && !exemption_allowed(s, k)) {
        s->guard_blocked++;
        return;
    }
    if (c->guard == FW_GD_COOLDOWN && (!s->brk_latched || now_us - s->brk_us < (uint64_t)k->brk_cooldown_ms * 1000u)) {
        s->guard_blocked++;
        return;
    }
    uint32_t next = c->state;
    switch (c->kind) {
    case FW_TG_SAME: next = s->mode; break;
    case FW_TG_PREV: next = s->prev_mode; break;
    case FW_TG_PREV_TOGGLED: next = s->prev_mode == (uint32_t)FW_ST_FULL ? (uint32_t)FW_ST_TRANSIENT : (uint32_t)FW_ST_FULL; break;
    case FW_TG_DEFAULT: next = default_mode(k); break;
    default: break;
    }
    switch (c->action) {
    case FW_AC_VOL_STEP:
        s->vol_idx = s->vol_idx + 1 >= k->volume_steps ? 0 : s->vol_idx + 1;     /* wraps (sub-ui option B) */
        break;
    case FW_AC_LOAD_DEFAULTS:
        s->vol_idx = k->volume_steps / 2;
        break;
    case FW_AC_SAVE_PREV:
        s->prev_mode = s->mode;
        break;
    case FW_AC_ST_START:
        s->st_active = 1u;
        s->st_start_us = now_us;
        break;
    case FW_AC_ST_END:
        s->st_active = 0u;
        s->st_raw_active = 0u;
        break;
    default:
        break;
    }
    if (s->mode == (uint32_t)FW_ST_SAFE && next != (uint32_t)FW_ST_SAFE) {
        s->brk_latched = 0u;
        s->brk_clear_req = 1u;                 /* the app clears TIM1 BIF once, then this flag */
    }
    s->mode = next;
}

static void gesture(fw_sys_t *s, const fw_knobs_t *k, uint32_t g, uint64_t now_us)
{
    s->gestures[g]++;
    int32_t ev = gmaps[(k->gesture_option >= 1 && k->gesture_option <= 3) ? k->gesture_option - 1 : 1].ev[g];
    if (s->mode == (uint32_t)FW_ST_OFF) {        /* any press in Off = On at defaults */
        if (g == FW_RG_SHORT || g == FW_RG_DOUBLE)
            fw_sys_fsm(s, k, FW_FE_G_ANY, now_us);
        return;
    }
    if (ev >= 0)
        fw_sys_fsm(s, k, (uint32_t)ev, now_us);
}

void fw_sys_btn_edge(fw_sys_t *s, uint32_t level, uint64_t now_us)
{
    level = level ? 1u : 0u;
    if (level != s->btn_raw)
        s->bounces++;
    s->btn_raw = level;
    s->btn_raw_us = now_us;                  /* stable after debounce_ms without another edge (fw_sys_poll) */
}

void fw_sys_vbus_edge(fw_sys_t *s, uint32_t level, uint64_t now_us)
{
    s->vbus_raw = level ? 1u : 0u;
    s->vbus_edge_us = now_us;
}

void fw_sys_poll(fw_sys_t *s, const fw_knobs_t *k, uint64_t now_us)
{
    const fw_gesture_map_t *gm = &gmaps[(k->gesture_option >= 1 && k->gesture_option <= 3) ? k->gesture_option - 1 : 1];
    /* VBUS: debounced with a 20 ms stable time; output already follows the raw level (fw_sys_outputs) */
    if (s->vbus_raw != s->vbus && now_us - s->vbus_edge_us >= FW_VBUS_DEBOUNCE_US) {
        s->vbus = s->vbus_raw;
        fw_sys_fsm(s, k, s->vbus ? FW_FE_VBUS_ON : FW_FE_VBUS_OFF, now_us);
    }
    /* button: debounce, then gestures */
    if (s->btn_raw != s->btn && now_us - s->btn_raw_us >= (uint64_t)k->debounce_ms * 1000u) {
        s->btn = s->btn_raw;
        uint64_t t = s->btn_raw_us;          /* the edge time, not the poll time */
        if (s->btn) {
            s->press_us = t;
            s->hold1 = s->hold2 = 0u;
            s->last_rep_us = t;
        } else {
            uint32_t was_hold = s->hold1 || s->hold2 || s->stuck;
            s->stuck = 0u;
            if (!was_hold) {
                if (gm->double_used && s->mode != (uint32_t)FW_ST_OFF) {
                    if (s->taps == 1u) {
                        s->taps = 0u;
                        gesture(s, k, FW_RG_DOUBLE, now_us);
                    } else {
                        s->taps = 1u;
                        s->release_us = t;
                    }
                } else {
                    gesture(s, k, FW_RG_SHORT, now_us);
                }
            }
        }
    }
    if (s->taps == 1u && !s->btn && now_us - s->release_us >= (uint64_t)k->double_window_ms * 1000u) {
        s->taps = 0u;
        gesture(s, k, FW_RG_SHORT, now_us);
    }
    if (s->btn && !s->stuck) {
        uint64_t held = now_us - s->press_us;
        if (held >= (uint64_t)k->stuck_button_s * 1000000u) {
            s->stuck = 1u;                    /* FWSIM-R29: stuck switch (+1.36 mA): stop acting on it until released */
            s->taps = 0u;
        } else {
            if (!s->hold1 && held >= (uint64_t)k->hold_ms * 1000u) {
                s->hold1 = 1u;
                s->taps = 0u;
                s->last_rep_us = now_us;
                gesture(s, k, FW_RG_HOLD1, now_us);
            } else if (s->hold1 && gm->hold1_repeats && now_us - s->last_rep_us >= (uint64_t)k->hold_ms * 1000u) {
                s->last_rep_us = now_us;
                gesture(s, k, FW_RG_HOLD1, now_us);
            }
            if (!s->hold2 && held >= (uint64_t)k->hold2_ms * 1000u) {
                s->hold2 = 1u;
                gesture(s, k, FW_RG_HOLD2, now_us);
            }
        }
    }
    /* self-test maximum duration (FWSIM-R19 variant a) */
    if (s->mode == (uint32_t)FW_ST_DOCKED_SELFTEST && now_us - s->st_start_us >= (uint64_t)k->selftest_max_s * 1000000u)
        fw_sys_fsm(s, k, FW_FE_ST_TIMEOUT, now_us);
    /* break cool-down (FWSIM-R65) */
    if (s->mode == (uint32_t)FW_ST_SAFE && s->brk_latched)
        fw_sys_fsm(s, k, FW_FE_FAULT_CLEAR, now_us);
}

fw_outputs_t fw_sys_outputs(const fw_sys_t *s)
{
    fw_outputs_t o;
    memset(&o, 0, sizeof o);
    uint32_t m = s->mode;
    uint32_t listening = m == (uint32_t)FW_ST_FULL || m == (uint32_t)FW_ST_TRANSIENT;
    /* docked interlock: any raw VBUS level stops normal output at once; it resumes only after VBUS is stably absent */
    o.output_enable = (uint8_t)((listening && !s->vbus_raw && !s->vbus) || (m == (uint32_t)FW_ST_DOCKED_SELFTEST && s->st_active && s->vbus && s->vbus_raw));
    o.selftest = (uint8_t)(m == (uint32_t)FW_ST_DOCKED_SELFTEST && o.output_enable);
    o.bridge_run = o.output_enable;
    o.mic_power = (uint8_t)(listening || m == (uint32_t)FW_ST_IDLE || m == (uint32_t)FW_ST_DOCKED_SELFTEST);
    o.pins_parked = (uint8_t)!o.bridge_run;
    o.brk_armed = o.bridge_run;
    o.brk_clear = (uint8_t)s->brk_clear_req;
    return o;
}

int32_t fw_sys_volume_offset_cdb(const fw_sys_t *s, const fw_knobs_t *k)
{
    return (s->vol_idx - k->volume_steps / 2) * k->volume_step_cdb;
}
