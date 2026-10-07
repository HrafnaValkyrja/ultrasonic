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
/* a = V_diff/Vdd; NaN -> centre. Inline (called once per PWM period, 128-512 x per hop); still the only CCR writer in core. */
static inline uint16_t fw_ccr_from_amp(float a, const fw_ccr_bounds_t *b, uint32_t *clamp_hits)
{
    float v = (a + 1.0f) * 0.5f * (float)b->arr;
    if (!(v == v))                       /* NaN */
        v = 0.5f * (float)b->arr;
    if (v < (float)b->lo) {
        v = (float)b->lo;
        (*clamp_hits)++;
    } else if (v > (float)b->hi) {
        v = (float)b->hi;
        (*clamp_hits)++;
    }
    uint16_t c = (uint16_t)(v + 0.5f);
    if (c > b->hi)
        c = b->hi;
    if (c < b->lo)
        c = b->lo;
    return c;
}
/* integer path for the shaper: level qi (V_diff/Vdd = 2 qi / ARR) -> CCR = qi + ARR/2, bounded exactly like fw_ccr_from_amp(2 qi / ARR)
 * (test_clamp_level_matches_amp). Statement macro so hot loops expand it on one source line (fw/tools/cycles.py attribution);
 * in-range test is one unsigned compare, the clamp itself is the rare path. */
#define FW_CCR_LEVEL_STORE(dst, qi, b, hits)                                                                             \
    do {                                                                                                                 \
        int32_t c_ = (qi) + (int32_t)((b)->arr / 2u);                                                                    \
        if ((uint32_t)(c_ - (int32_t)(b)->lo) > (uint32_t)((b)->hi - (b)->lo)) {                                         \
            c_ = c_ < (int32_t)(b)->lo ? (int32_t)(b)->lo : (int32_t)(b)->hi;                                            \
            (hits)++;                                                                                                    \
        }                                                                                                                \
        (dst) = (uint16_t)c_;                                                                                            \
    } while (0)
static inline uint16_t fw_ccr_from_level(int32_t qi, const fw_ccr_bounds_t *b, uint32_t *clamp_hits)
{
    uint16_t c;
    FW_CCR_LEVEL_STORE(c, qi, b, *clamp_hits);
    return c;
}
float fw_db_to_amp(int32_t cdb);                                   /* table lookup, 0.1 dB steps, -80..0 dB; > 0 dB -> 1 */
/* PWM timing per clock plan (FWSIM-R25, R46). TIM1 is centre-aligned on HCLK: f_pwm = HCLK / (2 ARR). Every plan has HCLK = B x 400 kHz
 * exactly (B integer: P80 200, P160 400, P64 160, P48 120, P112 280, P104 260, P72 180, P52 130), and fs_pcm = HCLK / 400, so the PWM rate
 * is an exact integer multiple R of the PCM rate when ARR = B / R (R = pwm_khz / 200). A rate is legal at a plan only when B is divisible by
 * R and ARR >= HC_ARR_MIN (amplitude resolution, spec D6 MP-01); otherwise the rate is halved until it is (nearest lower legal rate:
 * P52 800 -> 400 kHz, P64 800 -> 400, P48 800 -> 400). *eff_khz receives the rate actually used. */
uint32_t fw_plan_hclk_hz(uint32_t plan);                                    /* exact plan HCLK (= hal_clock_hclk_hz after set_plan) */
uint16_t fw_arr_for_khz(int32_t pwm_khz, uint32_t plan, int32_t *eff_khz);
uint32_t fw_dead_ticks(uint32_t ticks_p80, uint32_t plan);                 /* knob ticks are 12.5 ns P80 ticks: never shorter at a faster plan */
#endif
