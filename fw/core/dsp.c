/* fw/core/dsp.c: DSP chain (see dsp.h). Mirrors sim/dsp/pipeline.py algo_b / algo_a and sim/e2e/stages.py PwmShaper; deviations
 * from the float64 reference are listed in docs/sim/firmware-emulation.yaml FWSIM-R13/R14 status. */
#include "dsp.h"

#include <math.h>
#include <string.h>

#include "dsp_math.h"
#include "hal_fmac.h"

#define NOINL __attribute__((noinline))
#define FS_HZ 200000.0f
#define FS_OUT_HZ 12500.0f
#define BIN_HZ 781.25f                     /* 200 kHz / 256 */
#define INC_PER_HZ_INT 343597u             /* 2^32 / 12500 = 343597.38368 */
#define INC_PER_HZ_FRAC 0.38368f
#define HOP 128u
#define UP 16u

static const float hann[FW_DSP_HANN_N] = FW_DSP_HANN_INIT;
static const float eq2[FW_DSP_EQ2_N] = FW_DSP_EQ2_INIT;
static const float noise_spec[FW_DSP_NOISE_SPEC_N] = FW_DSP_NOISE_SPEC_INIT;
static const float noise_slim[FW_DSP_NOISE_SLIM_N] = FW_DSP_NOISE_SLIM_INIT;
static const float tw128[FW_DSP_TW128_N] = FW_DSP_TW128_INIT;
static const float twr256[FW_DSP_TWR256_N] = FW_DSP_TWR256_INIT;
static const float interp[FW_DSP_INTERP_N] = FW_DSP_INTERP_INIT;   /* [16][TPP] */
static const float hb[FW_DSP_HB_N] = FW_DSP_HB_INIT;
static const float a_hp[FW_DSP_A_HP_N] = FW_DSP_A_HP_INIT;
static const float a_h1[FW_DSP_A_H1_N] = FW_DSP_A_H1_INIT;
static const float a_h2[FW_DSP_A_H2_N] = FW_DSP_A_H2_INIT;
static const float ntf_2cos[FW_DSP_NTF_2COS_N] = FW_DSP_NTF_2COS_INIT;
static const float geo_spec[FW_DSP_GEO_SPEC_N] = FW_DSP_GEO_SPEC_INIT;
static const float geo_slim[FW_DSP_GEO_SLIM_N] = FW_DSP_GEO_SLIM_INIT;
static const float mapgeo_spec[FW_DSP_MAPGEO_SPEC_N] = FW_DSP_MAPGEO_SPEC_INIT;
static const float mapgeo_slim[FW_DSP_MAPGEO_SLIM_N] = FW_DSP_MAPGEO_SLIM_INIT;
static const float a_noise_sm[FW_DSP_A_NOISE_SM_N] = FW_DSP_A_NOISE_SM_INIT;

_Static_assert(FW_DSP_INTERP_N == 16u * FW_INTERP_TPP, "interpolator table shape");
_Static_assert(FW_DSP_A_H1_N == 16u && FW_DSP_A_H2_N == 40u, "algorithm A decimators 16 + 40 taps (pipeline.a_decimators)");
_Static_assert(FW_DSP_NOISE_SPEC_N == FW_DSP_NB_MAX, "spec B has 28 bands (FWSIM-R10 taps)");
_Static_assert(FW_INTERP_REJ_DB_X10 >= 670, "interpolator image rejection >= 67 dB into 8-16 kHz (FWSIM-R14 F5)");

/* Hz -> phase increment per 12.5 kS/s sample (2^32 = one turn); integer part exact */
static uint32_t hz_to_inc(float f)
{
    if (!(f > 0.0f))
        return 0u;
    uint32_t fi = (uint32_t)f;
    float ff = f - (float)fi;
    return fi * INC_PER_HZ_INT + (uint32_t)((float)fi * INC_PER_HZ_FRAC + ff * (343597.38368f) + 0.5f);
}

static float map_freq(const fw_dsp_t *d, float f)   /* pipeline.map_freq: log compression f_lo..f_hi -> out_lo..out_hi */
{
    if (f < d->f_lo)
        f = d->f_lo;
    if (f > d->f_hi)
        f = d->f_hi;
    return d->out_lo * fw_exp2f(d->k_map * fw_log2f(f / d->f_lo));
}

void fw_dsp_init(fw_dsp_t *d, const fw_knobs_t *k, uint32_t arr, uint32_t reps)
{
    memset(d, 0, sizeof *d);
    d->algo = k->algo == 1 ? (uint32_t)FW_ALGO_A : (uint32_t)FW_ALGO_B;
    d->slim = k->b_variant == 1 ? 1u : 0u;
    d->nb = d->slim ? FW_DSP_NOISE_SLIM_N : FW_DSP_NOISE_SPEC_N;
    d->ramp_len = d->slim ? 16u : 8u;
    d->ramp_shift = d->slim ? 4u : 3u;
    d->transient = k->transient_only ? 1u : 0u;
    d->arr = arr;
    d->reps = reps;
    d->dither_on = k->dither_on ? 1u : 0u;
    d->hold_samples = (uint32_t)k->squelch_hold_ms * 25u / 2u;   /* 12.5 samples per ms */
    float frame_s = (float)(d->slim ? 2u * HOP : HOP) / FS_HZ;
    d->om_up = fw_om_exp(frame_s * 1000.0f / (float)k->floor_up_ms);
    d->om_dn = fw_om_exp(frame_s * 1000.0f / (float)k->floor_down_ms);
    d->a_up = 1.0f - d->om_up;
    d->a_dn = 1.0f - d->om_dn;
    d->gate_lin = fw_db20_to_lin((float)k->gate_cdb * 0.02f);        /* 10^(gate_db/10) as power ratio */
    d->margin_lin = fw_db20_to_lin((float)k->noise_margin_cdb * 0.02f);
    d->gain_lin = fw_db20_to_lin((3000.0f + (float)k->volume_cdb) * 0.01f);   /* pipeline gain_db 30 + volume */
    d->a_att = fw_om_exp(frame_s * 1.0e6f / (float)k->env_attack_us);
    d->a_rel = fw_om_exp(frame_s * 1.0e6f / (float)k->env_release_us);
    d->f_lo = (float)k->band_lo_hz;
    d->f_hi = (float)k->band_hi_hz;
    d->out_lo = (float)k->out_lo_hz;
    float lr = fw_log2f(d->f_hi / d->f_lo);
    d->k_map = fw_log2f((float)k->out_hi_hz / d->out_lo) / lr;
    float bc = 1.0f;                                              /* binomial coefficients C(k_map, n), n = 1..5 */
    for (uint32_t i = 0; i < 5u; i++) {
        bc = bc * (d->k_map - (float)i) / (float)(i + 1u);
        d->mk[i] = bc;
    }
    /* band edges f_lo * (f_hi/f_lo)^(i/nb) (np.geomspace); bin k is in band b if edge[b] <= k*781.25 < edge[b+1] (np.digitize) */
    float edge[FW_DSP_NB_MAX + 1u];
    for (uint32_t i = 0; i <= d->nb; i++)
        edge[i] = i == 0u ? d->f_lo : (i == d->nb ? d->f_hi : d->f_lo * fw_exp2f(lr * (float)i / (float)d->nb));
    d->bin_lo = 0u;
    d->bin_hi = 0u;
    for (uint32_t kb = 0; kb < sizeof d->band_of_bin; kb++) {
        float f = (float)kb * BIN_HZ;
        uint8_t b = 255u;
        if (kb <= 128u && f >= edge[0] && f < edge[d->nb]) {
            uint32_t j = 0;
            while (j + 1u < d->nb && f >= edge[j + 1u])
                j++;
            b = (uint8_t)j;
            if (d->bin_hi == 0u)
                d->bin_lo = kb;
            d->bin_hi = kb + 1u;
        }
        d->band_of_bin[kb] = b;
    }
    for (uint32_t n = 0; n < 128u; n++) {
        uint32_t r = 0;
        for (uint32_t bit = 0; bit < 7u; bit++)
            r |= ((n >> bit) & 1u) << (6u - bit);
        d->rev[n] = (uint8_t)r;
    }
    for (uint32_t b = 0; b <= d->nb; b++) {                       /* first bin of each band (bins of a band are contiguous) */
        uint32_t kb = d->bin_lo;
        while (kb < d->bin_hi && d->band_of_bin[kb] < b)
            kb++;
        d->band_start[b] = (uint8_t)kb;
    }
    for (uint32_t b = 0; b < d->nb; b++) {
        d->geo[b] = sqrtf(edge[b] * edge[b + 1u]);
        d->noise[b] = d->slim ? noise_slim[b] : noise_spec[b];
        d->inc_prev[b] = hz_to_inc(map_freq(d, d->geo[b]));      /* pipeline: f_prev = map_freq(geometric centres) */
        d->map_geo[b] = map_freq(d, d->geo[b]);
        if (FW_DSP_MAP_DEFAULTS(k->band_lo_hz, k->band_hi_hz, k->out_lo_hz, k->out_hi_hz)) {   /* exact tables (dsp_tables.h) */
            d->geo[b] = d->slim ? geo_slim[b] : geo_spec[b];
            d->map_geo[b] = d->slim ? mapgeo_slim[b] : mapgeo_spec[b];
            d->inc_prev[b] = hz_to_inc(d->map_geo[b]);
        }
        d->inv_geo[b] = 1.0f / d->geo[b];
    }
    /* algorithm A */
    d->a_lo_inc = (uint32_t)((((uint64_t)(uint32_t)k->a_lo_hz << 32) + 100000u) / 200000u);   /* round(f 2^32 / 200 kHz), exact */
    d->a_gate_lin = fw_db20_to_lin((float)k->gate_cdb * 0.01f);
    d->a_noise_thr = a_noise_sm[0] * fw_db20_to_lin((float)k->noise_margin_cdb * 0.01f);   /* gate floor: mic self-noise + margin */
    d->a_up_s = fw_om_exp(1000.0f / ((float)k->floor_up_ms * FS_OUT_HZ));
    d->a_dn_s = fw_om_exp(1000.0f / ((float)k->floor_down_ms * FS_OUT_HZ));
    /* output stage */
    d->lim_c = fw_db20_to_lin((float)k->ceiling_cdb * 0.01f);
    d->lim_rel = fw_om_exp(1000.0f / (FS_OUT_HZ * (float)k->limiter_release_ms));
    d->la_on = k->lim_lookahead ? 1u : 0u;
    if (d->la_on) {   /* loudness fix: ceiling = R64 clamp minus the noise-shaper excursion bound (so the clamp never bites); D17 fixed ceiling */
        float amp = (float)fw_out_amp_max_ppm(k) * 1e-6f - (float)FW_SHAPER_EXCURSION_PPM * 1e-6f;
        d->lim_c = amp > d->lim_c ? amp : d->lim_c;
        fw_lahead_init(&d->la, d->lim_c, (uint32_t)k->lim_knee_pct, d->lim_rel);
    }
    d->lim_g = 1.0f;
    d->guard_g = 1.0f;
    {
        static const float kappa[FW_DSP_INTERP_KAPPA_N] = FW_DSP_INTERP_KAPPA_INIT;
        float sc = 0.999f / (2.0f * d->lim_c * kappa[0]);       /* +6 dB guard: |input| <= 2 ceiling -> |FMAC input| <= 0.999 / kappa */
        d->fmac_in_scale = sc * 32768.0f;
        d->fmac_out_scale = 1.0f / (sc * 32768.0f);
    }
    d->sq_thr2 = fw_db20_to_lin((float)k->squelch_cdb * 0.02f);    /* power threshold 10^(dB/10) */
    d->sq_a = 1.0f / 62.5f;                                         /* 5 ms one-pole power average (PwmShaper: 5 ms rms) */
    d->sq_quiet = d->hold_samples;                                  /* start squelched: silence is an exact 50 % square wave */
    d->step = 2.0f / (float)arr;
    d->inv_step = (float)arr * 0.5f;
    uint32_t ri = reps == 2u ? 1u : (reps == 4u ? 2u : 0u);   /* NTF zero tuned per PWM rate, not per ARR */
    d->h1 = -(ntf_2cos[ri] + 1.0f);                                 /* ntf = (1 - z^-1)(1 - 2c z^-1 + z^-2): h = ntf[1:] */
    d->h2 = ntf_2cos[ri] + 1.0f;
    d->dither = 22695477u;                                          /* xorshift32 seed (determinism rules: fixed) */
}

void fw_dsp_set_gain_cdb(fw_dsp_t *d, int32_t volume_cdb)
{
    d->gain_lin = fw_db20_to_lin((3000.0f + (float)volume_cdb) * 0.01f);   /* pipeline gain_db 30 + volume */
}

int fw_dsp_set_noise(fw_dsp_t *d, const float *band_energy, uint32_t n)
{
    if (band_energy == NULL || n != d->nb)
        return -1;
    for (uint32_t b = 0; b < n; b++)
        d->noise[b] = band_energy[b] >= 0.0f ? band_energy[b] : 0.0f;
    return 0;
}

/* ------------------------------------------------------------------ D2 front end */
NOINL void fw_dsp_halfband(fw_dsp_t *d, const int32_t in400[256], float pcm[128])
{
    float *h = d->hb_hist;                                       /* [30 history | 256 new] */
    for (uint32_t i = 0; i < 256u; i++)
        h[30u + i] = (float)in400[i];
    /* causal y[m] = sum h[k] x[m-k] at odd m (= reference 'same' output at even index m-15: PCM delayed 7 samples) */
    for (uint32_t j = 0; j < 128u; j++) {
        const float *x = &h[30u + 2u * j + 1u];
        float acc = hb[15] * x[-15];
        for (uint32_t t = 0; t < 15u; t++)
            acc += hb[t] * (x[-(int32_t)t] + x[-30 + (int32_t)t]);
        pcm[j] = acc;
    }
    for (uint32_t i = 0; i < 30u; i++)                           /* explicit loops, not memmove: newlib-nano copies bytewise */
        h[i] = h[256u + i];
}

/* ------------------------------------------------------------------ 256-pt real FFT (128-pt complex radix-2 DIT + split) */
/* window + bit-reversed packing in one pass: z[rev(n)] = (x[2n] + j x[2n+1]) * hann (replaces a separate bit-reverse pass) */
NOINL static void fft_pack_ring(const fw_dsp_t *d, const float *pcm, uint32_t off, float *z)
{
    for (uint32_t n = 0; n < 128u; n++) {                       /* pcm[] is a 2-half ring: frame sample i = pcm[(off + i) & 255] */
        uint32_t r = 2u * d->rev[n], i = (off + 2u * n) & 255u;
        z[r] = pcm[i] * hann[2u * n];
        z[r + 1u] = pcm[i + 1u] * hann[2u * n + 1u];
    }
}
#define fft_pack(d, z) fft_pack_ring((d), (d)->pcm, (d)->pcm_old, (z))

/* radix-2 DIT butterfly: (a, b) <- (a + w b, a - w b), the operation order of the plain radix-2 loop */
#define BFLY(a, b, wr, wi)                                                                            \
    do {                                                                                              \
        float tr_ = (wr) * (b)[0] - (wi) * (b)[1], ti_ = (wr) * (b)[1] + (wi) * (b)[0];               \
        float ar_ = (a)[0], ai_ = (a)[1];                                                             \
        (b)[0] = ar_ - tr_;                                                                           \
        (b)[1] = ai_ - ti_;                                                                           \
        (a)[0] = ar_ + tr_;                                                                           \
        (a)[1] = ai_ + ti_;                                                                           \
    } while (0)

/* 128-pt complex FFT, input bit-reversed: radix-2 stages fused in pairs (lengths 2+4 without multiplies, 8+16, 32+64: one pass over
 * memory per pair, same arithmetic order as plain radix-2), then the length-128 stage. */
NOINL static void fft_cfft128(float *z)
{
    for (uint32_t g = 0; g < 128u; g += 4u) {                    /* lengths 2 + 4: twiddles 1, 1, -j: no multiplies */
        float *a = &z[2u * g];
        float r0 = a[0] + a[2], i0 = a[1] + a[3], r1 = a[0] - a[2], i1 = a[1] - a[3];
        float r2 = a[4] + a[6], i2 = a[5] + a[7], r3 = a[4] - a[6], i3 = a[5] - a[7];
        a[0] = r0 + r2;
        a[1] = i0 + i2;
        a[4] = r0 - r2;
        a[5] = i0 - i2;
        a[2] = r1 + i3;                                          /* r1 + (-j)(r3 + j i3) = (r1 + i3) + j(i1 - r3) */
        a[3] = i1 - r3;
        a[6] = r1 - i3;
        a[7] = i1 + r3;
    }
    for (uint32_t q = 4u; q <= 16u; q <<= 2) {                 /* q = quarter of the fused group: 1, 4, 16 */
        uint32_t ts1 = 64u / q, ts2 = 32u / q;                  /* twiddle strides of the stages of length 2q and 4q */
        for (uint32_t j = 0; j < q; j++) {
            float w1r = tw128[2u * j * ts1], w1i = tw128[2u * j * ts1 + 1u];
            float w2r = tw128[2u * j * ts2], w2i = tw128[2u * j * ts2 + 1u];
            float w3r = tw128[2u * (j + q) * ts2], w3i = tw128[2u * (j + q) * ts2 + 1u];
            for (uint32_t g = j; g < 128u; g += 4u * q) {
                float *a = &z[2u * g], *b = &z[2u * (g + q)], *c = &z[2u * (g + 2u * q)], *e = &z[2u * (g + 3u * q)];
                BFLY(a, b, w1r, w1i);
                BFLY(c, e, w1r, w1i);
                BFLY(a, c, w2r, w2i);
                BFLY(b, e, w3r, w3i);
            }
        }
    }
    for (uint32_t j = 0; j < 64u; j++)                          /* length-128 stage */
        BFLY(&z[2u * j], &z[2u * (j + 64u)], tw128[2u * j], tw128[2u * j + 1u]);
}

NOINL static void fft_split(float *z)
{
    float z0r = z[0], z0i = z[1];
    z[0] = z0r + z0i;                                            /* DC */
    z[1] = z0r - z0i;                                            /* Nyquist (packed) */
    z[129] = -z[129];                                            /* k = 64 */
    for (uint32_t k = 1; k < 64u; k++) {
        float *a = &z[2u * k], *b = &z[2u * (128u - k)];
        float er = 0.5f * (a[0] + b[0]), ei = 0.5f * (a[1] - b[1]);
        float orr = 0.5f * (a[1] + b[1]), oi = -0.5f * (a[0] - b[0]);
        float wr = twr256[2u * k], wi = twr256[2u * k + 1u];
        float tr = wr * orr - wi * oi, ti = wr * oi + wi * orr;
        a[0] = er + tr;
        a[1] = ei + ti;
        b[0] = er - tr;
        b[1] = -(ei - ti);
    }
}

/* ------------------------------------------------------------------ algorithm B */
/* band energy and power-weighted frequency: bins of a band are contiguous, so per band one accumulation in registers */
NOINL static void b_bands(fw_dsp_t *d, const float *z, float *fc)
{
    for (uint32_t b = 0; b < d->nb; b++) {
        float e = 0.0f, f = 0.0f;
        for (uint32_t k = d->band_start[b]; k < d->band_start[b + 1u]; k++) {
            float p = (z[2u * k] * z[2u * k] + z[2u * k + 1u] * z[2u * k + 1u]) * eq2[k];
            e += p;
            f += p * ((float)k * BIN_HZ);
        }
        d->E[b] = e;
        fc[b] = f;
    }
}

NOINL static void b_update(fw_dsp_t *d, const float *fc)
{
    uint32_t first = d->frames == 0u;
    for (uint32_t b = 0; b < d->nb; b++) {
        float e = d->E[b];
        float fl = first ? e : d->floor_[b];                     /* floor initialised from the first frame (power-on) */
        fl = e > fl ? d->a_up * fl + d->om_up * e : d->a_dn * fl + d->om_dn * e;
        d->floor_[b] = fl;
        float nthr = d->noise[b] * d->margin_lin;
        float thr = fl * d->gate_lin;
        if (thr < nthr)
            thr = nthr;
        float eo = (d->transient ? e - thr : e - nthr);
        if (eo < 0.0f)
            eo = 0.0f;
        float target = sqrtf(eo) * d->gain_lin;
        float env = d->env[b];
        env += (target > env ? d->a_att : d->a_rel) * (target - env);
        d->env[b] = env;
        d->amp_new[b] = env;
        float cen = e > 0.0f ? fc[b] / e : d->geo[b];
        /* map_freq(cen) = out_lo (cen/f_lo)^k as a 5th-order binomial series around the band centre: the centroid lies inside the
         * band (|x| <= 4.6 % for slim B), truncation <= 2e-10; replaces a log2 + exp2 pair per band */
        float x = (cen - d->geo[b]) * d->inv_geo[b];                 /* cen - geo exact (Sterbenz): x carries no 1-ulp offset */
        float m = d->map_geo[b] * (1.0f + x * (d->mk[0] + x * (d->mk[1] + x * (d->mk[2] + x * (d->mk[3] + x * d->mk[4])))));
        d->inc_new[b] = hz_to_inc(m);
    }
}

/* oscillator bank: ramp amplitude and phase increment across ramp_len samples (8 spec, 16 slim); 8 samples per hop */
/* oscillator bank: ramp amplitude and phase increment across ramp_len samples (8 spec, 16 slim); 8 samples per hop.
 * Increment at ramp step kk = inc0 + floor(di kk / L) = inc0 + q kk + floor(r kk / L) with di = q L + r (exact in 32 bits). */
#define SYN(acc)                                                                                      \
    do {                                                                                              \
        qk += qd;                                                                                     \
        rk += rd;                                                                                     \
        fk += inv_len;                                                                                \
        ph += inc0 + qk + (rk >> sh);                                                                 \
        acc += (a0 + da * fk) * FW_SIN_TURNS(ph);                                                     \
    } while (0)

NOINL static void b_synth(fw_dsp_t *d, float *y8)
{
    float inv_len = d->slim ? 0.0625f : 0.125f;
    uint32_t sh = d->ramp_shift, kk0 = d->ramp_pos;
    float y0 = 0.0f, y1 = 0.0f, y2 = 0.0f, y3 = 0.0f, y4 = 0.0f, y5 = 0.0f, y6 = 0.0f, y7 = 0.0f;
    for (uint32_t b = 0; b < d->nb; b++) {
        float a0 = d->amp_prev[b], da = d->amp_new[b] - a0;
        int32_t di = (int32_t)(d->inc_new[b] - d->inc_prev[b]);
        uint32_t qd = (uint32_t)(di >> sh), rd = (uint32_t)di & (d->ramp_len - 1u);   /* floor division (arithmetic shift) */
        uint32_t ph = d->phase[b], inc0 = d->inc_prev[b], qk = qd * kk0, rk = rd * kk0;
        float fk = (float)kk0 * inv_len;
        SYN(y0); SYN(y1); SYN(y2); SYN(y3); SYN(y4); SYN(y5); SYN(y6); SYN(y7);
        d->phase[b] = ph;
    }
    y8[0] = y0; y8[1] = y1; y8[2] = y2; y8[3] = y3; y8[4] = y4; y8[5] = y5; y8[6] = y6; y8[7] = y7;
    d->ramp_pos += 8u;
    if (d->ramp_pos >= d->ramp_len) {
        d->ramp_pos = 0u;
        for (uint32_t b = 0; b < d->nb; b++) {
            d->amp_prev[b] = d->amp_new[b];
            d->inc_prev[b] = d->inc_new[b];
        }
    }
}

void fw_dsp_spectrum(const fw_dsp_t *d, const float *pcm256, uint32_t off, float p[129])
{
    float z[FW_DSP_NFFT];
    fft_pack_ring(d, pcm256, off, z);
    fft_cfft128(z);
    fft_split(z);
    p[0] = z[0] * z[0];
    p[128] = z[1] * z[1];
    for (uint32_t k = 1; k < 128u; k++)
        p[k] = z[2u * k] * z[2u * k] + z[2u * k + 1u] * z[2u * k + 1u];
}

static void algo_b(fw_dsp_t *d, float y8[8], float *band_energy, float *floor_tap)
{
    uint32_t idx = d->hops - 1u;                                 /* this hop's index */
    if (idx >= 1u && (!d->slim || (idx & 1u))) {                 /* a full 256-sample frame: spec every hop, slim every other */
        float z[FW_DSP_NFFT], fc[FW_DSP_NB_MAX] = {0.0f};
        fft_pack(d, z);
        fft_cfft128(z);
        fft_split(z);
        b_bands(d, z, fc);
        b_update(d, fc);
        d->frames++;
    }
    if (d->frames == 0u) {
        for (uint32_t s = 0; s < 8u; s++)
            y8[s] = 0.0f;
    } else {
        b_synth(d, y8);
    }
    if (band_energy != NULL && floor_tap != NULL)
        for (uint32_t b = 0; b < d->nb; b++) {
            band_energy[b] = d->E[b];
            floor_tap[b] = d->floor_[b];
        }
}

/* ------------------------------------------------------------------ algorithm A (fallback) */
/* LO mix: 2 x FS-scaled x cos(2 pi f_lo t) into the stage-1 buffer [15 history | 128 new] */
NOINL static void a_mix(fw_dsp_t *d, const float *pcm)
{
    float *x1 = &d->a_x1[15];
    uint32_t ph = d->a_lo_ph;
    for (uint32_t i = 0; i < HOP; i++) {
        x1[i] = pcm[i] * 0x1p-30f * FW_SIN_TURNS(ph + (1u << 30));
        ph += d->a_lo_inc;
    }
    d->a_lo_ph = ph;
}

/* pipeline.algo_a_base decimators, causal, outputs at input index 4k+3: 16-tap /4 (200k -> 50k), 40-tap /4 (50k -> 12.5k),
 * then butter(2) HP (transposed direct form II = scipy sosfilt) at 12.5 kS/s. Taps written out (one source line per 8). */
#define T8(h, x, o) (h)[o] * (x)[-(o)] + (h)[(o) + 1] * (x)[-(o) - 1] + (h)[(o) + 2] * (x)[-(o) - 2] + (h)[(o) + 3] * (x)[-(o) - 3] + \
                    (h)[(o) + 4] * (x)[-(o) - 4] + (h)[(o) + 5] * (x)[-(o) - 5] + (h)[(o) + 6] * (x)[-(o) - 6] + (h)[(o) + 7] * (x)[-(o) - 7]
NOINL static void a_decim(fw_dsp_t *d, float *y8)
{
    float *x2 = &d->a_x2[39];
    for (uint32_t k = 0; k < 32u; k++) {
        const float *x = &d->a_x1[15u + 4u * k + 3u];            /* newest input of output k */
        x2[k] = T8(a_h1, x, 0) + T8(a_h1, x, 8);
    }
    for (uint32_t i = 0; i < 15u; i++)
        d->a_x1[i] = d->a_x1[HOP + i];
    float z1 = d->a_z1, z2 = d->a_z2;
    for (uint32_t q = 0; q < 8u; q++) {
        const float *x = &x2[4u * q + 3u];
        float acc = T8(a_h2, x, 0) + T8(a_h2, x, 8) + T8(a_h2, x, 16);
        acc = acc + T8(a_h2, x, 24) + T8(a_h2, x, 32);
        float y = a_hp[0] * acc + z1;
        z1 = a_hp[1] * acc - a_hp[3] * y + z2;
        z2 = a_hp[2] * acc - a_hp[4] * y;
        y8[q] = y;
    }
    d->a_z1 = z1;
    d->a_z2 = z2;
    for (uint32_t i = 0; i < 39u; i++)
        d->a_x2[i] = d->a_x2[32u + i];
}

NOINL static void a_post(fw_dsp_t *d, float *y8)
{
    for (uint32_t s = 0; s < 8u; s++) {
        float y = y8[s];
        float g = 1.0f;
        if (d->transient) {                                      /* causal envelope gate (reference: hilbert + global percentile) */
            float sm = d->a_sm + 0.02f * (fabsf(y) * 1.5707964f - d->a_sm);
            d->a_sm = sm;
            float fl = d->a_floor_init ? d->a_floor : sm;
            d->a_floor_init = 1u;
            fl = sm > fl ? fl + d->a_up_s * (sm - fl) : fl + d->a_dn_s * (sm - fl);
            d->a_floor = fl;
            float thr = fl * d->a_gate_lin;
            if (thr < d->a_noise_thr)
                thr = d->a_noise_thr;
            g = sm > 0.0f ? (sm - thr) / sm : 0.0f;
            if (g < 0.0f)
                g = 0.0f;
            if (g > 1.0f)
                g = 1.0f;
        }
        y8[s] = y * g * d->gain_lin;
    }
}

void fw_dsp_pcm_push(fw_dsp_t *d, const float pcm[128])
{
    d->hops++;
    uint32_t w = (d->hops & 1u) * HOP;                           /* the new half overwrites the oldest one: no shift */
    d->pcm_old = w ^ HOP;
    for (uint32_t i = 0; i < HOP; i++)
        d->pcm[w + i] = pcm[i];
}

void fw_dsp_algo(fw_dsp_t *d, const float pcm[128], float y8[8], float *band_energy, float *floor_tap)
{
    if (d->algo == (uint32_t)FW_ALGO_A) {
        a_mix(d, pcm);
        a_decim(d, y8);
        a_post(d, y8);
        if (band_energy != NULL && floor_tap != NULL)
            for (uint32_t b = 0; b < FW_DSP_NB_MAX; b++)
                band_energy[b] = floor_tap[b] = 0.0f;
        return;
    }
    algo_b(d, y8, band_energy, floor_tap);
}

/* ------------------------------------------------------------------ output stage */
/* history in scalars (registers): h0 newest */
#define DOT4(c, o, x0, x1, x2, x3) (c)[o] * x0 + (c)[(o) + 1] * x1 + (c)[(o) + 2] * x2 + (c)[(o) + 3] * x3
#if FW_INTERP_TPP == 8
#define INTERP_DOT(c) (DOT4(c, 0, h0, h1_, h2_, h3) + DOT4(c, 4, h4, h5, h6, h7))
#elif FW_INTERP_TPP == 10
#define INTERP_DOT(c) (DOT4(c, 0, h0, h1_, h2_, h3) + DOT4(c, 4, h4, h5, h6, h7) + (c)[8] * h8 + (c)[9] * h9)
#else
#define INTERP_DOT(c) (DOT4(c, 0, h0, h1_, h2_, h3) + DOT4(c, 4, h4, h5, h6, h7) + DOT4(c, 8, h8, h9, h10, h11))
#endif

/* one PWM period of the 3rd-order error-feedback shaper (stages.PwmShaper) with TPDF dither; level qi -> CCR through the clamp.
 * No clip inside the loop (FWSIM-R15: never clip after the shaper); the FWSIM-R64 bound applies to the CCR only. */
#define SHAPE_ONE()                                                                                   \
    do {                                                                                              \
        float vv = x + h1 * e1 + h2 * e2 - e3;                                                        \
        dith ^= dith << 13;                                                                           \
        dith ^= dith >> 17;                                                                           \
        dith ^= dith << 5;                                                                            \
        float dz = (float)((int32_t)(dith >> 16) - (int32_t)(dith & 0xFFFFu)) * dscale;               \
        int32_t qi = (int32_t)((vv + dz) * inv_step + 1024.5f) - 1024;   /* floor(. + 0.5), arg > -1024 */ \
        e3 = e2;                                                                                      \
        e2 = e1;                                                                                      \
        e1 = (float)qi * step - vv;                                                                   \
        FW_CCR_LEVEL_STORE(ccr[n], qi, b, hits);                                                      \
        n++;                                                                                          \
    } while (0)

/* x16 interpolation of the hop's 8 samples -> v[128] (interleaved: v[16 s + p]).
 * FW_INTERP_FMAC = 1 (default): +6 dB scaling guard (sample-domain gain limiter at 2 x ceiling, same law as the true-peak limiter) ->
 * q1.15 at scale 0.999 / (2 ceiling kappa) -> FMAC polyphase bank (hal_fmac_fir_bank; bit-accurate model on host/QEMU) -> float.
 * docs/research/drastic/V5-fmac-cordic.yaml: in-band error -99.9 dBFS, D17 THD+N at -40 dBFS -49.3 -> -48.9 dB. On an FMAC error the
 * CPU float path runs for that hop (counted in fmac_faults). FW_INTERP_FMAC = 0: CPU float polyphase only (A/B build option). */
NOINL static void out_interp_cpu(fw_dsp_t *d, const float y8[8], float *v)
{
    for (uint32_t s = 0; s < 8u; s++) {
        for (uint32_t t = FW_INTERP_TPP - 1u; t > 0u; t--)
            d->ihist[t] = d->ihist[t - 1u];
        d->ihist[0] = y8[s];
        float h0 = d->ihist[0], h1_ = d->ihist[1], h2_ = d->ihist[2], h3 = d->ihist[3], h4 = d->ihist[4], h5 = d->ihist[5], h6 = d->ihist[6],
              h7 = d->ihist[7];
#if FW_INTERP_TPP >= 10
        float h8 = d->ihist[8], h9 = d->ihist[9];
#endif
#if FW_INTERP_TPP >= 12
        float h10 = d->ihist[10], h11 = d->ihist[11];
#endif
        for (uint32_t p = 0; p < UP; p++)
            v[s * UP + p] = INTERP_DOT(&interp[p * FW_INTERP_TPP]);
    }
}

#if FW_INTERP_FMAC
static const int16_t interp_q15[FW_DSP_INTERP_Q15_N] = FW_DSP_INTERP_Q15_INIT;

NOINL static void out_interp_fmac(fw_dsp_t *d, const float y8[8], float *v)
{
    int16_t *xq = d->xq;                                         /* [TPP-1 history | 8 new], oldest first */
    float lim = 2.0f * d->lim_c;
    for (uint32_t s = 0; s < 8u; s++) {
        float y = y8[s], a = fabsf(y);
        float g = d->guard_g + d->lim_rel * (1.0f - d->guard_g); /* +6 dB guard: same instant attack / release law */
        if (a * g > lim)
            g = lim / a;
        d->guard_g = g;
        float q = y * g * d->fmac_in_scale;                      /* |q| <= 0.999 x 32768 / kappa */
        int32_t qi = (int32_t)(q + (q >= 0.0f ? 0.5f : -0.5f));
        qi = qi > 32767 ? 32767 : (qi < -32768 ? -32768 : qi);
        xq[FW_INTERP_TPP - 1u + s] = (int16_t)qi;
    }
    int16_t yq[8u * UP];
    if (hal_fmac_fir_bank(interp_q15, UP, FW_INTERP_TPP, 0u, xq, 8u, yq) == HAL_OK) {
        float sc = d->fmac_out_scale;
        for (uint32_t i = 0; i < 8u * UP; i += 4u) {             /* q1.15 -> float, 4 per line */
            v[i] = (float)yq[i] * sc; v[i + 1u] = (float)yq[i + 1u] * sc; v[i + 2u] = (float)yq[i + 2u] * sc; v[i + 3u] = (float)yq[i + 3u] * sc;
        }
        for (uint32_t t = FW_INTERP_TPP; t-- > 0u;)            /* keep the float history in step for a later fallback hop */
            d->ihist[t] = t >= 8u ? d->ihist[t - 8u] : y8[7u - t];
    } else {
        d->fmac_faults++;
        out_interp_cpu(d, y8, v);
    }
    for (uint32_t i = 0; i < FW_INTERP_TPP - 1u; i++)
        xq[i] = xq[8u + i];
}
#endif

NOINL size_t fw_dsp_out(fw_dsp_t *d, const float y8_in[8], uint32_t force_squelch, const fw_ccr_bounds_t *b, uint16_t *ccr, fw_out_info_t *info)
{
    float yl[8];
    const float *y8 = y8_in;
    if (d->la_on) {
        fw_lahead_hop(&d->la, y8_in, yl);
        y8 = yl;
    }
    size_t n = 0;
    float peak = 0.0f;
    uint32_t sq = 0u, sq_periods = 0u, hits = 0u, reps = d->reps, dith = d->dither;
    float e1 = d->e1, e2 = d->e2, e3 = d->e3, h1 = d->h1, h2 = d->h2, step = d->step, inv_step = d->inv_step;
    float dscale = d->dither_on ? step * 0x1p-16f : 0.0f;       /* TPDF: two 16-bit uniforms of one xorshift32 draw, x 1 LSB */
    uint16_t centre = fw_ccr_from_level(0, b, &hits);
    float vall[8u * UP];
#if FW_INTERP_FMAC
    out_interp_fmac(d, y8, vall);
#else
    out_interp_cpu(d, y8, vall);
#endif
    for (uint32_t s = 0; s < 8u; s++) {
        float y = y8[s];
        /* squelch (stages.PwmShaper): 5 ms power below threshold for squelch_hold_ms -> exact zero, dither off, shaper reset */
        d->sq_env += d->sq_a * (y * y - d->sq_env);
        if (d->sq_env < d->sq_thr2) {
            if (d->sq_quiet < d->hold_samples)
                d->sq_quiet++;
        } else {
            d->sq_quiet = 0u;
        }
        sq = (force_squelch || d->sq_quiet >= d->hold_samples) ? 1u : 0u;
        const float *v = &vall[s * UP];
        float pk = 0.0f;
        for (uint32_t p = 0; p < UP; p++) {
            float a = fabsf(v[p]);
            pk = a > pk ? a : pk;
        }
        /* true-peak limiter at the ceiling (FWSIM-R14 F1): instant attack from the 16 interpolated samples, slow release;
         * |x| <= lim_c holds on every pre-quantiser sample by construction */
        float g = d->lim_g + d->lim_rel * (1.0f - d->lim_g);
        if (pk * g > d->lim_c)
            g = d->lim_c / pk;
        d->lim_g = g;
        if (sq) {                                                /* F2: exact centre, shaper state zeroed, dither off */
            e1 = e2 = e3 = 0.0f;
            for (uint32_t m = 0; m < UP * reps; m++)
                ccr[n++] = centre;
            sq_periods += UP * reps;
            continue;
        }
        for (uint32_t p = 0; p < UP; p++) {
            float x = v[p] * g;
            float a = fabsf(x);
            peak = a > peak ? a : peak;
            if (reps == 1u) {                                    /* 200 kHz PWM: one period per interpolated sample */
                SHAPE_ONE();
            } else {                                             /* 400 / 800 kHz: zero-order hold x2 / x4 */
                for (uint32_t r = 0; r < reps; r++)
                    SHAPE_ONE();
            }
        }
    }
    d->e1 = e1;
    d->e2 = e2;
    d->e3 = e3;
    d->dither = dith;
    if (info != NULL) {
        info->true_peak = peak;
        info->shaper_norm[0] = fabsf(e1);
        info->shaper_norm[1] = fabsf(e2);
        info->shaper_norm[2] = fabsf(e3);
        info->squelched = sq;
        info->squelched_periods = sq_periods;
        info->clamp_hits = hits;
    }
    return n;
}
