/* FWSIM-R6: knob table, ranges, enums, sanitize, metadata. */
#include <string.h>

#include "knobs.h"
#include "tf.h"
#include "tests.h"

void test_knobs_table(void)
{
    fw_knobs_t k;
    fw_knobs_defaults(&k);
    TF_CHECK_EQ(k.version, FW_KNOBS_VERSION);
    TF_CHECK_EQ(k.layout, FW_KNOBS_LAYOUT_HASH);
    TF_CHECK(FW_KNOB_COUNT >= 40);
    for (uint32_t i = 0; i < (uint32_t)FW_KNOB_COUNT; i++) {
        const fw_knob_meta_t *m = &fw_knob_meta[i];
        int32_t v = 0;
        TF_CHECK(m->name != NULL && m->name[0] != '\0');
        TF_CHECK(m->unit != NULL && m->unit[0] != '\0');
        TF_CHECK(m->src != NULL && strlen(m->src) > 5u);
        TF_CHECK(m->min <= m->def && m->def <= m->max);
        TF_CHECK_EQ(fw_knob_get(&k, i, &v), FW_KNOB_OK);
        TF_CHECK_EQ(v, m->def);
        /* min and max accepted (unless an enum excludes them), one past each rejected, k unchanged on reject */
        fw_knobs_t c = k;
        if (m->min > INT32_MIN)
            TF_CHECK_EQ(fw_knob_set(&c, i, m->min - 1), FW_KNOB_ERANGE);
        if (m->max < INT32_MAX)
            TF_CHECK_EQ(fw_knob_set(&c, i, m->max + 1), FW_KNOB_ERANGE);
        TF_CHECK(memcmp(&c, &k, sizeof c) == 0);
        TF_CHECK_EQ(fw_knob_set(&c, i, m->def), FW_KNOB_OK);
    }
    int32_t v;
    TF_CHECK_EQ(fw_knob_get(&k, FW_KNOB_COUNT, &v), FW_KNOB_EID);
    TF_CHECK_EQ(fw_knob_set(&k, 9999u, 0), FW_KNOB_EID);
    /* hard-clamped knobs are flagged */
    TF_CHECK_EQ(fw_knob_is_hard(FW_KNOB_ceiling_cdb), 1);
    TF_CHECK_EQ(fw_knob_is_hard(FW_KNOB_out_i_peak_ma), 1);
    TF_CHECK_EQ(fw_knob_is_hard(FW_KNOB_ichg_code_warm), 1);
    TF_CHECK_EQ(fw_knob_is_hard(FW_KNOB_vbatreg_code), 1);
    TF_CHECK_EQ(fw_knob_is_hard(FW_KNOB_ts_hot_code), 1);
    TF_CHECK_EQ(fw_knob_is_hard(FW_KNOB_dead_time_rise_ticks), 1);
    TF_CHECK_EQ(fw_knob_is_hard(FW_KNOB_docked_output), 1);
    TF_CHECK_EQ(fw_knob_is_hard(FW_KNOB_band_lo_hz), 0);
}

void test_knobs_enum_and_clamps(void)
{
    fw_knobs_t k;
    fw_knobs_defaults(&k);
    TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_pwm_khz, 300), FW_KNOB_EENUM);
    TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_pwm_khz, 400), FW_KNOB_OK);
    TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_dead_time_rise_ticks, 0), FW_KNOB_ERANGE);   /* >= 1 tick */
    TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_vbatreg_code, 0x47), FW_KNOB_ERANGE);        /* > 4.20 V */
    TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_ichg_code_warm, HC_ICHG_CODE_MAX + 1), FW_KNOB_ERANGE);
    TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_ts_hot_code, 4), FW_KNOB_ERANGE);
#if FW_SELFTEST_EXEMPTION == FW_EXEMPTION_b
    TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_docked_output, 1), FW_KNOB_ERANGE);          /* ECR-0009 variant b: never */
#else
    TF_CHECK_EQ(fw_knob_set(&k, FW_KNOB_docked_output, 1), FW_KNOB_OK);
#endif
    /* sanitize: a corrupted struct comes back inside every range */
    memset(&k, 0x7F, sizeof k);
    TF_CHECK(fw_knobs_sanitize(&k) > 0u);
    for (uint32_t i = 0; i < (uint32_t)FW_KNOB_COUNT; i++) {
        int32_t v;
        (void)fw_knob_get(&k, i, &v);
        TF_CHECK(v >= fw_knob_meta[i].min && v <= fw_knob_meta[i].max);
    }
    TF_CHECK(k.pwm_khz == 200 || k.pwm_khz == 400 || k.pwm_khz == 800);
    TF_CHECK(k.ceiling_cdb <= -1200);
    TF_CHECK(k.out_i_peak_ma <= FW_VAR_I_PEAK_MA_MAX);
    memset(&k, 0x80, sizeof k);
    (void)fw_knobs_sanitize(&k);
    TF_CHECK(k.dead_time_rise_ticks >= 1 && k.dead_time_fall_ticks >= 1);
    TF_CHECK(k.pwm_khz == 200 || k.pwm_khz == 400 || k.pwm_khz == 800);
    fw_knobs_t d;
    fw_knobs_defaults(&d);
    TF_CHECK_EQ(fw_knobs_sanitize(&d), 0);
}
