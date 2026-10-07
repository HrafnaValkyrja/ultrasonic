/* fw/hal/hal_brk.h: always-on bridge fault break (FWSIM-R65, OUT-6 decided 2026-10-07): ADC1 converts PA6 I_SENSE continuously into MDF1
 * (DATSRC = ADC1, RM0456 Rev 7 s16.3.18); the MDF1 out-of-limit detector window (both signs) asserts mdf_break0 -> TIM1 BKCMP7: MOE cleared,
 * outputs to the safe idle state, latched (BIF) until cleared. Armed before the first PWM edge of any output, disarmed only after MOE = 0. */
#ifndef FW_HAL_BRK_H
#define FW_HAL_BRK_H
#include "hal_types.h"

hal_status_t hal_brk_arm(uint32_t threshold_ma);   /* window +-threshold on the filtered supply current */
void hal_brk_disarm(void);
bool hal_brk_latched(void);                        /* TIM1 BIF */
void hal_brk_clear(void);                          /* clear BIF (only after the cool-down; never ocref_clr, ES0499 2.16.2) */
#endif
