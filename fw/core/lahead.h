/* fw/core/lahead.h: look-ahead soft-knee peak limiter (12.5 kS/s domain) and the alert tone generator (loudness fix, 2026-10-08).
 * Limiter: per-sample required gain r = f(|x|)/|x|, f = soft knee (linear to knee*c, then T + (c-T) u/(1+u), asymptote c, never above c);
 * gain = moving average (4) of the 4-sample forward minimum of r, then a one-pole release; output delayed 3 samples. By construction
 * |out| <= c for every sample and the gain moves in bounded steps (no clicks, spec T6). Backstop: the x16 true-peak limiter and R64 clamp. */
#ifndef FW_CORE_LAHEAD_H
#define FW_CORE_LAHEAD_H
#include <stdint.h>

typedef struct {
    float c, knee, rel;        /* ceiling, knee start (absolute), release one-pole coefficient (per sample) */
    float g;                   /* applied gain state */
    float xh[3], rh[6];        /* input history (delay 3), required-gain history */
} fw_lahead_t;

void fw_lahead_init(fw_lahead_t *l, float ceiling, uint32_t knee_pct, float release_coef);
void fw_lahead_hop(fw_lahead_t *l, const float in[8], float out[8]);   /* out may alias in */

typedef struct {
    uint32_t ph, inc, pos, total, ramp;
    float amp;
} fw_alert_t;
void fw_alert_start(fw_alert_t *a, uint32_t hz, int32_t cdb, uint32_t ms);
/* fills y[8]; returns 1 while the alert is playing (y written), 0 otherwise (y untouched) */
uint32_t fw_alert_hop(fw_alert_t *a, float y[8]);
#endif
