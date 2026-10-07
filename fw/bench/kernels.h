/* fw/bench/kernels.h - V4 cycle-budget kernels (docs/research/drastic/V4-cycles.yaml).
 *
 * Minimal C versions of the per-hop inner loops of the spec s5 DSP (algorithms A and B) and
 * the shared output path (x16 interpolation -> true-peak limiter -> 3rd-order shaper -> CCR).
 * They mirror sim/dsp/pipeline.py and sim/e2e/stages.py PwmShaper. They are NOT the firmware:
 * no peripherals, no state machine; just the arithmetic the CPU must do per 0.64 ms hop.
 *
 * Rates (spec D14, A3-u575-plan.md s2): PCM 200.02 kS/s from ADF1 (D1 = hardware decimation),
 * hop = 128 PCM samples (0.640 ms, 1562.6 hops/s), output 12.5 kS/s (8 samples/hop),
 * PWM 200 kHz (128 CCR values/hop).
 */
#ifndef V4_KERNELS_H
#define V4_KERNELS_H
#include <stdint.h>

#define NFFT      256
#define NC        128            /* complex FFT size for the 256-pt real FFT                    */
#define HOP       128
#define OUT_HOP   8              /* 12.5 kS/s samples per hop                                     */
#define UP        16             /* x16 interpolation to the 200 kHz PWM rate                     */
#ifndef NB
#define NB        32             /* bands in algorithm B (spec ~32; pipeline.py default 28)       */
#endif
#define BIN_LO    26             /* 26 * 781.25 = 20.3 kHz                                         */
#define NBIN      84             /* bins 26..109 = 20.3..85.2 kHz                                  */
#ifndef TPP
#define TPP       8              /* interpolator taps per phase (prototype = 16*TPP taps)         */
#endif
#define A_N1      16             /* algorithm A stage-1 decimator taps (/4, 200k -> 50k)          */
#define A_N2      40             /* algorithm A stage-2 decimator taps (/4, 50k -> 12.5k)         */
#define HB_N      8              /* half-band (D2 fallback) symmetric non-zero pairs (31 taps)    */
#define SINTAB    1024

typedef struct { float re, im; } cpx;

/* shared input */
void in_window(const int32_t *adf, const float *win, float *buf);        /* 256 words -> windowed float */
void halfband_d2(const float *x400, float *y200, int n_out);             /* D2 fallback only            */

/* 256-point real FFT = 128-point complex radix-2 DIT + real split */
void bitrev128(cpx *x, const uint8_t *pairs, int npairs);
void cfft128(cpx *x, const cpx *tw);
void rsplit256(cpx *x, const cpx *twr);

/* algorithm B */
typedef struct {
    float E[NB], C[NB], floor_[NB], env[NB], amp[NB];   /* amp = envelope at the previous hop */
    uint32_t inc[NB], incn[NB], ph[NB];                  /* phase increment prev/new, phase    */
    float a_up, a_dn, gate, gain, a_att, a_rel, ln_lo, k_map, out_lo_inc;
} bstate;
void b_bands(const cpx *X, const float *eq2, const float *fbin, const uint8_t *band, bstate *s);
void b_update(bstate *s);
void b_synth(bstate *s, const float *sintab, float *y8);

/* algorithm A */
typedef struct {
    uint32_t ph, inc;
    float d1[A_N1 - 1 + HOP];          /* stage-1 history + this hop's mixed samples            */
    float d2[A_N2 - 1 + HOP / 4];      /* stage-2 history + this hop's 50 kS/s samples          */
    float bq[5], z1, z2, sm, floor_, gate, a_sm;
} astate;
void a_mix(const int32_t *adf, const float *sintab, astate *s);
void a_decim(const float *h1, const float *h2, astate *s, float *y8);
void a_post(astate *s, float *y8);

/* shared output: interpolation + limiter + shaper */
typedef struct {
    float hist[TPP + OUT_HOP];          /* 12.5 kS/s history for the polyphase interpolator      */
    float g, c, a_rel, e1, e2, e3, h1, h2, h3, step, inv_step, half_levels, sq_env, sq_a;
    uint32_t lcg;
} ostate;
void out_hop(const float *y8, const float *hpoly, ostate *s, uint16_t *ccr);

/* ---- fixed-point (q15 + DSP-extension SMLAD) variants: the B3 lever (kernels_q15.c) ---- */
typedef struct {
    uint32_t ph, inc;
    int16_t d1[A_N1 - 1 + HOP + 1];    /* +1 keeps the hop part 4-byte aligned (A_N1-1 is odd) */
    int16_t d2[A_N2 - 1 + HOP / 4 + 1];
} aq_state;
void a_mix_q15(const int32_t *adf, const int16_t *sintab, aq_state *s);
void a_decim_q15(const int16_t *h1, const int16_t *h2, aq_state *s, int16_t *y8);
typedef struct {
    int16_t hist[TPP + OUT_HOP];
    int32_t g, c, a_rel, e1, e2, e3, h1, h2, h3;   /* g, c: q15; h: q12 shaper coefficients */
    uint32_t lcg;
} oq_state;
void out_hop_q15(const int16_t *y8, const int16_t *hpoly, oq_state *s, uint16_t *ccr);

#endif
