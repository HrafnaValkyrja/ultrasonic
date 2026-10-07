/* fw/hal/hal_pwm.h: TIM1 bridge sink + safe-state sequencer (spec D6; FWSIM-R16, R17, R43). Leg A CH1/CH1N, leg B CH3/CH3N
 * (Rev F, ECR-0003); the port writes CCR1 and CCR3 = ARR - CCR1 per period from the one CCR stream (IF-FW-DSP). */
#ifndef FW_HAL_PWM_H
#define FW_HAL_PWM_H
#include "hal_types.h"

typedef struct {
    uint16_t arr;          /* 200 / 100 / 50 (>= HC_ARR_MIN) */
    uint8_t rcr;           /* 1: one update per centre-aligned period (FWSIM design_binding.tim1_update_cadence) */
    uint8_t dtg_rise;      /* dead-time ticks (>= HC_DEADTIME_TICKS_MIN) */
    uint8_t dtg_fall;      /* asymmetric dead time TIM1_DTR2 */
} hal_pwm_cfg_t;

hal_status_t hal_pwm_config(const hal_pwm_cfg_t *cfg);    /* outputs stay idle (MOE = 0) */
hal_status_t hal_pwm_start(void);                         /* CCR = ARR/2 preloaded -> UEV -> CCxE/CCxNE -> MOE = 1 */
void hal_pwm_stop(void);                                  /* MOE = 0 -> pins analog */
hal_status_t hal_pwm_submit(const uint16_t *ccr, size_t n); /* next hop's CCR stream (n = 128 * 200 / ARR) */
uint32_t hal_pwm_underruns(void);                         /* hops where the centre CCR was repeated (FWSIM-R46) */
#endif
