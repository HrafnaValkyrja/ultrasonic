/* FWSIM-R64 output current clamp + the -12 dBFS ceiling hard clamp (FWSIM-R6). Property test over amplitude x ARR x knob. */
#include <math.h>

#include "fw.h"
#include "out_clamp.h"
#include "tf.h"
#include "tests.h"
#include "variant_config.h"

static int within(uint16_t c, uint16_t arr, uint32_t ppm)
{
    /* |2c/arr - 1| <= ppm/1e6, exact in integers: |2e6 c - 1e6 arr| <= ppm arr */
    int64_t d = 2000000LL * c - 1000000LL * arr;
    if (d < 0)
        d = -d;
    return d <= (int64_t)ppm * arr;
}

void test_clamp_property(void)
{
    static const uint16_t arrs[3] = {200, 100, 50};
    static const int32_t knob_ma[4] = {0, 79, 150, FW_VAR_I_PEAK_MA_MAX};
    uint32_t viol = 0, n = 0;
    for (int ai = 0; ai < 3; ai++)
        for (int ki = 0; ki < 4; ki++) {
            fw_knobs_t k;
            fw_knobs_defaults(&k);
            TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_out_i_peak_ma, knob_ma[ki]), FW_KNOB_OK);
            uint32_t ppm = fw_out_amp_max_ppm(&k);
            TF_CHECK(ppm <= FW_VAR_AMP_MAX_PPM);
            fw_ccr_bounds_t b = fw_ccr_bounds(arrs[ai], ppm);
            uint32_t hits = 0;
            for (int32_t i = -40000; i <= 40000; i++) {          /* a in [-4, 4] step 1e-4: full scale, overdrive */
                float a = (float)i * 1e-4f;
                uint16_t c = fw_ccr_from_amp(a, &b, &hits);
                n++;
                if (!within(c, arrs[ai], ppm) || c > arrs[ai])
                    viol++;
            }
            float odd[6] = {NAN, INFINITY, -INFINITY, 1e30f, -1e30f, 1e-45f};
            for (int j = 0; j < 6; j++) {
                uint16_t c = fw_ccr_from_amp(odd[j], &b, &hits);
                n++;
                if (!within(c, arrs[ai], ppm))
                    viol++;
            }
            TF_CHECK_EQ(fw_ccr_from_amp(NAN, &b, &hits), arrs[ai] / 2u);
            TF_CHECK(hits > 0u);
        }
    TF_CHECK_EQ(viol, 0);
    TF_CHECK(n > 900000u);
}

void test_clamp_hard_limits(void)
{
    fw_knobs_t k;
    fw_knobs_defaults(&k);
    /* the knob can lower the current clamp, never raise it */
    TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_out_i_peak_ma, FW_VAR_I_PEAK_MA_MAX + 1), FW_KNOB_ERANGE);
    k.out_i_peak_ma = 100000;                              /* corrupted struct */
    TF_CHECK_EQ(fw_out_amp_max_ppm(&k), FW_VAR_AMP_MAX_PPM);
    /* bounds builder caps an oversized request too */
    fw_ccr_bounds_t b = fw_ccr_bounds(200, 1000000u);
    TF_CHECK_EQ(b.amp_ppm, FW_VAR_AMP_MAX_PPM);
    TF_CHECK(b.lo > 0u && b.hi < 200u);
    /* the ceiling knob cannot pass -12 dBFS, the self-test cap neither */
    TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_ceiling_cdb, -1199), FW_KNOB_ERANGE);
    TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_ceiling_cdb, -1200), FW_KNOB_OK);
    TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_selftest_cap_cdb, -1100), FW_KNOB_ERANGE);
    /* the ceiling (true-peak target) + the FWSIM-R15 shaper excursion sit below the current clamp: music never hits it */
    TF_CHECK(HC_CEILING_PEAK_PPM + FW_SHAPER_EXCURSION_PPM < FW_VAR_AMP_MAX_PPM);
    /* numbers of fw/variants.yaml: Phase-2 175 mAh 270 mA, K1 130 mAh 208 mA */
#if FW_CELL == FW_CELL_PH2_175
    TF_CHECK_EQ(FW_VAR_I_PEAK_MA_MAX, 270);
#elif FW_CELL == FW_CELL_K1_130
    TF_CHECK_EQ(FW_VAR_I_PEAK_MA_MAX, 208);
#endif
    TF_CHECK_EQ(fw_amp_ppm_for_ma(FW_VAR_I_PEAK_MA_MAX) / 1000u, FW_VAR_AMP_MAX_PPM / 1000u);
}

void test_clamp_db_table(void)
{
    TF_CHECK(fabsf(fw_db_to_amp(-1200) - 0.25118864f) < 1e-6f);
    TF_CHECK(fabsf(fw_db_to_amp(-600) - 0.50118723f) < 1e-6f);
    TF_CHECK(fw_db_to_amp(0) == 1.0f);
    TF_CHECK(fw_db_to_amp(500) == 1.0f);
    TF_CHECK(fw_db_to_amp(-9000) > 0.0f && fw_db_to_amp(-9000) < 1.1e-4f);
    float prev = 0.0f;
    for (int32_t c = -8000; c <= 0; c += 10) {
        float a = fw_db_to_amp(c);
        TF_CHECK(a > prev);
        prev = a;
    }
}

/* the shaper's integer CCR path bounds exactly like the float path (FWSIM-R64: fw_ccr_from_level == fw_ccr_from_amp(2 qi / ARR)) */
void test_clamp_level_matches_amp(void)
{
    static const uint16_t arrs[3] = {200u, 100u, 50u};
    static const uint32_t ppm[3] = {1000000u, 635300u, 251189u};
    uint32_t bad = 0;
    for (int a = 0; a < 3; a++)
        for (int p = 0; p < 3; p++) {
            fw_ccr_bounds_t b = fw_ccr_bounds(arrs[a], ppm[p]);
            for (int32_t qi = -(int32_t)arrs[a] / 2; qi <= (int32_t)arrs[a] / 2; qi++) {
                uint32_t h1 = 0, h2 = 0;
                uint16_t c1 = fw_ccr_from_level(qi, &b, &h1);
                uint16_t c2 = fw_ccr_from_amp((float)qi * (2.0f / (float)arrs[a]), &b, &h2);
                bad += c1 != c2 || h1 != h2;
            }
        }
    TF_CHECK_EQ(bad, 0);
}
