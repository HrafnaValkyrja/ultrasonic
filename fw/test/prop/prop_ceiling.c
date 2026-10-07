/* fw/test/prop/prop_ceiling.c: FWSIM-R15 D17 ceiling property test (fwsim stage dsp.ceiling_property). Not in the unit-test binary
 * (it has its own main and runs >= 1e6 hops). Adversarial input at the mic words: full-scale 20-85 kHz tones, full-scale white noise
 * (AOP), steps, chirps, alternating full-scale bursts, silence gaps; segments of random length; every volume step; B spec, B slim, A;
 * ARR 200 / 100 / 50. Checks every hop:
 *   (a) pre-quantiser x16 true peak (tap FWSIM-R10) <= 10^(ceiling/20) + 1e-6
 *   (b) max |2 CCR/ARR - 1| <= 10^(ceiling/20) + 7.67 x 1.5 LSB / (ARR/2)   (0.366 at -12 dBFS, ARR 200)
 *   (c) the FWSIM-R64 current clamp never engages (clamp_hits == 0: the shaper output is never clipped)
 * Prints one JSON line; exit 1 on any violation. */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#if defined(__SSE__)
#include <xmmintrin.h>
#endif

#include "fw.h"

static uint32_t rs = 0x1234567u;
static uint32_t rnd(void)
{
    rs ^= rs << 13;
    rs ^= rs >> 17;
    rs ^= rs << 5;
    return rs;
}
static double urand(void) { return (double)(rnd() >> 8) / 16777216.0; }

static int32_t word(double x)   /* FS float -> DR word, saturating */
{
    if (x > 1.0 - 1.0 / 8388608.0) x = 1.0 - 1.0 / 8388608.0;
    if (x < -1.0) x = -1.0;
    return (int32_t)lrint(x * 8388608.0) * 256;
}

typedef struct { const char *name; int32_t algo, bvar, khz; uint32_t hops; } cfg_t;

int main(int argc, char **argv)
{
#if defined(__SSE__)
    _mm_setcsr(_mm_getcsr() | 0x8040u);
#endif
    double scale = argc > 1 ? atof(argv[1]) : 1.0;          /* hop budget multiplier (1.0 -> 1.36e6 hops) */
    static const cfg_t cfgs[] = {{"B", 2, 0, 200, 1000000u}, {"slim", 2, 1, 200, 120000u}, {"A", 1, 0, 200, 120000u},
                                 {"B_400k", 2, 0, 400, 60000u}, {"B_800k", 2, 0, 800, 60000u}};
    static fw_state_t st;
    uint64_t total = 0, viol_a = 0, viol_b = 0, viol_c = 0;
    double worst_a = 0.0, worst_b = 0.0;
    printf("{\"rows\": [");
    for (size_t ci = 0; ci < sizeof cfgs / sizeof cfgs[0]; ci++) {
        const cfg_t *c = &cfgs[ci];
        uint32_t hops = (uint32_t)(c->hops * scale);
        double cmax_a = 0.0, cmax_b = 0.0;
        int32_t vmin = fw_knob_meta[FW_KNOB_volume_cdb].min, vmax = fw_knob_meta[FW_KNOB_volume_cdb].max;
        int32_t step = fw_knob_meta[FW_KNOB_volume_step_cdb].def;
        uint32_t nvol = (uint32_t)((vmax - vmin) / step + 1);
        uint32_t per_vol = hops / nvol + 1u;
        for (uint32_t vi = 0; vi < nvol; vi++) {
            fw_knobs_t k;
            fw_knobs_defaults(&k);
            fw_knob_set(&k, FW_KNOB_algo, c->algo);
            fw_knob_set(&k, FW_KNOB_b_variant, c->bvar);
            fw_knob_set(&k, FW_KNOB_pwm_khz, c->khz);
            fw_knob_set(&k, FW_KNOB_volume_cdb, vmin + (int32_t)vi * step);
            fw_knob_set(&k, FW_KNOB_transient_only, (int32_t)(vi & 1u));
            fw_init(&st, &k, 0u);
            double ceil_lin = pow(10.0, k.ceiling_cdb / 2000.0);
            double bound_b = ceil_lin + 7.67 * 1.5 / (st.arr / 2.0);
            int32_t in[FW_HOP_N];
            uint16_t ccr[FW_CCR_MAX_PER_HOP];
            fw_taps_t t;
            uint32_t seg_left = 0, kind = 0;
            double f0 = 0, f1 = 0, ph = 0, amp = 1.0;
            uint64_t n = 0;
            for (uint32_t h = 0; h < per_vol; h++) {
                fw_poll(&st, (uint64_t)st.hop_count * 640u);
                if (seg_left == 0) {
                    kind = rnd() % 6u;
                    seg_left = 20u + rnd() % 200u;
                    f0 = 20e3 + 65e3 * urand();
                    f1 = 20e3 + 65e3 * urand();
                    amp = urand() < 0.5 ? 1.0 : pow(10.0, -40.0 * urand() / 20.0);
                }
                seg_left--;
                for (uint32_t i = 0; i < FW_HOP_N; i++, n++) {
                    double x;
                    switch (kind) {
                    case 0: ph += 2 * M_PI * f0 / 200e3; x = amp * sin(ph); break;                          /* tone */
                    case 1: x = amp * (2.0 * urand() - 1.0); break;                                       /* white, full scale */
                    case 2: x = ((n / (64u + (rnd() & 1023u))) & 1u) ? amp : -amp; break;                 /* steps */
                    case 3: { double fr = f0 + (f1 - f0) * (double)(seg_left % 50u) / 50.0;              /* chirp */
                              ph += 2 * M_PI * fr / 200e3; x = amp * sin(ph); } break;
                    case 4: ph += 2 * M_PI * f0 / 200e3; x = ((n / 200u) & 1u) ? amp * sin(ph) : 0.0; break; /* alternating bursts */
                    default: x = 0.0; break;                                                               /* silence */
                    }
                    in[i] = word(x);
                }
                size_t m = fw_hop(&st, in, ccr, FW_CCR_MAX_PER_HOP, &t);
                double pk = t.pre_q_true_peak;
                if (pk > cmax_a) cmax_a = pk;
                if (pk > ceil_lin + 1e-6) viol_a++;
                for (size_t j = 0; j < m; j++) {
                    double a = fabs(2.0 * ccr[j] / st.arr - 1.0);
                    if (a > cmax_b) cmax_b = a;
                    if (a > bound_b + 1e-9) viol_b++;
                }
                if (t.clamp_hits) viol_c++;
                total++;
            }
            if (cmax_a > worst_a) worst_a = cmax_a;
        }
        if (cmax_b > worst_b && c->khz == 200) worst_b = cmax_b;
        printf("%s{\"cfg\": \"%s\", \"hops\": %u, \"true_peak_max\": %.7f, \"ccr_amp_max\": %.5f}", ci ? ", " : "", c->name, per_vol * nvol, cmax_a, cmax_b);
    }
    double ceil0 = pow(10.0, -1200 / 2000.0);
    printf("], \"total_hops\": %llu, \"ceiling\": %.7f, \"true_peak_max\": %.7f, \"ccr_amp_max_arr200\": %.5f, \"bound_b_arr200\": %.5f, "
           "\"viol_a\": %llu, \"viol_b\": %llu, \"viol_c\": %llu}\n",
           (unsigned long long)total, ceil0, worst_a, worst_b, ceil0 + 7.67 * 1.5 / 100.0, (unsigned long long)viol_a, (unsigned long long)viol_b,
           (unsigned long long)viol_c);
    return (viol_a || viol_b || viol_c || total < 1000000u * scale) ? 1 : 0;
}
