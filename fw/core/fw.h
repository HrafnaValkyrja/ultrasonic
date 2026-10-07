/* fw/core/fw.h: core entry points and the frozen IF-FW-DSP ABI (FWSIM-R3, R9, R10).
 * Execution model (FWSIM-R3): ISRs only move data and set flags; every entry point below is a pure function of
 * (fw_state_t, args, injected time): it calls no HAL function, reads no register, keeps no static state.
 * ABI (FWSIM-R9, docs/sim/e2e-chain.yaml IF-FW-DSP): in = int32[128] ADF1 DR words (24-bit left-aligned, 200.02 kS/s,
 * one hop = 0.640 ms); out = uint16 TIM1 CCR1 values, 128 per hop at ARR 200 (256 at ARR 100, 512 at ARR 50);
 * V_diff/Vdd = 2*CCR/ARR - 1; leg B (CH3) = ARR - CCR1 is written by the port, the ABI carries one value.
 * Firmware output hop k aligns with reference hop k-1 (frame completion, e2e F9). Changing anything here bumps FW_ABI_VERSION
 * and must pass sim/e2e selftest fw_abi.*. */
#ifndef FW_CORE_FW_H
#define FW_CORE_FW_H
#include <stddef.h>
#include <stdint.h>
#include "dsp.h"
#include "idle.h"
#include "knobs.h"
#include "modes.h"
#include "variant_config.h"

#define FW_ABI_VERSION 1u
#define FW_HOP_N 128u                         /* input samples per hop */
#define FW_IDLE_LOOKBACK 12u                  /* hops (7.7 ms) the algorithm trails the idle detector when idle_enable = 1 */
#define FW_CCR_MAX_PER_HOP (FW_HOP_N * 4u)    /* ARR 50 (800 kHz): FWSIM-R61 sizes buffers for it */
#define FW_N_BANDS 28u
#define FW_DSP_OUT_N 8u                       /* 12.5 kS/s output samples per hop */
#define FW_HOP_US_X1000 639930u               /* 128 / 200.02 kS/s in ns (shared-params hop_ms 0.63993) */

typedef struct {                              /* FWSIM-R10 taps, one set per hop */
    float dsp_out[FW_DSP_OUT_N];              /* DSP output @12.5 kS/s, full scale 1.0 */
    float band_energy[FW_N_BANDS];
    float floor[FW_N_BANDS];
    float pre_q_true_peak;                    /* true peak of the pre-quantiser x16-interpolated stream */
    float shaper_norm[3];                     /* |e1|, |e2|, |e3| noise-shaper state */
    uint32_t squelch_state;                   /* 1 = squelched */
    uint32_t cycles_hop;                      /* filled by the caller (DWT), never by core */
    uint32_t n_ccr;                           /* CCR words written */
    uint32_t clamp_hits;                      /* FWSIM-R64 clamp engagements this hop (0 in normal listening) */
} fw_taps_t;

typedef enum {
    FW_EV_NONE = 0,
    FW_EV_BUTTON_SHORT,
    FW_EV_BUTTON_LONG,
    FW_EV_VBUS_ON,
    FW_EV_VBUS_OFF,
    FW_EV_CHG_INT,
    FW_EV_MIC_FAULT,
    FW_EV_KNOBS_DEFAULTED,                    /* knob store empty or bad (FWSIM-R6) */
    FW_EV_KNOBS_CLAMPED,                      /* stored knobs outside today's ranges were clamped */
    FW_EV_BTN_EDGE,                           /* raw BTN (PA0) level change, arg = level (debounced in core, FWSIM-R29) */
    FW_EV_BREAK,                              /* TIM1 break latched by the MDF1 out-of-limit detector (FWSIM-R65) */
    FW_EV_QUIET,                              /* idle detector: nothing to hear -> IDLE */
    FW_EV_WAKE,                               /* idle detector: activity -> back to the mode before IDLE */
    FW_EV_USB_ENUMERATED,                     /* USB configured: charger ILIM may leave 100 mA (FWSIM-R20) */
    FW_EV_COUNT
} fw_event_id_t;

typedef struct {
    uint64_t now_us;          /* last injected time */
    uint64_t boot_us;
    uint64_t hop_count;
    fw_knobs_t knobs;
    uint32_t abi;             /* FW_ABI_VERSION */
    uint32_t arr;             /* from knobs.pwm_khz */
    uint32_t amp_max_ppm;     /* FWSIM-R64 bound in use */
    uint32_t squelched;       /* 1 until power_on_hold_ms elapsed (e2e F4) */
    uint32_t vbus;            /* docked: output disabled unless exemption (ECR-0009) */
    uint32_t clamp_hits;
    uint32_t cdc_bytes;
    uint32_t last_event;
    int32_t last_arg;
    uint32_t event_count[FW_EV_COUNT];
    fw_idle_t idle;           /* idle-listening wake detector (spec C9) */
    float lb[FW_IDLE_LOOKBACK][FW_HOP_N];   /* look-back: the algorithm's input delayed by FW_IDLE_LOOKBACK hops */
    float lb_out[FW_HOP_N];
    uint32_t lb_head;
    fw_sys_t sys;             /* modes, gestures, docked interlock, self-test, break latch (FWSIM-R18, R19, R29, R65) */
    int32_t vol_offset_cdb;   /* volume applied to the DSP gain */
    uint32_t usb_enumerated;
    fw_dsp_t dsp;             /* DSP chain state (FWSIM-R13): front end, algorithm, interpolator, limiter, shaper */
} fw_state_t;

void fw_init(fw_state_t *st, const fw_knobs_t *knobs, uint64_t now_us);
/* One hop. Writes n = 128 * 200 / ARR CCR words if ccr_cap >= n and returns n; else writes nothing and returns 0.
 * taps may be NULL. in = D1 front end: 128 ADF1 words at 200 kS/s. Output squelched (CCR = ARR/2) while the power-on hold runs
 * (released by fw_poll with injected time, e2e F4). */
size_t fw_hop(fw_state_t *st, const int32_t in[FW_HOP_N], uint16_t *ccr, size_t ccr_cap, fw_taps_t *taps);
/* Same hop for the D2 front end (knob adf_front = 2): 256 ADF1 words at 400 kS/s (CIC /10), CPU half-band to 200 kS/s.
 * Additive entry point: fw_hop's ABI is unchanged (FW_ABI_VERSION 1). The port calls the one its ADF1 configuration feeds. */
size_t fw_hop_d2(fw_state_t *st, const int32_t in400[2u * FW_HOP_N], uint16_t *ccr, size_t ccr_cap, fw_taps_t *taps);
/* Load the unit's mic self-noise band energies (production / boot calibration); n = 28 (spec B) or 16 (slim B). 0 = ok. */
int fw_set_noise_cal(fw_state_t *st, const float *band_energy, uint32_t n);
void fw_poll(fw_state_t *st, uint64_t now_us);
void fw_event(fw_state_t *st, fw_event_id_t id, int32_t arg, uint64_t now_us);
/* CDC commands (minimal framing until the FWSIM-R57 codec): 0xA5, type, len, payload. Types: 0x01 ST_ARM {int16 amp_cdb, uint16 freq_hz},
 * 0x02 ST_STOP, 0x03 RAW {int16 q15 V_diff/Vdd: bring-up constant drive}, 0x04 DFU_REQ. Reply: 1 byte ACK 0x06 / NACK 0x15. Every drive these
 * paths produce goes through fw_ccr_from_amp (FWSIM-R64) and only in DOCKED_SELFTEST (ECR-0009 variant a). */
size_t fw_cdc_rx(fw_state_t *st, const uint8_t *buf, size_t len, uint8_t *reply, size_t reply_cap);
fw_outputs_t fw_outputs(const fw_state_t *st);
void fw_brk_clear_done(fw_state_t *st);   /* the app cleared TIM1 BIF as fw_outputs().brk_clear asked */
#if FW_VAR_DOCKED_OUTPUT_MAX
size_t fw_selftest_hop(fw_state_t *st, float y8[FW_DSP_OUT_N], const fw_ccr_bounds_t *b, uint16_t *ccr, uint32_t *hits);
#endif
uint32_t fw_state_hash(const fw_state_t *st);
#endif
