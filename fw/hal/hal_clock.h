/* fw/hal/hal_clock.h: clock plans (A3-u575-plan.md s2; FWSIM-R25). Change only with ADF1 and TIM1 stopped. */
#ifndef FW_HAL_CLOCK_H
#define FW_HAL_CLOCK_H
#include "hal_types.h"

/* A3-u575-plan.md s2 plans (MSIS 48.005 MHz LSE-locked, /3 -> 16.0017 MHz PLL1 input) + the per-variant plans from the runtime model
 * (sim/checks/runtime_fw.py; FWSIM-R47): P112 spec B (Range 1), P104 spec B in Range 2 (load 81 %: marginal), P72 slim B, P52 algorithm A
 * (Range 3). Every plan keeps HCLK = 400 kHz x integer (PCM and PWM rate) and the mic clock 4.0004 MHz; TIM1 ARR = HCLK / 400 kHz. */
typedef enum { HAL_CLK_P80 = 0, HAL_CLK_P160 = 1, HAL_CLK_P64 = 2, HAL_CLK_P48 = 3, HAL_CLK_P112 = 4, HAL_CLK_P104 = 5, HAL_CLK_P72 = 6,
               HAL_CLK_P52 = 7, HAL_CLK_PLAN_COUNT } hal_clock_plan_t;

hal_status_t hal_clock_set_plan(hal_clock_plan_t plan);   /* PLL lock, flash wait states, ICACHE; timeout -> HAL_TIMEOUT */
uint32_t hal_clock_hclk_hz(void);
hal_status_t hal_clock_stop_prep(void);   /* FWSIM-R23: PLL2/PLL3/HSI48/SHSI off, waiting for their RDY flags to clear; exit = hal_clock_set_plan */                          /* current HCLK */
#endif
