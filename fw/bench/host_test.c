/* fw/bench/host_test.c - functional check of the counted kernels on the host (make test).
 * Prints the 256-pt real FFT of a fixed test frame; host_test.py compares it with numpy.rfft
 * and runs one algorithm-B hop + output hop for crashes / NaNs. Not a cycle measurement. */
#include "kernels.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    static cpx x[NC], tw[NC / 2], twr[NC / 2];
    static uint8_t pairs[2 * 64];
    int np = 0;
    for (int i = 0; i < NC; i++) {
        int r = 0;
        for (int b = 0; b < 7; b++) r |= ((i >> b) & 1) << (6 - b);
        if (r > i) { pairs[2 * np] = (uint8_t)i; pairs[2 * np + 1] = (uint8_t)r; np++; }
    }
    for (int m = 0; m < NC / 2; m++) {
        tw[m].re = (float)cos(2 * M_PI * m / NC);   tw[m].im = (float)-sin(2 * M_PI * m / NC);
        twr[m].re = (float)cos(2 * M_PI * m / NFFT); twr[m].im = (float)-sin(2 * M_PI * m / NFFT);
    }
    /* test frame through in_window: ADF words of a 40 kHz + 61 kHz tone, Hann window */
    static int32_t adf[NFFT];
    static float win[NFFT], buf[NFFT];
    for (int i = 0; i < NFFT; i++) {
        double v = 0.5 * sin(2 * M_PI * 40e3 * i / 200.02e3) + 0.25 * sin(2 * M_PI * 61e3 * i / 200.02e3 + 1.0);
        adf[i] = (int32_t)lrint(v * 8388607.0) * 256;
        win[i] = (float)((0.5 - 0.5 * cos(2 * M_PI * i / NFFT)) / 8388608.0);
    }
    in_window(adf, win, buf);
    memcpy(x, buf, sizeof buf);
    bitrev128(x, pairs, np);
    cfft128(x, tw);
    rsplit256(x, twr);
    printf("npairs %d\n", np);
    for (int k = 0; k < NC; k++) printf("%d %.7g %.7g\n", k, x[k].re, x[k].im);

    /* one B hop + output hop: no NaN, CCR in range */
    static bstate s; static ostate o; static float sintab[SINTAB], eq2[NBIN], fbin[NBIN], y8[OUT_HOP];
    static uint8_t band[NBIN]; static float hpoly[UP * TPP]; static uint16_t ccr[OUT_HOP * UP];
    for (int i = 0; i < SINTAB; i++) sintab[i] = (float)sin(2 * M_PI * i / SINTAB);
    for (int k = 0; k < NBIN; k++) { eq2[k] = 1.0f; fbin[k] = (BIN_LO + k) * 781.33f; band[k] = (uint8_t)(k * NB / NBIN); }
    for (int i = 0; i < UP * TPP; i++) hpoly[i] = 1.0f / TPP;
    s.a_up = 0.0002f; s.a_dn = 0.002f; s.gate = 4.0f; s.gain = 30.0f; s.a_att = 0.35f; s.a_rel = 0.04f;
    s.ln_lo = log2f(20e3f); s.k_map = 1.0f / log2f(85e3f / 20e3f); s.out_lo_inc = 1500.0f / 12500.0f * 4294967296.0f;
    o.c = 0.25f; o.g = 1.0f; o.a_rel = 0.002f; o.h1 = 1.0f; o.h2 = -1.0f; o.h3 = 0.5f;
    o.step = 2.0f / 200.0f; o.inv_step = 100.0f; o.half_levels = 100.0f; o.sq_a = 0.01f; o.lcg = 1;
    b_bands(x, eq2, fbin, band, &s);
    b_update(&s);
    b_synth(&s, sintab, y8);
    out_hop(y8, hpoly, &o, ccr);
    int bad = 0;
    for (int i = 0; i < OUT_HOP; i++) bad += !isfinite(y8[i]);
    for (int i = 0; i < OUT_HOP * UP; i++) bad += ccr[i] > 200;
    printf("bhop_bad %d inc0 %u\n", bad, s.incn[0]);
    return 0;
}
