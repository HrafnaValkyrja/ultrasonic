/* fw/core/out_clamp.h: the last stage before TIM1: amplitude -> CCR with the FWSIM-R64 output CURRENT hard clamp.
 * Every output path (music, self-test tones, calibration, CDC bring-up commands) produces its CCR stream through
 * fw_ccr_from_amp(); there is no other CCR writer in core. Bound: |2*CCR/ARR - 1| <= amp_max, with amp_max =
 * min(FW_VAR_AMP_MAX_PPM (compile time, fw/variants.yaml), knob out_i_peak_ma) and the bound applied in the integer CCR domain
 * (exact, no rounding slack). The -12 dBFS listening ceiling (DSP true-peak limiter, FWSIM-R14/R15) sits below it. */
#ifndef FW_CORE_OUT_CLAMP_H
#define FW_CORE_OUT_CLAMP_H
#include <stdint.h>
#include "knobs.h"

typedef struct {
    uint16_t arr;
    uint16_t lo, hi;      /* allowed CCR range, centre = arr/2 */
    uint32_t amp_ppm;     /* the amplitude bound it was built from */
} fw_ccr_bounds_t;

uint32_t fw_amp_ppm_for_ma(int32_t i_ma);                          /* i * R_load / Vdd in ppm (fw/variants.yaml bridge) */
uint32_t fw_out_amp_max_ppm(const fw_knobs_t *k);                  /* min(compile-time clamp, knob) */
fw_ccr_bounds_t fw_ccr_bounds(uint16_t arr, uint32_t amp_ppm);     /* amp_ppm is capped at FW_VAR_AMP_MAX_PPM here too */
uint16_t fw_ccr_from_amp(float a, const fw_ccr_bounds_t *b, uint32_t *clamp_hits);   /* a = V_diff/Vdd; NaN -> centre */
float fw_db_to_amp(int32_t cdb);                                   /* table lookup, 0.1 dB steps, -80..0 dB; > 0 dB -> 1 */
uint16_t fw_arr_for_khz(int32_t pwm_khz);                          /* 200 -> 200, 400 -> 100, 800 -> 50 (else 200) */
#endif
