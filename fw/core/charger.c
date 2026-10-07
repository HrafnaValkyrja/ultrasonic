#include "charger.h"

#include <string.h>

#include "dsp_math.h"
#include "hal.h"
#include "variant_config.h"

/* register write order: safety limits first, charge current last */
static const uint8_t order[8] = {0x0Bu, 0x09u, 0x08u, 0x05u, 0x07u, 0x0Au, 0x03u, 0x04u};

int32_t fw_chg_ts_temp_c10(uint32_t ts_mv)
{
    if (ts_mv == 0u)
        return 2000;                                 /* shorted / pulled low */
    float r = (float)ts_mv * 1e-3f / 38e-6f;         /* ohm at the 38 uA bias (sub-power.md, SLUSE99C) */
    if (r > 1.0e6f)
        return -1000;                                /* open */
    float inv_t = 1.0f / 298.15f + fw_log2f(r / 10000.0f) * 0.69314718f / 3435.0f;
    return (int32_t)((1.0f / inv_t - 273.15f) * 10.0f + (inv_t > 0.0f ? 0.5f : -0.5f));
}

fw_chg_plan_t fw_chg_plan(const fw_knobs_t *k, uint32_t usb_enumerated, uint32_t usb_suspended, uint32_t temp_valid, int32_t temp_c10)
{
    fw_chg_plan_t p;
    memset(&p, 0, sizeof p);
    int32_t vbat = k->vbatreg_code > HC_VBATREG_CODE_MAX ? HC_VBATREG_CODE_MAX : k->vbatreg_code;
    int32_t warm = k->ichg_code_warm > HC_ICHG_CODE_MAX ? HC_ICHG_CODE_MAX : k->ichg_code_warm;
    int32_t cool = k->ichg_code_cool > HC_ICHG_CODE_MAX ? HC_ICHG_CODE_MAX : k->ichg_code_cool;
    int32_t ichg = (temp_valid && temp_c10 >= 200) ? warm : cool;       /* 20 C rule (gen.py U3 comment, sub-power.md) */
    int32_t ts_hot = k->ts_hot_code > HC_TS_HOT_CODE_MAX ? HC_TS_HOT_CODE_MAX : k->ts_hot_code;
    /* index = register */
    p.want[0x03] = (uint8_t)(vbat & 0x7F);                  p.mask[0x03] = 0x7Fu;   /* VBATREG */
    p.want[0x04] = (uint8_t)(ichg & 0x7F);                  p.mask[0x04] = 0xFFu;   /* CHG_DIS = 0, ICHG */
    p.want[0x05] = 0x00u;                                   p.mask[0x05] = 0x0Cu;   /* VINDPM 00 = 4.2 V */
    p.want[0x07] = 0x10u | 0x01u;                           p.mask[0x07] = 0x13u;   /* 2XTMR_EN = 1, WATCHDOG_SEL 01 (HW reset, 160 s) */
    p.want[0x08] = usb_enumerated ? 0x05u : 0x01u;          p.mask[0x08] = 0x07u;   /* ILIM 100 mA until enumeration, then 500 */
    p.want[0x09] = 0x00u;                                   p.mask[0x09] = 0x99u;   /* REG_RST 0, PB_LPRESS_ACTION 00, EN_PUSH 0 */
    p.want[0x0A] = usb_suspended ? 0x04u : 0x00u;          p.mask[0x0A] = 0x0Cu;   /* SYS_MODE 01 on USB suspend, else 00 */
    p.want[0x0B] = (uint8_t)((ts_hot & 3) << 6);            p.mask[0x0B] = 0xC0u;   /* TS_HOT 11 = 45 C */
    return p;
}

/* SYS_MODE 01 is ignored by the charger while VBAT < VBUVLO (SLUSE99C 8.3.4: it falls back to 00 so a flat cell is never cut off). A
 * read-back of 00 when 01 was asked is therefore accepted (counted), never a plan failure: CHG_DIS on a flat cell would be worse. */
static uint32_t matches(const uint8_t *r, const fw_chg_plan_t *p, uint32_t *sys_refused)
{
    *sys_refused = 0u;
    for (uint32_t i = 0; i < FW_CHG_NREG; i++)
        if ((r[i] & p->mask[i]) != (p->want[i] & p->mask[i])) {
            if (i == 0x0Au && (p->want[i] & 0x0Cu) == 0x04u && (r[i] & 0x0Cu) == 0x00u) {
                *sys_refused = 1u;
                continue;
            }
            return 0u;
        }
    return 1u;
}

uint32_t fw_chg_service(fw_chg_t *c, const fw_knobs_t *k, const fw_chg_plan_t *p, uint64_t now_us, uint32_t force)
{
    if (!force && now_us - c->last_us < (uint64_t)k->chg_keepalive_s * 1000000u)
        return c->fault ? 0u : 1u;
    c->last_us = now_us;                             /* also throttles retries after an error */
    c->services++;
    uint8_t r[FW_CHG_NREG];
    if (hal_i2c_read(FW_CHG_ADDR, FW_CHG_REG0, r, FW_CHG_NREG) != HAL_OK) {
        c->i2c_errors++;
        c->fault = 1u;
        (void)hal_i2c_recover();                     /* fail safe: nothing written; the charger keeps its (10 mA) defaults */
        return 0u;
    }
    memcpy(c->seen, r, sizeof r);
    c->pgood = r[0] & 1u;
    uint32_t refused = 0u;
    if (matches(r, p, &refused) && !refused) {
        c->verified++;
        c->fault = 0u;
        return 1u;
    }
    c->reasserts++;
    for (uint32_t i = 0; i < sizeof order; i++) {
        uint32_t idx = order[i];
        uint8_t v = (uint8_t)((r[idx] & (uint8_t)~p->mask[idx]) | (p->want[idx] & p->mask[idx]));
        if (hal_i2c_write(FW_CHG_ADDR, order[i], &v, 1u) != HAL_OK) {
            c->i2c_errors++;
            break;
        }
    }
    if (hal_i2c_read(FW_CHG_ADDR, FW_CHG_REG0, r, FW_CHG_NREG) == HAL_OK && matches(r, p, &refused)) {
        c->sys_mode_refused += refused;
        c->verified++;
        c->fault = 0u;
        c->last_ichg_code = p->want[0x04];
        c->last_ilim_code = p->want[0x08];
        return 1u;
    }
    /* the plan could not be verified: stop charging (CHG_DIS = 1) and say so */
    c->verify_fail++;
    c->fault = 1u;
    uint8_t dis = (uint8_t)(0x80u | (p->want[0x04] & 0x7Fu));
    if (hal_i2c_write(FW_CHG_ADDR, 0x04u, &dis, 1u) == HAL_OK)
        c->chg_dis_set++;
    return 0u;
}
