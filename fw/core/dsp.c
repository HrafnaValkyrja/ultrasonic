/* fw/core/dsp.c: DSP chain (see dsp.h). Mirrors sim/dsp/pipeline.py algo_b / algo_a and sim/e2e/stages.py PwmShaper; deviations
 * from the float64 reference are listed in docs/sim/firmware-emulation.yaml FWSIM-R13/R14 status. */
#include "dsp.h"

#include <math.h>
#include <string.h>

#include "dsp_math.h"

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
static const uint8_t bitrev[FW_DSP_BITREV_N] = FW_DSP_BITREV_INIT;
static const float tw128[FW_DSP_TW128_N] = FW_DSP_TW128_INIT;
static const float twr256[FW_DSP_TWR256_N] = FW_DSP_TWR256_INIT;
static const float interp[FW_DSP_INTERP_N] = FW_DSP_INTERP_INIT;   /* [16][TPP] */
static const float hb[FW_DSP_HB_N] = FW_DSP_HB_INIT;
static const float a_hp[FW_DSP_A_HP_N] = FW_DSP_A_HP_INIT;
static const float a_c[FW_DSP_A_C_N] = FW_DSP_A_C_INIT;
static const float ntf_2cos[FW_DSP_NTF_2COS_N] = FW_DSP_NTF_2COS_INIT;

_Static_assert(FW_DSP_INTERP_N == 16u * FW_INTERP_TPP, "interpolator table shape");
_Static_assert(FW_DSP_A_C_N * 2u - 1u == FW_DSP_A_NC, "algorithm A FIR is symmetric, 288 folded taps");
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

void fw_dsp_init(fw_dsp_t *d, const fw_knobs_t *k, uint32_t arr)
{
    memset(d, 0, sizeof *d);
    d->algo = k->algo == 1 ? (uint32_t)FW_ALGO_A : (uint32_t)FW_ALGO_B;
    d->slim = k->b_variant == 1 ? 1u : 0u;
    d->nb = d->slim ? FW_DSP_NOISE_SLIM_N : FW_DSP_NOISE_SPEC_N;
    d->ramp_len = d->slim ? 16u : 8u;
    d->ramp_shift = d->slim ? 4u : 3u;
    d->transient = k->transient_only ? 1u : 0u;
    d->arr = arr;
    d->reps = 200u / arr;
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
    for (uint32_t b = 0; b < d->nb; b++) {
        d->geo[b] = sqrtf(edge[b] * edge[b + 1u]);
        d->noise[b] = d->slim ? noise_slim[b] : noise_spec[b];
        d->inc_prev[b] = hz_to_inc(map_freq(d, d->geo[b]));      /* pipeline: f_prev = map_freq(geometric centres) */
    }
    /* algorithm A */
    d->a_lo_inc = (uint32_t)((((uint64_t)(uint32_t)k->a_lo_hz << 32) + 100000u) / 200000u);   /* round(f 2^32 / 200 kHz), exact */
    d->a_gate_lin = fw_db20_to_lin((float)k->gate_cdb * 0.01f);
    d->a_up_s = fw_om_exp(1000.0f / ((float)k->floor_up_ms * FS_OUT_HZ));
    d->a_dn_s = fw_om_exp(1000.0f / ((float)k->floor_down_ms * FS_OUT_HZ));
    /* output stage */
    d->lim_c = fw_db20_to_lin((float)k->ceiling_cdb * 0.01f);
    d->lim_rel = fw_om_exp(1000.0f / (FS_OUT_HZ * (float)k->limiter_release_ms));
    d->lim_g = 1.0f;
    d->sq_thr2 = fw_db20_to_lin((float)k->squelch_cdb * 0.02f);    /* power threshold 10^(dB/10) */
    d->sq_a = 1.0f / 62.5f;                                         /* 5 ms one-pole power average (PwmShaper: 5 ms rms) */
    d->sq_quiet = d->hold_samples;                                  /* start squelched: silence is an exact 50 % square wave */
    d->step = 2.0f / (float)arr;
    d->inv_step = (float)arr * 0.5f;
    uint32_t ri = arr == 100u ? 1u : (arr == 50u ? 2u : 0u);
    d->h1 = -(ntf_2cos[ri] + 1.0f);                                 /* ntf = (1 - z^-1)(1 - 2c z^-1 + z^-2): h = ntf[1:] */
    d->h2 = ntf_2cos[ri] + 1.0f;
    d->dither = 22695477u;                                          /* xorshift32 seed (determinism rules: fixed) */
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
NOINL static void fft_pack(const float *pcm, float *z)
{
    for (uint32_t i = 0; i < FW_DSP_NFFT; i++)
        z[i] = pcm[i] * hann[i];                                 /* z[2n] + j z[2n+1]: interleaved complex */
}

NOINL static void fft_bitrev(float *z)
{
    for (uint32_t p = 0; p < FW_DSP_BITREV_N; p += 2u) {
        uint32_t a = 2u * bitrev[p], b = 2u * bitrev[p + 1u];
        float tr = z[a], ti = z[a + 1u];
        z[a] = z[b];
        z[a + 1u] = z[b + 1u];
        z[b] = tr;
        z[b + 1u] = ti;
    }
}

NOINL static void fft_cfft128(float *z)
{
    for (uint32_t len = 2u, ts = 64u; len <= 128u; len <<= 1, ts >>= 1) {
        uint32_t half = len >> 1;
        for (uint32_t j = 0; j < half; j++) {
            float wr = tw128[2u * j * ts], wi = tw128[2u * j * ts + 1u];
            for (uint32_t i = j; i < 128u; i += len) {
                float *a = &z[2u * i], *b = &z[2u * (i + half)];
                float tr = wr * b[0] - wi * b[1];
                float ti = wr * b[1] + wi * b[0];
                float ar = a[0], ai = a[1];
                b[0] = ar - tr;
                b[1] = ai - ti;
                a[0] = ar + tr;
                a[1] = ai + ti;
            }
        }
    }
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
NOINL static void b_bands(fw_dsp_t *d, const float *z, float *fc)
{
    for (uint32_t b = 0; b < d->nb; b++) {
        d->E[b] = 0.0f;
        fc[b] = 0.0f;
    }
    for (uint32_t k = d->bin_lo; k < d->bin_hi; k++) {
        float p = (z[2u * k] * z[2u * k] + z[2u * k + 1u] * z[2u * k + 1u]) * eq2[k];
        uint32_t b = d->band_of_bin[k];
        d->E[b] += p;
        fc[b] += p * ((float)k * BIN_HZ);
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
        d->inc_new[b] = hz_to_inc(map_freq(d, cen));
    }
}

/* oscillator bank: ramp amplitude and phase increment across ramp_len samples (8 spec, 16 slim); 8 samples per hop */
NOINL static void b_synth(fw_dsp_t *d, float *y8)
{
    float inv_len = d->slim ? 0.0625f : 0.125f;
    for (uint32_t s = 0; s < 8u; s++)
        y8[s] = 0.0f;
    for (uint32_t b = 0; b < d->nb; b++) {
        float a0 = d->amp_prev[b], da = d->amp_new[b] - a0;
        int32_t di = (int32_t)(d->inc_new[b] - d->inc_prev[b]);
        uint32_t ph = d->phase[b], inc0 = d->inc_prev[b];
        for (uint32_t s = 0; s < 8u; s++) {
            uint32_t kk = d->ramp_pos + s + 1u;
            ph += inc0 + (uint32_t)(int32_t)(((int64_t)di * (int64_t)kk) >> d->ramp_shift);
            y8[s] += (a0 + da * ((float)kk * inv_len)) * fw_sin_turns(ph);
        }
        d->phase[b] = ph;
    }
    d->ramp_pos += 8u;
    if (d->ramp_pos >= d->ramp_len) {
        d->ramp_pos = 0u;
        for (uint32_t b = 0; b < d->nb; b++) {
            d->amp_prev[b] = d->amp_new[b];
            d->inc_prev[b] = d->inc_new[b];
        }
    }
}

static void algo_b(fw_dsp_t *d, float y8[8], float *band_energy, float *floor_tap)
{
    uint32_t idx = d->hops - 1u;                                 /* this hop's index */
    if (idx >= 1u && (!d->slim || (idx & 1u))) {                 /* a full 256-sample frame: spec every hop, slim every other */
        float z[FW_DSP_NFFT], fc[FW_DSP_NB_MAX];
        fft_pack(d->pcm, z);
        fft_bitrev(z);
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
NOINL static void a_mix(fw_dsp_t *d, const float *pcm)
{
    float *h = &d->a_hist[FW_DSP_A_NC - 1u];
    float z1 = d->a_z1, z2 = d->a_z2;
    uint32_t ph = d->a_lo_ph;
    for (uint32_t i = 0; i < HOP; i++) {
        float x = pcm[i] * 0x1p-30f * fw_sin_turns(ph + (1u << 30));   /* 2 x FS-scaled x cos(2 pi f_lo t) */
        ph += d->a_lo_inc;
        float y = a_hp[0] * x + z1;                              /* butter(2) HP, transposed direct form II */
        z1 = a_hp[1] * x - a_hp[3] * y + z2;
        z2 = a_hp[2] * x - a_hp[4] * y;
        h[i] = y;
    }
    d->a_z1 = z1;
    d->a_z2 = z2;
    d->a_lo_ph = ph;
}

NOINL static void a_decim(fw_dsp_t *d, float *y8)
{
    for (uint32_t q = 0; q < 8u; q++) {
        const float *x = &d->a_hist[16u * q + 15u];              /* oldest tap of output q: x[0..574] */
        float acc = a_c[287] * x[287];
        for (uint32_t j = 0; j < 287u; j++)
            acc += a_c[j] * (x[574u - j] + x[j]);
        y8[q] = acc;
    }
    for (uint32_t i = 0; i < FW_DSP_A_NC - 1u; i++)
        d->a_hist[i] = d->a_hist[HOP + i];
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
            g = sm > 0.0f ? (sm - fl * d->a_gate_lin) / sm : 0.0f;
            if (g < 0.0f)
                g = 0.0f;
            if (g > 1.0f)
                g = 1.0f;
        }
        y8[s] = y * g * d->gain_lin;
    }
}

void fw_dsp_algo(fw_dsp_t *d, const float pcm[128], float y8[8], float *band_energy, float *floor_tap)
{
    d->hops++;
    if (d->algo == (uint32_t)FW_ALGO_A) {
        a_mix(d, pcm);
        a_decim(d, y8);
        a_post(d, y8);
        if (band_energy != NULL && floor_tap != NULL)
            for (uint32_t b = 0; b < FW_DSP_NB_MAX; b++)
                band_energy[b] = floor_tap[b] = 0.0f;
        return;
    }
    for (uint32_t i = 0; i < HOP; i++) {
        d->pcm[i] = d->pcm[HOP + i];
        d->pcm[HOP + i] = pcm[i];
    }
    algo_b(d, y8, band_energy, floor_tap);
}

/* ------------------------------------------------------------------ output stage */
static float dither_u(uint32_t *s)
{
    uint32_t x = *s;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *s = x;
    return (float)(x >> 8) * 0x1p-24f;                          /* [0, 1) */
}

static int32_t floor_i(float v)
{
    int32_t i = (int32_t)v;
    return (float)i > v ? i - 1 : i;
}

NOINL size_t fw_dsp_out(fw_dsp_t *d, const float y8[8], uint32_t force_squelch, const fw_ccr_bounds_t *b, uint16_t *ccr, fw_out_info_t *info)
{
    size_t n = 0;
    float peak = 0.0f;
    uint32_t sq = 0u, sq_periods = 0u, hits = 0u;
    int32_t half = (int32_t)(d->arr / 2u);
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
        /* x16 polyphase interpolation */
        for (uint32_t t = FW_INTERP_TPP - 1u; t > 0u; t--)
            d->ihist[t] = d->ihist[t - 1u];
        d->ihist[0] = y;
        float v[UP], pk = 0.0f;
        for (uint32_t p = 0; p < UP; p++) {
            const float *c = &interp[p * FW_INTERP_TPP];
            float acc = 0.0f;
            for (uint32_t t = 0; t < FW_INTERP_TPP; t++)
                acc += c[t] * d->ihist[t];
            v[p] = acc;
            float a = fabsf(acc);
            pk = a > pk ? a : pk;
        }
        /* true-peak limiter at the ceiling (FWSIM-R14 F1): instant attack from the 16 interpolated samples, slow release;
         * |x| <= lim_c holds on every pre-quantiser sample by construction */
        float g = d->lim_g + d->lim_rel * (1.0f - d->lim_g);
        if (pk * g > d->lim_c)
            g = d->lim_c / pk;
        d->lim_g = g;
        for (uint32_t p = 0; p < UP; p++) {
            float x = sq ? 0.0f : v[p] * g;
            float a = fabsf(x);
            peak = a > peak ? a : peak;
            for (uint32_t r = 0; r < d->reps; r++) {
                float q;
                if (sq) {
                    d->e1 = d->e2 = d->e3 = 0.0f;                /* F2: shaper state zeroed while squelched */
                    q = 0.0f;
                    sq_periods++;
                } else {
                    float vv = x + d->h1 * d->e1 + d->h2 * d->e2 - d->e3;
                    float dz = d->dither_on ? (dither_u(&d->dither) - dither_u(&d->dither)) : 0.0f;
                    int32_t qi = floor_i((vv + dz * d->step) * d->inv_step + 0.5f);
                    if (qi > half)
                        qi = half;
                    if (qi < -half)
                        qi = -half;
                    q = (float)qi * d->step;
                    d->e3 = d->e2;
                    d->e2 = d->e1;
                    d->e1 = q - vv;
                }
                ccr[n++] = fw_ccr_from_amp(q, b, &hits);
            }
        }
    }
    if (info != NULL) {
        info->true_peak = peak;
        info->shaper_norm[0] = fabsf(d->e1);
        info->shaper_norm[1] = fabsf(d->e2);
        info->shaper_norm[2] = fabsf(d->e3);
        info->squelched = sq;
        info->squelched_periods = sq_periods;
        info->clamp_hits = hits;
    }
    return n;
}
