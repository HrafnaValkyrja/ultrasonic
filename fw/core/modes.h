/* fw/core/modes.h: mode state machine (FWSIM-R18, table fw/gen/fsm_table.h from fw/spec/fsm.yaml), button gesture recogniser (FWSIM-R29,
 * knob table gesture_option), VBUS debounce + docked interlock (FWSIM-R19, ECR-0009), self-test exemption timing, fault-break latch
 * bookkeeping (FWSIM-R65) and the desired pin/peripheral state fw_outputs() the app applies. Pure: state + args + injected time. */
#ifndef FW_CORE_MODES_H
#define FW_CORE_MODES_H
#include <stdint.h>

#include "fsm_table.h"
#include "knobs.h"

#define FW_VBUS_DEBOUNCE_US 20000u        /* PA1 stable 20 ms before VBUS counts as present / absent (raw high disables output at once) */

typedef struct {
    uint32_t mode, prev_mode, steps, ignored, guard_blocked;
    int32_t vol_idx;
    uint32_t vbus_raw, vbus;               /* raw PA1 edge state, debounced state */
    uint64_t vbus_edge_us;
    uint32_t btn_raw, btn;                 /* raw edge level, debounced level */
    uint64_t btn_raw_us, press_us, release_us, last_rep_us;
    uint32_t taps, hold1, hold2, stuck, consumed, bounces;
    uint32_t st_active;                    /* self-test drive running (variant a) */
    uint64_t st_start_us;
    int32_t st_amp_cdb;
    uint32_t st_freq_hz, st_ph, st_raw_active;
    int32_t st_raw_q15;
    uint32_t brk_latched, brk_events, brk_clear_req;
    uint64_t brk_us;
    uint32_t gestures[FW_RG_COUNT];
} fw_sys_t;

typedef struct {
    uint8_t output_enable;   /* the DSP / self-test may drive the bridge (else CCR = ARR/2 and the bridge stops) */
    uint8_t bridge_run;      /* TIM1 MOE wanted */
    uint8_t mic_power;       /* PA5 */
    uint8_t pins_parked;     /* PB3/PB4 analog, no pull */
    uint8_t brk_armed;       /* FWSIM-R65 MDF1 break armed (always while the bridge runs) */
    uint8_t brk_clear;       /* request: clear the latched TIM1 break (BIF) */
    uint8_t selftest;        /* drive comes from the self-test generator */
    uint8_t pad;
} fw_outputs_t;

void fw_sys_init(fw_sys_t *s, const fw_knobs_t *k, uint64_t now_us);
void fw_sys_poll(fw_sys_t *s, const fw_knobs_t *k, uint64_t now_us);     /* debounce, gesture timers, self-test timeout, break cool-down */
void fw_sys_fsm(fw_sys_t *s, const fw_knobs_t *k, uint32_t ev, uint64_t now_us);   /* one FSM event (fw_fsm_ev_t) */
void fw_sys_btn_edge(fw_sys_t *s, uint32_t level, uint64_t now_us);
void fw_sys_vbus_edge(fw_sys_t *s, uint32_t level, uint64_t now_us);
fw_outputs_t fw_sys_outputs(const fw_sys_t *s);
int32_t fw_sys_volume_offset_cdb(const fw_sys_t *s, const fw_knobs_t *k);
const char *fw_mode_name(uint32_t m);
#endif
