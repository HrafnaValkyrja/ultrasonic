/* fw/hal/hal_power.h: low-power modes, reset cause, dead-battery release (FWSIM-R22, R23; ECR-0013). */
#ifndef FW_HAL_POWER_H
#define FW_HAL_POWER_H
#include "hal_types.h"

typedef enum { HAL_RESET_POWER_LOSS = 0, HAL_RESET_SOFT, HAL_RESET_PIN, HAL_RESET_IWDG, HAL_RESET_BOR, HAL_RESET_OTHER } hal_reset_cause_t;
typedef enum { HAL_WAKE_NONE = 0, HAL_WAKE_BUTTON, HAL_WAKE_CHG_INT, HAL_WAKE_VBUS, HAL_WAKE_OTHER } hal_wake_t;

hal_wake_t hal_power_stop2(void);                   /* caller has done the FWSIM-R23 sequence; returns the wake source */
hal_reset_cause_t hal_power_reset_cause(void);      /* RCC_CSR, read once at boot then cleared */
void hal_power_system_reset(void);                  /* never returns on target; the fake records it and returns */
void hal_power_ucpd_dbdis(void);                    /* PWR_UCPDR.UCPD_DBDIS: release the dead-battery pull-downs (PA15, PB15) */
#endif
