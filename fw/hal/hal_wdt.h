/* fw/hal/hal_wdt.h: IWDG (FWSIM-R55). Once started only a reset stops it. */
#ifndef FW_HAL_WDT_H
#define FW_HAL_WDT_H
#include "hal_types.h"

hal_status_t hal_wdt_start(uint32_t timeout_ms);
void hal_wdt_kick(void);
#endif
