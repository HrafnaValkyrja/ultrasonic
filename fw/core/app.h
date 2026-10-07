/* fw/core/app.h: the portable main loop (glue between HAL and the pure entry points). Runs unchanged on the host fakes
 * (tests) and on the target. Owns all HAL calls in core; entry points stay pure (FWSIM-R3). */
#ifndef FW_CORE_APP_H
#define FW_CORE_APP_H
#include "cdc_frame.h"
#include "charger.h"
#include "fw.h"
#include "knob_store.h"

typedef struct {
    fw_state_t st;
    fw_taps_t taps;
    fw_store_info_t store;
    uint16_t ccr[FW_CCR_MAX_PER_HOP];
    uint32_t hops;
    uint32_t submit_errors;
    uint32_t vbus_seen;
    uint32_t bridge_on, brk_reported, start_errors;
    uint32_t chg_ok, chg_temp_class, chg_int_seen, pa1_seen;
    uint32_t mic_on, led_duty_ppm, stops, last_wake;
    fw_chg_t chg;
    uint32_t usb_on, cdc_replies;          /* OTG_FS powered (FWSIM-R28: only while PA1 shows VBUS) */
    uint32_t usb_cfg;                      /* hal_usb_bus_t last seen: charger ILIM / input-off follow it (FWSIM-R20) */
    uint32_t dfu_prep, dfu_refusals, dfu_handoffs;   /* FWSIM-R21 handoff: charger watchdog off while the ROM loader runs */
    uint64_t dfu_since_us;
    fw_cdc_frame_t cdc;
} fw_app_t;

void fw_app_boot(fw_app_t *app);   /* knobs from flash (defaults + event if bad), fw_init, UCPD release, TIM1 config */
void fw_app_step(fw_app_t *app);   /* one main-loop pass: hops -> fw_hop -> submit; VBUS edges -> events; poll; bridge + break (FWSIM-R65);
                                    * charger supervision (FWSIM-R20); wdt */
uint32_t fw_app_brk_threshold_ma(const fw_app_t *app);
#endif
