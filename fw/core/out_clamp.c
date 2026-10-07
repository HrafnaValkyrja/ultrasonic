#include "out_clamp.h"

#include "tables.h"
#include "variant_config.h"

_Static_assert(FW_VAR_AMP_MAX_PPM <= 1000000u, "current clamp amplitude above full scale");
_Static_assert(HC_CEILING_PEAK_PPM + FW_SHAPER_EXCURSION_PPM < FW_VAR_AMP_MAX_PPM,
               "listening ceiling + shaper excursion must sit below the FWSIM-R64 current clamp (else the clamp clips music)");
_Static_assert(FW_VAR_I_PEAK_MA_MAX <= 270, "i_peak_max <= 0.9 x U4 300 mA (FWSIM-R64)");

static const float db_table[FW_DB_TABLE_N] = FW_DB_TABLE_INIT;

uint32_t fw_amp_ppm_for_ma(int32_t i_ma)
{
    if (i_ma <= 0)
        return 0u;
    /* i[mA] * R[mohm] / Vdd[mV] = (V/V) * 1e3; x 1e3 more for ppm. 64-bit: no overflow for any int32 input. */
    uint64_t ppm = ((uint64_t)(uint32_t)i_ma * (uint64_t)FW_VAR_R_LOAD_MOHM * 1000u) / (uint64_t)FW_VAR_VDD_MV;
    return ppm > 1000000u ? 1000000u : (uint32_t)ppm;
}

uint32_t fw_out_amp_max_ppm(const fw_knobs_t *k)
{
    int32_t i_ma = k->out_i_peak_ma;
    if (i_ma > FW_VAR_I_PEAK_MA_MAX)
        i_ma = FW_VAR_I_PEAK_MA_MAX;   /* a corrupted struct cannot lift the hard clamp */
    uint32_t a = fw_amp_ppm_for_ma(i_ma);
    return a < FW_VAR_AMP_MAX_PPM ? a : FW_VAR_AMP_MAX_PPM;
}

fw_ccr_bounds_t fw_ccr_bounds(uint16_t arr, uint32_t amp_ppm)
{
    fw_ccr_bounds_t b;
    if (arr < HC_ARR_MIN)
        arr = HC_ARR_MIN;
    if (amp_ppm > FW_VAR_AMP_MAX_PPM)
        amp_ppm = FW_VAR_AMP_MAX_PPM;
    /* |2c/arr - 1| <= p/1e6  <=>  arr(1e6 - p) <= 2e6 c <= arr(1e6 + p) */
    uint64_t lo_num = (uint64_t)arr * (1000000u - amp_ppm), hi_num = (uint64_t)arr * (1000000u + amp_ppm);
    b.arr = arr;
    b.lo = (uint16_t)((lo_num + 1999999u) / 2000000u);
    b.hi = (uint16_t)(hi_num / 2000000u);
    b.amp_ppm = amp_ppm;
    return b;
}

float fw_db_to_amp(int32_t cdb)
{
    if (cdb >= 0)
        return 1.0f;
    if (cdb <= FW_DB_TABLE_MIN_CDB)
        return db_table[0];
    int32_t i = (cdb - FW_DB_TABLE_MIN_CDB + FW_DB_TABLE_STEP_CDB / 2) / FW_DB_TABLE_STEP_CDB;
    return db_table[i];
}

static const uint32_t plan_hz[8] = {80009000u, 160018000u, 64007000u, 48005000u, 112012000u, 104011000u, 72008000u, 52006000u};
static const uint16_t plan_b[8] = {200u, 400u, 160u, 120u, 280u, 260u, 180u, 130u};   /* HCLK / 400 kHz (MSIS 48.005 / 3 x N / R) */

uint32_t fw_plan_hclk_hz(uint32_t plan) { return plan_hz[plan < 8u ? plan : 0u]; }

uint16_t fw_arr_for_khz(int32_t pwm_khz, uint32_t plan, int32_t *eff_khz)
{
    uint32_t b = plan_b[plan < 8u ? plan : 0u];
    uint32_t r = pwm_khz == 800 ? 4u : (pwm_khz == 400 ? 2u : 1u);
    while (r > 1u && (b % r != 0u || b / r < HC_ARR_MIN))
        r /= 2u;
    if (eff_khz)
        *eff_khz = (int32_t)(200u * r);
    return (uint16_t)(b / r);
}

uint32_t fw_dead_ticks(uint32_t ticks_p80, uint32_t plan)
{
    uint64_t t = ((uint64_t)ticks_p80 * fw_plan_hclk_hz(plan) + plan_hz[0] - 1u) / plan_hz[0];   /* ceil */
    return (uint32_t)t;
}
