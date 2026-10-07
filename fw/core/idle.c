#include "idle.h"

#include <string.h>

#include "dsp_math.h"

void fw_idle_init(fw_idle_t *s)
{
    memset(s, 0, sizeof *s);
    float hop_s = (float)(FW_IDLE_EVERY * 128u) / 200000.0f;
    s->om_b_up = fw_om_exp(hop_s / 3.0f);
    s->om_b_dn = fw_om_exp(hop_s / 1.0f);
    s->b_up = 1.0f - s->om_b_up;
    s->b_dn = 1.0f - s->om_b_dn;
    s->thr = fw_db20_to_lin(30.0f);             /* 10^(15/10) */
    s->peak = fw_db20_to_lin(20.0f);            /* 10^(10/10) */
    s->hang_hops = (uint32_t)(0.3f / hop_s);    /* int(hang_s / hop_s) as the reference */
    s->bin0 = 26u;                              /* 26 x 781.25 = 20.3 kHz >= 20 kHz; 108 x 781.25 = 84.4 kHz < 85 kHz */
}

/* median of n floats (n odd) by an insertion sort of a copy: n = 83, every 5 ms */
static float median(float *v, uint32_t n)
{
    for (uint32_t i = 1; i < n; i++) {
        float x = v[i];
        uint32_t j = i;
        while (j > 0u && v[j - 1u] > x) {
            v[j] = v[j - 1u];
            j--;
        }
        v[j] = x;
    }
    return v[n / 2u];
}

uint32_t fw_idle_hop(fw_idle_t *s, const fw_dsp_t *d, const float pcm[128])
{
    s->hops++;
    uint32_t w = (s->hops & 1u) * 128u;
    s->pcm_old = w ^ 128u;
    for (uint32_t i = 0; i < 128u; i++)
        s->pcm[w + i] = pcm[i];
    if (s->hops < 2u || (s->hops % FW_IDLE_EVERY) != 0u)
        return 0u;
    float p[129], r[FW_IDLE_NBIN];
    fw_dsp_spectrum(d, s->pcm, s->pcm_old, p);
    const float *pb = &p[s->bin0];
    if (!s->init) {
        for (uint32_t i = 0; i < FW_IDLE_NBIN; i++)
            s->bfloor[i] = pb[i] + 1e-30f;
        s->init = 1u;
    }
    float rmax = 0.0f;
    for (uint32_t i = 0; i < FW_IDLE_NBIN; i++) {
        float f = s->bfloor[i];
        r[i] = pb[i] / f;
        rmax = r[i] > rmax ? r[i] : rmax;
        s->bfloor[i] = pb[i] > f ? s->b_up * f + s->om_b_up * pb[i] : s->b_dn * f + s->om_b_dn * pb[i];
    }
    float med = median(r, FW_IDLE_NBIN);
    uint32_t hit = rmax > s->thr && rmax > s->peak * med;
    s->hits += hit;
    s->hang = hit ? s->hang_hops : (s->hang > 0u ? s->hang - 1u : 0u);
    s->active = s->hang > 0u;
    s->frames++;
    return 1u;
}
