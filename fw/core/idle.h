/* fw/core/idle.h: idle-listening wake detector (spec C9) = sim/dsp/pipeline.py idle_detector_fft rev 2 with its defaults: a 256-point
 * Hann FFT snapshot every 8 hops (5.12 ms; the reference uses 5 ms), per-bin slow floors (up 3 s, down 1 s) over the 20-85 kHz bins,
 * hit = best bin >= 15 dB over its floor AND >= 10 dB over the band's median bin ratio; 0.3 s hang. Drives FW_FE_QUIET / FW_FE_WAKE. */
#ifndef FW_CORE_IDLE_H
#define FW_CORE_IDLE_H
#include <stdint.h>

#include "dsp.h"

#define FW_IDLE_EVERY 8u                  /* hops per snapshot */
#define FW_IDLE_NBIN 83u                  /* bins 26..108 = 20.3-84.4 kHz (f_lo <= f < f_hi) */

typedef struct {
    float bfloor[FW_IDLE_NBIN];
    float b_up, om_b_up, b_dn, om_b_dn, thr, peak;
    uint32_t init, hang, hang_hops, active, frames, hits, bin0;
    float pcm[256];                       /* the detector's own ring of the CURRENT samples (the algorithm may run on a delayed stream) */
    uint32_t hops, pcm_old;
} fw_idle_t;

void fw_idle_init(fw_idle_t *s);
/* call every hop with the hop's PCM; returns 1 when a snapshot was evaluated this hop */
uint32_t fw_idle_hop(fw_idle_t *s, const fw_dsp_t *d, const float pcm[128]);
#endif
