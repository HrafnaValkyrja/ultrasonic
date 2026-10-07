/* fw/port_u575/hal_u575_periph.c: register layer, safest-first peripherals (GPIO, TIM1 PWM + break). RM0456 Rev 7 values (reg.h).
 * Host-tested by fw/test/port/test_regs.c against a recorded-register fake (FW_REG_RECORD); never executed by QEMU (no STM32 peripherals). */
#include "board_config.h"
#include "hal.h"
#include "reg.h"

static const board_pin_info_t pins[BOARD_PIN_COUNT] = BOARD_PIN_TABLE_INIT;

static int32_t port_index(char p)
{
    return (p >= 'A' && p <= 'J') ? (int32_t)(p - 'A') : -1;
}

/* ---------------------------------------------------------------------------------------------- GPIO */
hal_status_t hal_gpio_mode(board_pin_t pin, hal_gpio_mode_t mode)
{
    if ((uint32_t)pin >= (uint32_t)BOARD_PIN_COUNT || (uint32_t)mode >= (uint32_t)HAL_GPIO_MODE_COUNT)
        return HAL_EINVAL;
    const board_pin_info_t *p = &pins[pin];
    int32_t pi = port_index(p->port);
    if (pi < 0)
        return HAL_EINVAL;                                       /* NRST has no GPIO */
    if (mode == HAL_GPIO_AF && p->af == BOARD_AF_NONE)
        return HAL_EINVAL;
    uint32_t base = GPIO_BASE(pi), n = p->num, sh = 2u * n;
    REG_SET(RCC_AHB2ENR1, 1u << (uint32_t)pi);
    uint32_t moder = 3u, pupd = 0u, od = 0u;
    switch (mode) {
    case HAL_GPIO_ANALOG: moder = 3u; break;
    case HAL_GPIO_INPUT: moder = 0u; break;
    case HAL_GPIO_INPUT_PU: moder = 0u; pupd = 1u; break;
    case HAL_GPIO_INPUT_PD: moder = 0u; pupd = 2u; break;
    case HAL_GPIO_OUTPUT_PP: moder = 1u; break;
    case HAL_GPIO_OUTPUT_OD: moder = 1u; od = 1u; break;
    case HAL_GPIO_AF: moder = 2u; break;
    default: break;
    }
    if (mode == HAL_GPIO_AF) {                                   /* AF number before the mode switch: no glitch on another function */
        uint32_t afr = n < 8u ? GPIO_AFRL : GPIO_AFRH, ash = 4u * (n & 7u);
        REG_MOD(base + afr, 0xFu << ash, (uint32_t)p->af << ash);
    }
    REG_MOD(base + GPIO_OTYPER, 1u << n, od << n);
    REG_MOD(base + GPIO_PUPDR, 3u << sh, pupd << sh);
    REG_MOD(base + GPIO_MODER, 3u << sh, moder << sh);
    return HAL_OK;
}

void hal_gpio_write(board_pin_t pin, bool high)
{
    if ((uint32_t)pin >= (uint32_t)BOARD_PIN_COUNT || port_index(pins[pin].port) < 0)
        return;
    REG_W(GPIO_BASE(port_index(pins[pin].port)) + GPIO_BSRR, high ? (1u << pins[pin].num) : (1u << (pins[pin].num + 16u)));
}

bool hal_gpio_read(board_pin_t pin)
{
    if ((uint32_t)pin >= (uint32_t)BOARD_PIN_COUNT || port_index(pins[pin].port) < 0)
        return false;
    return ((REG_R(GPIO_BASE(port_index(pins[pin].port)) + GPIO_IDR) >> pins[pin].num) & 1u) != 0u;
}

/* ---------------------------------------------------------------------------------------------- TIM1 PWM (FWSIM-R16) */
#define T(off) (TIM1_BASE + (off))
static uint16_t pwm_arr;

hal_status_t hal_pwm_config(const hal_pwm_cfg_t *cfg)
{
    if (cfg == NULL || cfg->arr < 50u || cfg->dtg_rise < 1u || cfg->dtg_fall < 1u || cfg->rcr < 1u)
        return HAL_EINVAL;                                       /* hard clamps: ARR >= 50, dead time >= 1 tick */
    REG_SET(RCC_APB2ENR, 1u << 11);                              /* TIM1EN */
    REG_W(T(TIM_BDTR), 0u);                                      /* MOE = 0 while configuring */
    REG_W(T(TIM_CR1), (1u << 7) | (1u << 5));                    /* ARPE, CMS = 01 centre-aligned mode 1, CEN = 0 */
    REG_W(T(TIM_CR2), 0u);                                       /* OIS1/1N/3/3N = 0: idle level low = FET off [A: gate polarity per bridge, sub-output.md] */
    REG_W(T(TIM_PSC), 0u);
    REG_W(T(TIM_ARR), cfg->arr);
    REG_W(T(TIM_RCR), cfg->rcr);
    REG_W(T(TIM_CCMR1), (6u << 4) | (1u << 3));                  /* OC1M 0110 PWM mode 1, OC1PE */
    REG_W(T(TIM_CCMR2), (6u << 4) | (1u << 3));                  /* OC3M 0110, OC3PE (leg B on CH3/CH3N since Rev F) */
    REG_W(T(TIM_CCER), 0u);                                      /* outputs disabled until start */
    REG_W(T(TIM_DTR2), (uint32_t)cfg->dtg_fall | (cfg->dtg_fall != cfg->dtg_rise ? (1u << 16) : 0u));   /* DTGF, DTAE before BDTR (RM) */
    REG_W(T(TIM_BDTR), (uint32_t)cfg->dtg_rise | (1u << 10) | (1u << 11));                               /* DTG, OSSI, OSSR; MOE = 0 */
    pwm_arr = cfg->arr;
    return HAL_OK;
}

hal_status_t hal_pwm_start(void)
{
    if (pwm_arr == 0u)
        return HAL_EINVAL;
    if (REG_R(T(TIM_SR)) & (1u << 7))
        return HAL_BUSY;                                         /* break latched (BIF): MOE would be refused */
    REG_W(T(TIM_CCR1), pwm_arr / 2u);                            /* centre (zero differential) preloaded on both legs */
    REG_W(T(TIM_CCR3), pwm_arr / 2u);
    REG_W(T(TIM_EGR), 1u);                                       /* UG: load ARR/CCR preloads */
    REG_SET(T(TIM_CR1), 1u);                                     /* CEN */
    REG_W(T(TIM_CCER), (1u << 0) | (1u << 2) | (1u << 8) | (1u << 10));   /* CC1E CC1NE CC3E CC3NE */
    REG_SET(T(TIM_BDTR), 1u << 15);                              /* MOE last */
    return HAL_OK;
}

void hal_pwm_stop(void)
{
    REG_CLR(T(TIM_BDTR), 1u << 15);                              /* MOE = 0: outputs to the OSSI idle levels at once */
    REG_W(T(TIM_CCER), 0u);
    REG_CLR(T(TIM_CR1), 1u);
    (void)hal_gpio_mode(BOARD_PIN_GA_P, HAL_GPIO_ANALOG);        /* then the bridge pins analog (FWSIM-R16 stop) */
    (void)hal_gpio_mode(BOARD_PIN_GA_N, HAL_GPIO_ANALOG);
    (void)hal_gpio_mode(BOARD_PIN_GB_P, HAL_GPIO_ANALOG);
    (void)hal_gpio_mode(BOARD_PIN_GB_N, HAL_GPIO_ANALOG);
}


/* the TIM1 side of the break, used by hal_brk_* in hal_u575_io.c */
void u575_tim1_brk_enable(uint32_t on)
{
    if (on) {
        REG_SET(RCC_APB2ENR, 1u << 11);
        REG_MOD(T(TIM_BDTR), (1u << 13), (1u << 12));            /* BKE; BKP = 0 [T: confirm against the mdf1_break0 output polarity at bring-up] */
        REG_SET(T(TIM_AF1), 1u << 7);                            /* BKCMP7E: tim_brk_cmp7 = mdf1_break0 */
    } else {
        REG_CLR(T(TIM_AF1), 1u << 7);
        REG_CLR(T(TIM_BDTR), 1u << 12);
    }
}

bool hal_brk_latched(void)
{
    return (REG_R(T(TIM_SR)) & (1u << 7)) != 0u;
}

void hal_brk_clear(void)
{
    REG_W(T(TIM_SR), ~(1u << 7));                                /* rc_w0: write 0 to BIF only */
}

uint16_t u575_pwm_arr(void) { return pwm_arr; }
