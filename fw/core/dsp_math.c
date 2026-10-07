#include "dsp_math.h"

#include <string.h>

#include "dsp_tables.h"

static const float sin_tab[FW_DSP_SIN_N] = FW_DSP_SIN_INIT;

#define LN2_F 0x1.62e430p-1f      /* ln 2 */
#define LOG2E_F 0x1.715476p+0f    /* 1 / ln 2 */
#define LOG2_10_F 0x1.a934f0p+1f  /* log2(10) */

float fw_log2f(float x)
{
    uint32_t b;
    memcpy(&b, &x, sizeof b);
    int32_t e = (int32_t)((b >> 23) & 0xFFu) - 127;
    if (!(x > 0.0f) || e == -127 || e == 128)
        return -126.0f;
    b = (b & 0x007FFFFFu) | (127u << 23);    /* mantissa in [1, 2) */
    float m;
    memcpy(&m, &b, sizeof m);
    if (m > 1.41421356f) {
        m *= 0.5f;
        e += 1;
    }
    float s = (m - 1.0f) / (m + 1.0f);       /* |s| <= 0.1716 */
    float s2 = s * s;
    float p = 1.0f + s2 * (0x1.555556p-2f + s2 * (0.2f + s2 * (0x1.249250p-3f + s2 * 0x1.c71c72p-4f)));
    return (float)e + 2.0f * s * p * LOG2E_F;
}

float fw_exp2f(float x)
{
    if (x < -126.0f)
        x = -126.0f;
    if (x > 127.0f)
        x = 127.0f;
    int32_t n = (int32_t)(x + (x >= 0.0f ? 0.5f : -0.5f));   /* round half away from zero */
    float t = (x - (float)n) * LN2_F;                         /* |t| <= 0.347 */
    float p = 1.0f + t * (1.0f + t * (0.5f + t * (0x1.555556p-3f + t * (0x1.555556p-5f + t * (0x1.111112p-7f + t * (0x1.6c16c2p-10f + t * 0x1.a01a02p-13f))))));
    if (n < -126)                                              /* 2^n would be subnormal: FTZ semantics */
        return 0.0f;
    uint32_t b = (uint32_t)(n + 127) << 23;
    float sc;
    memcpy(&sc, &b, sizeof sc);
    return p * sc;
}

float fw_db20_to_lin(float db)
{
    return fw_exp2f(db * (LOG2_10_F / 20.0f));
}

float fw_om_exp(float x)
{
    if (x <= 0.0f)
        return 0.0f;
    if (x < 0.5f)   /* Taylor to x^8: rel err < 1e-8 at 0.5 */
        return x * (1.0f - x * (0.5f - x * (0x1.555556p-3f - x * (0x1.555556p-5f - x * (0x1.111112p-7f - x * (0x1.6c16c2p-10f - x * (0x1.a01a02p-13f - x * 0x1.a01a02p-16f)))))));
    return 1.0f - fw_exp2f(-x * LOG2E_F);
}

float fw_sin_turns(uint32_t ph)
{
    uint32_t i = ph >> 22;                                    /* 1024 entries */
    float f = (float)(ph & 0x3FFFFFu) * 0x1p-22f;
    float a = sin_tab[i];
    return a + f * (sin_tab[i + 1u] - a);
}
