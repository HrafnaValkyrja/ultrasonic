/* fw/core/dsp_math.h: the few transcendental functions the DSP needs at init and per frame, as polynomials (determinism rules:
 * no libm transcendentals in core; the same arithmetic on host and ARM with -ffp-contract=off). Accuracy (host check
 * test_dsp_math): log2 abs err <= 2e-7 on [1e-30, 1e30]; exp2 rel err <= 3e-7 on [-60, 60]; om_exp rel err <= 1e-6. */
#ifndef FW_CORE_DSP_MATH_H
#define FW_CORE_DSP_MATH_H
#include <stdint.h>

float fw_log2f(float x);          /* x > 0 and normal; else returns -126 */
float fw_exp2f(float x);          /* clamps x to [-126, 127] */
float fw_db20_to_lin(float db);   /* 10^(db/20) */
float fw_om_exp(float x);         /* 1 - exp(-x), x >= 0, accurate for small x (one-pole coefficients) */
extern const float fw_sin_tab[1025];
/* sin(2 pi ph / 2^32) from the 1024-entry table + linear interpolation (inline: called 8 x bands per hop) */
static inline float fw_sin_turns(uint32_t ph)
{
    uint32_t i = ph >> 22;
    float f = (float)(ph & 0x3FFFFFu) * 0x1p-22f;
    float a = fw_sin_tab[i];
    return a + f * (fw_sin_tab[i + 1u] - a);
}
/* macro form of fw_sin_turns for hot loops (same arithmetic; instructions attributed to the calling line by fw/tools/cycles.py) */
#define FW_SIN_TURNS(ph) (fw_sin_tab[(ph) >> 22] + (float)((ph) & 0x3FFFFFu) * 0x1p-22f * (fw_sin_tab[((ph) >> 22) + 1u] - fw_sin_tab[(ph) >> 22]))
#endif
