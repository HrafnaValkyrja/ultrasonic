/* sim/fw/shim.c: ctypes surface of the host firmware build (sim/fw/fwlib.py). Not firmware: a batch driver around the pure entry
 * points (fw_init, fw_poll, fw_hop, fw_hop_d2) so Python can run whole scenes in one call. Time is injected: hop k at k * 640 us
 * + t0_us (sim rate 200 kS/s; hardware 200.02 kS/s). t0_us >= 300000 = powered on long before the scene (hold over). */
#include <string.h>

#include "fw.h"

size_t shim_state_size(void) { return sizeof(fw_state_t); }
uint32_t shim_abi(void) { return FW_ABI_VERSION; }

int32_t shim_knob_id(const char *name)
{
    for (uint32_t i = 0; i < (uint32_t)FW_KNOB_COUNT; i++)
        if (strcmp(fw_knob_meta[i].name, name) == 0)
            return (int32_t)i;
    return -1;
}

/* defaults + overrides; returns 0 or (1 + index) of the first rejected override */
int32_t shim_init(fw_state_t *st, const int32_t *ids, const int32_t *vals, int32_t n)
{
    fw_knobs_t k;
    fw_knobs_defaults(&k);
    for (int32_t i = 0; i < n; i++)
        if (fw_knob_set(&k, (uint32_t)ids[i], vals[i]) != FW_KNOB_OK)
            return 1 + i;
    fw_init(st, &k, 0u);
    return 0;
}

int32_t shim_set_noise(fw_state_t *st, const float *nb, uint32_t n) { return fw_set_noise_cal(st, nb, n); }
uint32_t shim_hash(const fw_state_t *st) { return fw_state_hash(st); }
uint32_t shim_ccr_per_hop(const fw_state_t *st) { return FW_HOP_N * 200u / st->arr; }

/* n_hops hops of words (128 per hop for D1, 256 for D2). Outputs (each may be NULL): ccr[n_hops * ccr_per_hop],
 * dsp[n_hops * 8], band[n_hops * 28], floor_[n_hops * 28], peak[n_hops], sq[n_hops], norm[n_hops * 3], sq_periods[n_hops] */
int32_t shim_run(fw_state_t *st, const int32_t *words, uint32_t n_hops, int32_t d2, uint16_t *ccr, float *dsp, float *band,
                 float *floor_, float *peak, uint32_t *sq, float *norm, uint32_t *clamp, uint64_t t0_us)
{
    fw_taps_t t;
    uint16_t buf[FW_CCR_MAX_PER_HOP];
    for (uint32_t h = 0; h < n_hops; h++) {
        fw_poll(st, t0_us + (uint64_t)st->hop_count * 640u);   /* t0_us: time since power-on at the first hop */
        size_t n = d2 ? fw_hop_d2(st, &words[(size_t)h * 256u], buf, FW_CCR_MAX_PER_HOP, &t)
                      : fw_hop(st, &words[(size_t)h * 128u], buf, FW_CCR_MAX_PER_HOP, &t);
        if (n == 0u)
            return -1;
        if (ccr) memcpy(&ccr[(size_t)h * n], buf, n * sizeof buf[0]);
        if (dsp) memcpy(&dsp[(size_t)h * 8u], t.dsp_out, sizeof t.dsp_out);
        if (band) memcpy(&band[(size_t)h * 28u], t.band_energy, sizeof t.band_energy);
        if (floor_) memcpy(&floor_[(size_t)h * 28u], t.floor, sizeof t.floor);
        if (peak) peak[h] = t.pre_q_true_peak;
        if (sq) sq[h] = t.squelch_state;
        if (norm) memcpy(&norm[(size_t)h * 3u], t.shaper_norm, sizeof t.shaper_norm);
        if (clamp) clamp[h] = t.clamp_hits;
    }
    return 0;
}

/* output stage only (interpolator, limiter, squelch, shaper) on a 12.5 kS/s stream, 8 samples per hop: the firmware drop-in for
 * stages.PwmShaper when a scenario feeds the shaper directly (chain.image_tone_test). No power-on hold. */
int32_t shim_out(fw_state_t *st, const float *y, uint32_t n_hops, uint16_t *ccr, float *peak, uint32_t *sqp)
{
    fw_ccr_bounds_t b = fw_ccr_bounds((uint16_t)st->arr, st->amp_max_ppm);
    uint32_t per = FW_HOP_N * 200u / st->arr;
    for (uint32_t h = 0; h < n_hops; h++) {
        fw_out_info_t oi;
        (void)fw_dsp_out(&st->dsp, &y[(size_t)h * 8u], 0u, &b, &ccr[(size_t)h * per], &oi);
        if (peak) peak[h] = oi.true_peak;
        if (sqp) sqp[h] = oi.squelched_periods;
    }
    return 0;
}
