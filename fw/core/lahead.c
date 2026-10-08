/* fw/core/lahead.c: see lahead.h */
#include "lahead.h"
#include "dsp_math.h"

#define ALERT_RAMP 125u   /* 10 ms at 12.5 kS/s */

void fw_lahead_init(fw_lahead_t *l, float ceiling, uint32_t knee_pct, float release_coef)
{
    l->c = ceiling;
    l->knee = ceiling * (float)knee_pct * 0.01f;
    l->rel = release_coef;
    l->g = 1.0f;
    for (uint32_t i = 0; i < 3u; i++)
        l->xh[i] = 0.0f;
    for (uint32_t i = 0; i < 6u; i++)
        l->rh[i] = 1.0f;
}

static float req_gain(const fw_lahead_t *l, float x)
{
    float a = x < 0.0f ? -x : x;
    if (!(a > l->knee))
        return 1.0f;
    float w = l->c - l->knee;
    float u = (a - l->knee) / w;
    return (l->knee + w * (u / (1.0f + u))) / a;
}

void fw_lahead_hop(fw_lahead_t *l, const float in[8], float out[8])
{
    float X[11], R[14], M[11];                   /* X[k] = input at index k-3, R[k] = required gain at index k-6 */
    for (uint32_t k = 0; k < 3u; k++)
        X[k] = l->xh[k];
    for (uint32_t k = 0; k < 6u; k++)
        R[k] = l->rh[k];
    for (uint32_t k = 0; k < 8u; k++) {
        X[3u + k] = in[k];
        R[6u + k] = req_gain(l, in[k]);
    }
    for (uint32_t u = 0; u < 11u; u++) {         /* m(u) = min R over [u, u+3] (index u-6) */
        float m = R[u];
        for (uint32_t j = 1; j < 4u; j++)
            m = R[u + j] < m ? R[u + j] : m;
        M[u] = m;
    }
    for (uint32_t i = 0; i < 8u; i++) {          /* output i <- input index i-3: G = mean m(i-6 .. i-3) in M offsets 0..3 + i */
        float G = 0.25f * (M[i] + M[i + 1u] + M[i + 2u] + M[i + 3u]);
        float gr = l->g + l->rel * (1.0f - l->g);
        l->g = G < gr ? G : gr;
        out[i] = X[i] * l->g;                    /* X[i] is input index i-3 */
    }
    for (uint32_t k = 0; k < 3u; k++)
        l->xh[k] = X[8u + k];
    for (uint32_t k = 0; k < 6u; k++)
        l->rh[k] = R[8u + k];
}

void fw_alert_start(fw_alert_t *a, uint32_t hz, int32_t cdb, uint32_t ms)
{
    a->ph = 0u;
    a->inc = (uint32_t)((((uint64_t)hz << 32) + 6250u) / 12500u);
    a->pos = 0u;
    a->total = ms * 25u / 2u;                    /* ms x 12.5 samples */
    a->ramp = a->total < 2u * ALERT_RAMP ? a->total / 2u : ALERT_RAMP;
    a->amp = fw_db20_to_lin((float)cdb * 0.01f);
    a->period = 0u;
    a->pulse = 0u;
}

void fw_haptic_start(fw_alert_t *a, uint32_t hz, int32_t cdb, uint32_t n, uint32_t pulse_ms, uint32_t gap_ms)
{
    fw_alert_start(a, hz, cdb, pulse_ms);
    a->pulse = pulse_ms * 25u / 2u;
    a->period = (pulse_ms + gap_ms) * 25u / 2u;
    a->total = (n - 1u) * a->period + a->pulse;
    a->ramp = a->pulse < 2u * ALERT_RAMP ? a->pulse / 2u : ALERT_RAMP;
}

uint32_t fw_alert_hop(fw_alert_t *a, float y[8])
{
    if (a->pos >= a->total)
        return 0u;
    for (uint32_t i = 0; i < 8u; i++) {
        float e = 1.0f;
        if (a->pos >= a->total) {
            y[i] = 0.0f;
            continue;
        }
        uint32_t p0 = 0u, pl = a->total;                 /* position inside the current pulse, pulse length */
        if (a->period != 0u) {
            p0 = a->pos % a->period;
            pl = a->pulse;
            if (p0 >= pl) {                              /* gap between pulses: silence, phase restarts at 0 */
                a->ph = 0u;
                y[i] = 0.0f;
                a->pos++;
                continue;
            }
        } else {
            p0 = a->pos;
        }
        if (a->ramp != 0u) {
            uint32_t d = p0 < a->ramp ? p0 : (p0 + a->ramp >= pl ? pl - p0 : a->ramp);
            if (d < a->ramp) {
                float s = fw_sin_turns((uint32_t)(((uint64_t)d << 30) / a->ramp));   /* quarter turn */
                e = s * s;
            }
        }
        a->ph += a->inc;
        y[i] = a->amp * e * fw_sin_turns(a->ph);
        a->pos++;
    }
    return 1u;
}
