/* fw/hal/hal_led.h: status LED on PB7 (LED_K, TIM4_CH2, cathode side: sink PWM). sub-ui.md issues 6/7: duty from VSYS toward a target current;
 * PB7 must be released (analog) before Stop 2 because pins hold their state there (RM0456 s10.7.8). */
#ifndef FW_HAL_LED_H
#define FW_HAL_LED_H
#include "hal_types.h"

hal_status_t hal_led_set(uint32_t duty_ppm);   /* 0 = off (pin may then be parked); >= 1 kHz PWM so it looks solid */
#endif
