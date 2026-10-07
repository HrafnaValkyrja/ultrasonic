#include "fmac_model.h"

int32_t fw_fmac_mac_floor8(int32_t prod)
{
    return prod >= 0 ? prod >> 8 : -(int32_t)((uint32_t)(-(prod + 1)) >> 8) - 1;   /* floor(prod / 256) without implementation-defined >> */
}

static int32_t wrap26(int32_t v)
{
    uint32_t u = (uint32_t)v & 0x03FFFFFFu;
    return (u & 0x02000000u) ? (int32_t)(u | 0xFC000000u) : (int32_t)u;
}

int16_t fw_fmac_model_fir1(const int16_t *coef, uint32_t taps, uint32_t r_gain, const int16_t *x_newest)
{
    int32_t acc = 0;
    for (uint32_t k = 0; k < taps; k++)                                  /* modular sum: order does not matter */
        acc = wrap26(acc + fw_fmac_mac_floor8((int32_t)coef[k] * (int32_t)x_newest[-(int32_t)k]));
    int64_t g = (int64_t)acc * (int64_t)(1u << r_gain);                  /* 2^R gain, no overflow in 64 bits */
    int64_t o = g >= 0 ? g / 128 : -((-g + 127) / 128);                  /* A2: floor(g / 2^7) */
    if (o > 32767)                                                        /* CLIPEN = 1 */
        o = 32767;
    if (o < -32768)
        o = -32768;
    return (int16_t)o;
}

void fw_fmac_model_bank(const int16_t *coef, uint32_t n_phase, uint32_t taps, uint32_t r_gain, const int16_t *x, uint32_t n_new, int16_t *y)
{
    for (uint32_t s = 0; s < n_new; s++)
        for (uint32_t p = 0; p < n_phase; p++)
            y[s * n_phase + p] = fw_fmac_model_fir1(&coef[p * taps], taps, r_gain, &x[taps - 1u + s]);
}
