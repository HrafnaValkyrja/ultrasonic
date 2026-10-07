/* fw/bench/kernels.c - V4 cycle-budget kernels. See kernels.h and docs/research/drastic/V4-cycles.yaml.
 * Every loop has a data-independent trip count (FWSIM-R47); branchless selects (vsel/vmaxnm)
 * keep the static count honest. Build flags: Makefile (CFLAGS_M33).
 */
#include "kernels.h"
#include <math.h>
#include <string.h>

#define NOINL __attribute__((noinline))

/* ------------------------------------------------------------------ shared input */
/* ADF1 DR words: 24-bit sample left-aligned in DR[31:8]; window pre-scaled by 2^-23. */
NOINL void in_window(const int32_t *adf, const float *win, float *buf)
{
    _Pragma("GCC unroll 4")
    for (int i = 0; i < NFFT; i++)
        buf[i] = (float)(adf[i] >> 8) * win[i];
}

/* D2 fallback only: 400 -> 200 kS/s, 31-tap half-band = centre + 8 symmetric pairs. */
NOINL void halfband_d2(const float *x400, float *y200, int n_out)
{
    static const float h[HB_N] = {0.3133f, -0.0954f, 0.0491f, -0.0272f, 0.0148f, -0.0075f, 0.0034f, -0.0013f};
    for (int n = 0; n < n_out; n++) {
        const float *c = &x400[2 * n + 15];
        float acc = 0.5f * c[0];
        _Pragma("GCC unroll 8")
        for (int t = 0; t < HB_N; t++)
            acc += h[t] * (c[-1 - 2 * t] + c[1 + 2 * t]);
        y200[n] = acc;
    }
}

/* ------------------------------------------------------------------ 256-pt real FFT */
NOINL void bitrev128(cpx *x, const uint8_t *pairs, int npairs)
{
    for (int k = 0; k < npairs; k++) {
        int a = pairs[2 * k], b = pairs[2 * k + 1];
        cpx t = x[a]; x[a] = x[b]; x[b] = t;
    }
}

/* radix-2 DIT, in place, input already bit-reversed; tw[m] = exp(-2 pi i m / 128), m < 64 */
NOINL void cfft128(cpx *x, const cpx *tw)
{
    for (int len = 2, ts = NC / 2; len <= NC; len <<= 1, ts >>= 1) {
        int half = len >> 1;
        for (int j = 0; j < half; j++) {
            float wr = tw[j * ts].re, wi = tw[j * ts].im;
            for (int i = j; i < NC; i += len) {
                cpx *a = &x[i], *b = &x[i + half];
                float tr = wr * b->re - wi * b->im;
                float ti = wr * b->im + wi * b->re;
                float ar = a->re, ai = a->im;
                b->re = ar - tr; b->im = ai - ti;
                a->re = ar + tr; a->im = ai + ti;
            }
        }
    }
}

/* real split: Z = cfft(packed even/odd) -> X[k], k = 0..128 (X[128].re packed in X[0].im).
 * twr[k] = exp(-2 pi i k / 256), k = 0..63. */
NOINL void rsplit256(cpx *x, const cpx *twr)
{
    float z0r = x[0].re, z0i = x[0].im;
    x[0].re = z0r + z0i;           /* DC      */
    x[0].im = z0r - z0i;           /* Nyquist */
    x[NC / 2].im = -x[NC / 2].im;  /* k = 64  */
    for (int k = 1; k < NC / 2; k++) {
        cpx a = x[k], b = x[NC - k];
        float er = 0.5f * (a.re + b.re), ei = 0.5f * (a.im - b.im);     /* Fe = (Z[k] + conj Z[N-k]) / 2  */
        float or_ = 0.5f * (a.im + b.im), oi = -0.5f * (a.re - b.re);   /* Fo = -j (Z[k] - conj Z[N-k]) / 2 */
        float wr = twr[k].re, wi = twr[k].im;
        float tr = wr * or_ - wi * oi, ti = wr * oi + wi * or_;
        x[k].re = er + tr;      x[k].im = ei + ti;
        x[NC - k].re = er - tr; x[NC - k].im = -(ei - ti);
    }
}

/* ------------------------------------------------------------------ algorithm B */
static inline float fast_log2(float v)          /* |err| < 0.005 octave, v > 0 normal */
{
    union { float f; int32_t i; } u = {v};
    float e = (float)((u.i >> 23) - 127);
    u.i = (u.i & 0x007FFFFF) | 0x3F800000;      /* mantissa in [1,2) */
    float m = u.f;
    return e + (-0.34484843f * m + 2.02466578f) * m - 0.67487759f;
}
static inline float fast_exp2(float v)          /* v in [-126, 126] */
{
    float fl = floorf(v), f = v - fl;
    union { float f; int32_t i; } u;
    u.i = ((int32_t)fl + 127) << 23;
    return u.f * (1.0f + f * (0.6565f + f * 0.3435f));
}

/* per bin: power x mic EQ, accumulated into its band with the power-weighted frequency */
NOINL void b_bands(const cpx *X, const float *eq2, const float *fbin, const uint8_t *band, bstate *s)
{
    for (int b = 0; b < NB; b++) { s->E[b] = 0.0f; s->C[b] = 0.0f; }
    for (int k = 0; k < NBIN; k++) {
        cpx x = X[BIN_LO + k];
        float p = (x.re * x.re + x.im * x.im) * eq2[k];
        int j = band[k];
        s->E[j] += p;
        s->C[j] += p * fbin[k];
    }
}

/* per band: floor tracker, gate, envelope, centroid -> log map -> oscillator increment */
NOINL void b_update(bstate *s)
{
    for (int b = 0; b < NB; b++) {
        float e = s->E[b], f = s->floor_[b];
        float a = (e > f) ? s->a_up : s->a_dn;                 /* vsel                      */
        f += a * (e - f);
        s->floor_[b] = f;
        float eo = fmaxf(e - f * s->gate, 0.0f);               /* transient-only gate       */
        float target = sqrtf(eo) * s->gain;                    /* vsqrt                     */
        float env = s->env[b];
        float aa = (target > env) ? s->a_att : s->a_rel;
        s->amp[b] = env;                                       /* previous hop -> ramp start */
        s->env[b] = env + aa * (target - env);
        float cen = s->C[b] / (e + 1e-30f);                    /* vdiv: centroid (Hz)       */
        cen = fmaxf(cen, 20e3f);
        float u = s->k_map * (fast_log2(cen) - s->ln_lo);      /* 0..1 across 20..85 kHz   */
        s->inc[b] = s->incn[b];
        s->incn[b] = (uint32_t)(s->out_lo_inc * fast_exp2(u));
    }
}

/* oscillator bank: NB bands x 8 output samples, amplitude + frequency ramps, 1024-entry sine table */
NOINL void b_synth(bstate *s, const float *sintab, float *y8)
{
    for (int n = 0; n < OUT_HOP; n++) y8[n] = 0.0f;
    for (int b = 0; b < NB; b++) {
        float A = s->amp[b], dA = (s->env[b] - A) * (1.0f / OUT_HOP);
        int32_t I = (int32_t)s->inc[b], dI = ((int32_t)s->incn[b] - I) >> 3;
        uint32_t ph = s->ph[b];
        _Pragma("GCC unroll 8")
        for (int n = 0; n < OUT_HOP; n++) {
            A += dA; I += dI; ph += (uint32_t)I;
            y8[n] += A * sintab[ph >> 22];
        }
        s->ph[b] = ph;
    }
}

/* ------------------------------------------------------------------ algorithm A */
/* mix with the LO at 200 kS/s into the stage-1 buffer */
NOINL void a_mix(const int32_t *adf, const float *sintab, astate *s)
{
    uint32_t ph = s->ph, inc = s->inc;
    float *d = &s->d1[A_N1 - 1];
    for (int i = 0; i < HOP; i++) {
        ph += inc;
        d[i] = (float)(adf[i] >> 8) * sintab[ph >> 22];
    }
    s->ph = ph;
}

/* two-stage polyphase decimator: /4 (A_N1 taps, 32 outputs) then /4 (A_N2 taps, 8 outputs) */
NOINL void a_decim(const float *h1, const float *h2, astate *s, float *y8)
{
    for (int m = 0; m < HOP / 4; m++) {
        const float *x = &s->d1[4 * m];
        float acc = 0.0f;
        _Pragma("GCC unroll 16")
        for (int t = 0; t < A_N1; t++) acc += h1[t] * x[t];
        s->d2[A_N2 - 1 + m] = acc;
    }
    for (int n = 0; n < OUT_HOP; n++) {
        const float *x = &s->d2[4 * n];
        float acc = 0.0f;
        _Pragma("GCC unroll 8")
        for (int t = 0; t < A_N2; t++) acc += h2[t] * x[t];
        y8[n] = acc;
    }
    for (int t = 0; t < A_N1 - 1; t++) s->d1[t] = s->d1[HOP + t];
    for (int t = 0; t < A_N2 - 1; t++) s->d2[t] = s->d2[HOP / 4 + t];
}

/* 12.5 kS/s: band-floor high-pass biquad (DF2T) + envelope squelch with a slow floor */
NOINL void a_post(astate *s, float *y8)
{
    float b0 = s->bq[0], b1 = s->bq[1], b2 = s->bq[2], a1 = s->bq[3], a2 = s->bq[4];
    float z1 = s->z1, z2 = s->z2, sm = s->sm, fl = s->floor_;
    for (int n = 0; n < OUT_HOP; n++) {
        float x = y8[n];
        float y = b0 * x + z1;
        z1 = b1 * x - a1 * y + z2;
        z2 = b2 * x - a2 * y;
        sm += s->a_sm * (fabsf(y) - sm);
        fl = fminf(fl + 1e-6f * sm, sm);                      /* slow rise, instant fall   */
        float g = (sm - fl * s->gate) / (sm + 1e-20f);         /* vdiv                      */
        y8[n] = y * fminf(fmaxf(g, 0.0f), 1.0f);
    }
    s->z1 = z1; s->z2 = z2; s->sm = sm; s->floor_ = fl;
}

/* ------------------------------------------------------------------ shared output */
/* per 12.5 kS/s sample: x16 polyphase interpolation (TPP taps/phase), true peak of the 16
 * interpolated samples, limiter gain (instant attack from that true peak, smooth release:
 * B-FW-LIMITER), squelch envelope; then per 200 kHz sample: gain, 3rd-order error-feedback
 * shaper, TPDF dither (2 LCG draws), floor quantiser, clamp, CCR. */
NOINL void out_hop(const float *y8, const float *hpoly, ostate *s, uint16_t *ccr)
{
    float xi[UP];
    for (int n = 0; n < OUT_HOP; n++) s->hist[TPP - 1 + n] = y8[n];
    float e1 = s->e1, e2 = s->e2, e3 = s->e3, g = s->g;
    uint32_t lcg = s->lcg;
    for (int n = 0; n < OUT_HOP; n++) {
        const float *h = &s->hist[n];
        float peak = s->c;
        for (int p = 0; p < UP; p++) {
            const float *c = &hpoly[p * TPP];
            float acc = 0.0f;
            _Pragma("GCC unroll 16")
            for (int t = 0; t < TPP; t++) acc += c[t] * h[t];
            xi[p] = acc;
            peak = fmaxf(peak, fabsf(acc));
        }
        float need = s->c / peak;                              /* vdiv, <= 1                */
        g = fminf(g + s->a_rel * (1.0f - g), need);
        s->sq_env += s->sq_a * (y8[n] * y8[n] - s->sq_env);
        for (int p = 0; p < UP; p++) {
            float v = g * xi[p] + s->h1 * e1 + s->h2 * e2 + s->h3 * e3;
            lcg = lcg * 1664525u + 1013904223u; int32_t r1 = (int32_t)(lcg >> 9);
            lcg = lcg * 1664525u + 1013904223u; int32_t r2 = (int32_t)(lcg >> 9);
            float d = (float)(r1 - r2) * (1.0f / 8388608.0f);   /* TPDF, +-1 LSB             */
            float q = floorf(v * s->inv_step + d + 0.5f);
            q = fminf(fmaxf(q, -s->half_levels), s->half_levels);
            float e = q * s->step - v;
            e3 = e2; e2 = e1; e1 = e;
            ccr[n * UP + p] = (uint16_t)(int32_t)(q + s->half_levels);
        }
    }
    _Pragma("GCC unroll 1")
    for (int t = 0; t < TPP - 1; t++) s->hist[t] = s->hist[OUT_HOP + t];
    s->e1 = e1; s->e2 = e2; s->e3 = e3; s->g = g; s->lcg = lcg;
}
