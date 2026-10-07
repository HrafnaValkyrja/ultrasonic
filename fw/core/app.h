/* fw/core/app.h: the portable main loop (glue between HAL and the pure entry points). Runs unchanged on the host fakes
 * (tests) and on the target. Owns all HAL calls in core; entry points stay pure (FWSIM-R3). */
#ifndef FW_CORE_APP_H
#define FW_CORE_APP_H
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
} fw_app_t;

void fw_app_boot(fw_app_t *app);   /* knobs from flash (defaults + event if bad), fw_init, UCPD release, TIM1 config */
void fw_app_step(fw_app_t *app);   /* one main-loop pass: hops -> fw_hop -> submit; VBUS edges -> events; poll; wdt */
#endif
