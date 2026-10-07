/* fw/core/dsp.h: the DSP chain behind fw_hop (FWSIM-R13, R14): front end (D1 words / D2 400 kS/s + half-band) -> algorithm
 * (B spec, B slim, A) -> x16 polyphase interpolation -> true-peak limiter at the ceiling -> squelch -> 3rd-order error-feedback
 * shaper + TPDF dither -> CCR through the FWSIM-R64 clamp (fw_ccr_from_amp).
 * Numeric reference: sim/dsp/pipeline.py algo_b / algo_a, sim/e2e/stages.py PwmShaper (float64). Alignment (e2e F9): firmware
 * 12.5 kS/s output sample n = reference sample n - 8 for B (both variants), n - 17 for A (causal 575-tap decimator).
 * Pure: state in fw_dsp_t only, no statics, no HAL. Every loop has a data-independent trip count per variant (fw/tools/cycles.py). */
#ifndef FW_CORE_DSP_H
#define FW_CORE_DSP_H
#include <stddef.h>
#include <stdint.h>

#include "dsp_tables.h"
#include "knobs.h"
#include "out_clamp.h"

#define FW_DSP_NFFT 256u
#define FW_DSP_NB_MAX 28u
#define FW_DSP_A_NC 575u                         /* algorithm-A decimating FIR length */
#define FW_DSP_A_HIST (FW_DSP_A_NC - 1u + 128u)
#define FW_DSP_HB_HIST (31u - 1u + 256u)

typedef enum { FW_ALGO_A = 1, FW_ALGO_B = 2 } fw_algo_t;

typedef struct {
    /* ---- configuration (fw_dsp_init, from knobs) */
    uint32_t algo, slim, nb, ramp_len, ramp_shift, transient, arr, reps, dither_on, hold_samples;
    uint32_t bin_lo, bin_hi;                      /* bins [bin_lo, bin_hi) fall inside a band */
    uint8_t band_of_bin[132];
    float a_up, om_up, a_dn, om_dn, gate_lin, margin_lin, gain_lin, a_att, a_rel, k_map, out_lo, f_lo, f_hi;
    float geo[FW_DSP_NB_MAX];                     /* geometric band centres (centroid of an empty band) */
    float noise[FW_DSP_NB_MAX];                   /* mic self-noise band energy (calibration) */
    float lim_c, lim_rel, sq_thr2, sq_a, step, inv_step, h1, h2;   /* h3 = -1 */
    /* ---- front end + algorithm B */
    float pcm[FW_DSP_NFFT];                       /* last 256 PCM samples, DR-word units (2^31 = FS) */
    uint32_t hops, frames, ramp_pos;
    float E[FW_DSP_NB_MAX], floor_[FW_DSP_NB_MAX], env[FW_DSP_NB_MAX], amp_prev[FW_DSP_NB_MAX], amp_new[FW_DSP_NB_MAX];
    uint32_t inc_prev[FW_DSP_NB_MAX], inc_new[FW_DSP_NB_MAX], phase[FW_DSP_NB_MAX];
    /* ---- algorithm A */
    float a_hist[FW_DSP_A_HIST];
    float a_z1, a_z2, a_sm, a_floor, a_gate_lin, a_up_s, a_dn_s;
    uint32_t a_lo_ph, a_lo_inc, a_floor_init;
    /* ---- D2 half-band */
    float hb_hist[FW_DSP_HB_HIST];
    /* ---- output stage */
    float ihist[FW_INTERP_TPP];
    float lim_g, e1, e2, e3, sq_env;
    uint32_t dither, sq_quiet;
} fw_dsp_t;

void fw_dsp_init(fw_dsp_t *d, const fw_knobs_t *k, uint32_t arr);
int fw_dsp_set_noise(fw_dsp_t *d, const float *band_energy, uint32_t n);   /* unit calibration; n must equal the band count */
/* D2 front end: 256 words at 400 kS/s -> 128 PCM (DR-word units) */
void fw_dsp_halfband(fw_dsp_t *d, const int32_t in400[256], float pcm[128]);
/* algorithm: 128 PCM -> 8 samples at 12.5 kS/s (full scale 1.0); band_energy / floor taps (may be NULL) */
void fw_dsp_algo(fw_dsp_t *d, const float pcm[128], float y8[8], float *band_energy, float *floor_tap);
typedef struct {
    float true_peak;          /* max |x| of the pre-quantiser x16 stream this hop (after limiter and squelch) */
    float shaper_norm[3];     /* |e1|, |e2|, |e3| at the end of the hop */
    uint32_t squelched;       /* squelch state at the end of the hop */
    uint32_t squelched_periods;
    uint32_t clamp_hits;
} fw_out_info_t;
/* output stage: 8 samples at 12.5 kS/s -> 128 * reps CCR words, every one through fw_ccr_from_amp (FWSIM-R64); returns the count.
 * force_squelch: power-on hold (e2e F4) or any other mute: output exactly ARR/2, shaper state zeroed, dither off (F2). */
size_t fw_dsp_out(fw_dsp_t *d, const float y8[8], uint32_t force_squelch, const fw_ccr_bounds_t *b, uint16_t *ccr, fw_out_info_t *info);
#endif
