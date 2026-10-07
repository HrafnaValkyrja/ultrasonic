/* fw/hal/hal_clock.h: clock plans (A3-u575-plan.md s2; FWSIM-R25). Change only with ADF1 and TIM1 stopped. */
#ifndef FW_HAL_CLOCK_H
#define FW_HAL_CLOCK_H
#include "hal_types.h"

typedef enum { HAL_CLK_P80 = 0, HAL_CLK_P160 = 1, HAL_CLK_P64 = 2, HAL_CLK_P48 = 3, HAL_CLK_PLAN_COUNT } hal_clock_plan_t;

hal_status_t hal_clock_set_plan(hal_clock_plan_t plan);   /* PLL lock, flash wait states, ICACHE; timeout -> HAL_TIMEOUT */
uint32_t hal_clock_hclk_hz(void);
hal_status_t hal_clock_stop_prep(void);   /* FWSIM-R23: PLL2/PLL3/HSI48/SHSI off, waiting for their RDY flags to clear; exit = hal_clock_set_plan */                          /* current HCLK */
#endif
