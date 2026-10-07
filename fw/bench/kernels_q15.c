/* fw/bench/kernels_q15.c - fixed-point variants of the per-sample-heavy kernels (algorithm A front
 * end and the shared output path), using the M33 DSP extension (SMLAD: two 16x16 MACs per cycle).
 * This is the lever for the 24 MHz (B3) budget; same structure and tap counts as kernels.c.
 * Fixed-point scaling is sketched, not tuned (no overflow/rounding analysis yet).
 */
#include "kernels.h"
#include <arm_acle.h>
#include <string.h>

#define NOINL __attribute__((noinline))

static inline int32_t ld2(const int16_t *p) { int32_t v; memcpy(&v, p, 4); return v; }  /* LDR (unaligned ok on M33) */

NOINL void a_mix_q15(const int32_t *adf, const int16_t *sintab, aq_state *s)
{
    uint32_t ph = s->ph, inc = s->inc;
    int16_t *d = &s->d1[A_N1];          /* aligned start (A_N1 - 1 history + 1 pad) */
    for (int i = 0; i < HOP; i++) {
        ph += inc;
        d[i] = (int16_t)((adf[i] >> 16) * sintab[ph >> 22] >> 15);   /* SMULBB-class multiply */
    }
    s->ph = ph;
}

NOINL void a_decim_q15(const int16_t *h1, const int16_t *h2, aq_state *s, int16_t *y8)
{
    for (int m = 0; m < HOP / 4; m++) {
        const int16_t *x = &s->d1[1 + 4 * m];
        int32_t acc = 0;
        _Pragma("GCC unroll 8")
        for (int t = 0; t < A_N1; t += 2) acc = __smlad(ld2(&h1[t]), ld2(&x[t]), acc);
        s->d2[A_N2 + m] = (int16_t)(acc >> 15);
    }
    for (int n = 0; n < OUT_HOP; n++) {
        const int16_t *x = &s->d2[1 + 4 * n];
        int32_t acc = 0;
        _Pragma("GCC unroll 20")
        for (int t = 0; t < A_N2; t += 2) acc = __smlad(ld2(&h2[t]), ld2(&x[t]), acc);
        y8[n] = (int16_t)(acc >> 15);
    }
    _Pragma("GCC unroll 1")
    for (int t = 0; t < A_N1; t++) s->d1[t] = s->d1[HOP + t];
    _Pragma("GCC unroll 1")
    for (int t = 0; t < A_N2; t++) s->d2[t] = s->d2[HOP / 4 + t];
}

/* x16 polyphase interpolation (SMLAD), true-peak limiter (one SDIV per 12.5 kS/s sample),
 * 3rd-order error-feedback shaper in integer (q12 coefficients), TPDF dither, 201 levels. */
NOINL void out_hop_q15(const int16_t *y8, const int16_t *hpoly, oq_state *s, uint16_t *ccr)
{
    int32_t xi[UP];
    for (int n = 0; n < OUT_HOP; n++) s->hist[TPP - 1 + n] = y8[n];
    int32_t e1 = s->e1, e2 = s->e2, e3 = s->e3, g = s->g;
    uint32_t lcg = s->lcg;
    for (int n = 0; n < OUT_HOP; n++) {
        const int16_t *h = &s->hist[n];
        int32_t peak = s->c;
        for (int p = 0; p < UP; p++) {
            const int16_t *c = &hpoly[p * TPP];
            int32_t acc = 0;
            _Pragma("GCC unroll 8")
            for (int t = 0; t < TPP; t += 2) acc = __smlad(ld2(&c[t]), ld2(&h[t]), acc);
            acc >>= 15;
            xi[p] = acc;
            int32_t a = acc < 0 ? -acc : acc;
            peak = a > peak ? a : peak;
        }
        int32_t need = (s->c << 15) / peak;                    /* SDIV, q15, <= 1.0         */
        g += (s->a_rel * (32768 - g)) >> 15;
        g = g < need ? g : need;
        for (int p = 0; p < UP; p++) {
            int32_t v = (xi[p] * g) >> 15;                      /* sample in units of 1/2^15 FS */
            v += (s->h1 * e1 + s->h2 * e2 + s->h3 * e3) >> 12;
            lcg = lcg * 1664525u + 1013904223u;
            int32_t d = (int32_t)(lcg >> 24) - (int32_t)((lcg >> 16) & 0xFF);   /* TPDF from one draw */
            int32_t q = (v * 100 + (d << 7) + 16384) >> 15;     /* 200 steps across +-FS      */
            q = q > 100 ? 100 : (q < -100 ? -100 : q);
            int32_t e = q * 328 - v;                            /* q*FS/100 in 2^15 units (328 ~ 32768/100) */
            e3 = e2; e2 = e1; e1 = e;
            ccr[n * UP + p] = (uint16_t)(q + 100);
        }
    }
    _Pragma("GCC unroll 1")
    for (int t = 0; t < TPP - 1; t++) s->hist[t] = s->hist[OUT_HOP + t];
    s->e1 = e1; s->e2 = e2; s->e3 = e3; s->g = g; s->lcg = lcg;
}
