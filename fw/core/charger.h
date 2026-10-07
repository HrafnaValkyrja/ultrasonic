/* fw/core/charger.h: BQ25180 supervision (FWSIM-R20). fw_chg_plan() is pure (knobs + inputs -> wanted bits); fw_chg_service() is app-level
 * (like app.c it owns HAL calls): read-back of the plan registers at least every chg_keepalive_s (that read is also the watchdog keep-alive,
 * <= half the 160 s WATCHDOG_SEL 01 period), re-assert on any difference (watchdog revert, HW reset, power-good), verify, and fall back to
 * CHG_DIS when the plan cannot be verified. Bitfields: TI SLUSE99C Rev C Tables 8-12..8-20 (fetched 2026-10-07, SHA-256 prefix c2008f613723fec3). */
#ifndef FW_CORE_CHARGER_H
#define FW_CORE_CHARGER_H
#include <stdint.h>

#include "knobs.h"

#define FW_CHG_ADDR 0x6Au
#define FW_CHG_REG0 0x00u              /* STAT0 .. TS_CONTROL = 0x00 .. 0x0B (index = register) */
#define FW_CHG_NREG 12u

typedef struct {
    uint64_t last_us;
    uint32_t services, verified, reasserts, verify_fail, i2c_errors, chg_dis_set, fault, pgood;   /* pgood: STAT0 VIN_PGOOD at the last read */
    uint32_t last_ichg_code, last_ilim_code, sys_mode_refused;
    uint8_t seen[FW_CHG_NREG];
} fw_chg_t;

typedef struct {
    uint8_t want[FW_CHG_NREG], mask[FW_CHG_NREG];
} fw_chg_plan_t;

/* temp_valid only while docked (TS on PA2 is meaningful only with VIN, SLUSE99C Table 8-6); unknown temperature -> the cool (50 mA) code */
/* usb_suspended: a connected host suspended the bus (USB 2.0 s7.2.3: <= 2.5 mA); the 50 mA ILIM floor cannot meet that, so SYS_MODE = 01
 * (SYS from BAT, IN disconnected; SLUSE99C 8.3.4) until resume; VIN toggling resets SYS_MODE to 00 by itself, VBAT < VBUVLO ignores it */
fw_chg_plan_t fw_chg_plan(const fw_knobs_t *k, uint32_t usb_enumerated, uint32_t usb_suspended, uint32_t temp_valid, int32_t temp_c10);
int32_t fw_chg_ts_temp_c10(uint32_t ts_mv);   /* 10 k B3435 NTC at the 38 uA docked bias -> 0.1 C (pure; < -400 = open, > 1000 = short) */
/* returns 1 if the plan is verified in the charger now */
uint32_t fw_chg_service(fw_chg_t *c, const fw_knobs_t *k, const fw_chg_plan_t *p, uint64_t now_us, uint32_t force);
#endif
