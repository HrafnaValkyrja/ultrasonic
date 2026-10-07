/* fw/hal/hal_irq.h: interrupt masking around the few shared flags (PRIMASK on target). */
#ifndef FW_HAL_IRQ_H
#define FW_HAL_IRQ_H
#include "hal_types.h"

uint32_t hal_irq_save(void);          /* disable, return the previous state */
void hal_irq_restore(uint32_t state);
#endif
