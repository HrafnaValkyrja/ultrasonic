/* fw/hal/hal_time.h: time base. hal_time_us is monotonic wall time (LPTIM/SysTick on target, simulated on host);
 * hal_time_cycles is DWT CYCCNT (core clock, stops when the core clock is gated; FWSIM-R49). Core entry points never call
 * these: the caller injects time (FWSIM-R3). */
#ifndef FW_HAL_TIME_H
#define FW_HAL_TIME_H
#include "hal_types.h"

uint64_t hal_time_us(void);
uint32_t hal_time_cycles(void);
#endif
