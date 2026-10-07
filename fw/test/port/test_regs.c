/* fw/test/port/test_regs.c: U575 register layer (fw/port_u575/hal_u575_periph.c) against RM0456 Rev 7 values, recorded-register fake.
 * Prints one JSON line; exit 1 on any failure. Run by fwsim (row port_u575.regs). */
#include <stdio.h>

#include "hal.h"
#include "reg.h"
#include "regfake.h"

static uint32_t checks, fails;
#define CHECK(c) do { checks++; if (!(c)) { fails++; fprintf(stderr, "FAIL %s:%d %s\n", __FILE__, __LINE__, #c); } } while (0)
#define GA 0x42020000u
#define GB 0x42020400u
#define T(o) (TIM1_BASE + (o))

int main(void)
{
    /* GPIO: GA_P = PA8 AF1 (TIM1_CH1): AF written before MODER; MODER bits 17:16 = 10 from the 0xABFFFFFF reset */
    rf_reset();
    CHECK(hal_gpio_mode(BOARD_PIN_GA_P, HAL_GPIO_AF) == HAL_OK);
    CHECK(reg_read(RCC_AHB2ENR1) & 1u);
    CHECK((reg_read(GA + GPIO_AFRH) & 0xFu) == 1u);
    CHECK(reg_read(GA + GPIO_MODER) == 0xABFEFFFFu);
    CHECK(rf_find(GA + GPIO_AFRH, 0u) >= 0 && rf_find(GA + GPIO_AFRH, 0u) < rf_find(GA + GPIO_MODER, 0u));
    /* LED_K = PB7 analog (reset 0xFFFFFEBF already analog at 15:14); BTN = PA0 input pull-up; MIC_DATA PB4 AF3 (ADF1_SDI0) */
    CHECK(hal_gpio_mode(BOARD_PIN_LED_K, HAL_GPIO_ANALOG) == HAL_OK);
    CHECK(((reg_read(GB + GPIO_MODER) >> 14) & 3u) == 3u);
    CHECK(reg_read(RCC_AHB2ENR1) & 2u);
    CHECK(hal_gpio_mode(BOARD_PIN_BTN, HAL_GPIO_INPUT_PU) == HAL_OK);
    CHECK((reg_read(GA + GPIO_MODER) & 3u) == 0u && (reg_read(GA + GPIO_PUPDR) & 3u) == 1u);
    CHECK(hal_gpio_mode(BOARD_PIN_MIC_DATA, HAL_GPIO_AF) == HAL_OK);
    CHECK(((reg_read(GB + GPIO_AFRL) >> 16) & 0xFu) == 3u && ((reg_read(GB + GPIO_MODER) >> 8) & 3u) == 2u);
    CHECK(hal_gpio_mode(BOARD_PIN_MIC_VDD, HAL_GPIO_AF) == HAL_EINVAL);   /* PA5 has no AF in the pin contract */
    CHECK(hal_gpio_mode(BOARD_PIN_NRST, HAL_GPIO_OUTPUT_PP) == HAL_EINVAL);
    hal_gpio_write(BOARD_PIN_MIC_VDD, true);
    CHECK(reg_read(GA + GPIO_BSRR) == (1u << 5));
    hal_gpio_write(BOARD_PIN_MIC_VDD, false);
    CHECK(reg_read(GA + GPIO_BSRR) == (1u << 21));
    rf_poke(GA + GPIO_IDR, 1u);
    CHECK(hal_gpio_read(BOARD_PIN_BTN));

    /* TIM1 config (FWSIM-R16): MOE 0 first, centre-aligned 1 + ARPE, PWM mode 1 + preload on CH1/CH3, dead time rise 1 / fall 2 asymmetric,
     * OSSI/OSSR, outputs disabled; DTR2 before the final BDTR write */
    rf_reset();
    hal_pwm_cfg_t cfg = {200u, 1u, 1u, 2u};
    CHECK(hal_pwm_config(&cfg) == HAL_OK);
    CHECK(reg_read(RCC_APB2ENR) & (1u << 11));
    CHECK(rf_log(0)->addr == RCC_APB2ENR || rf_find(T(TIM_BDTR), 0u) < rf_find(T(TIM_CR1), 0u));
    CHECK(reg_read(T(TIM_CR1)) == 0xA0u);
    CHECK(reg_read(T(TIM_ARR)) == 200u && reg_read(T(TIM_RCR)) == 1u && reg_read(T(TIM_PSC)) == 0u);
    CHECK(reg_read(T(TIM_CCMR1)) == 0x68u && reg_read(T(TIM_CCMR2)) == 0x68u);
    CHECK(reg_read(T(TIM_CCER)) == 0u);
    CHECK(reg_read(T(TIM_DTR2)) == (2u | (1u << 16)));
    CHECK(reg_read(T(TIM_BDTR)) == (1u | (1u << 10) | (1u << 11)));
    {
        int32_t i_dtr2 = rf_find(T(TIM_DTR2), 0u), i_bdtr = -1;
        for (int32_t j = rf_find(T(TIM_BDTR), 0u); j >= 0; j = rf_find(T(TIM_BDTR), (uint32_t)j + 1u))
            i_bdtr = j;
        CHECK(i_dtr2 >= 0 && i_bdtr > i_dtr2);
    }
    hal_pwm_cfg_t bad = {40u, 1u, 1u, 1u};
    CHECK(hal_pwm_config(&bad) == HAL_EINVAL);
    hal_pwm_cfg_t bad2 = {200u, 1u, 0u, 1u};
    CHECK(hal_pwm_config(&bad2) == HAL_EINVAL);
    /* start: CCR1 = CCR3 = ARR/2 -> UG -> CEN -> CCxE/CCxNE -> MOE last */
    uint32_t m = rf_nlog();
    CHECK(hal_pwm_start() == HAL_OK);
    int32_t i1 = rf_find(T(TIM_CCR1), m), i3 = rf_find(T(TIM_CCR3), m), iu = rf_find(T(TIM_EGR), m), ic = rf_find(T(TIM_CCER), m);
    int32_t imoe = rf_find(T(TIM_BDTR), m);
    CHECK(reg_read(T(TIM_CCR1)) == 100u && reg_read(T(TIM_CCR3)) == 100u);
    CHECK(i1 >= 0 && i3 > i1 && iu > i3 && ic > iu && imoe > ic);
    CHECK((uint32_t)imoe == rf_nlog() - 1u);
    CHECK(reg_read(T(TIM_CCER)) == 0x505u && (reg_read(T(TIM_BDTR)) & (1u << 15)) && (reg_read(T(TIM_CR1)) & 1u));
    /* stop: MOE cleared first, then CCER, then the four bridge pins analog */
    m = rf_nlog();
    hal_pwm_stop();
    CHECK(rf_log(m)->addr == T(TIM_BDTR) && !(rf_log(m)->val & (1u << 15)));
    CHECK(rf_find(T(TIM_CCER), m) > (int32_t)m);
    CHECK(((reg_read(GA + GPIO_MODER) >> 16) & 3u) == 3u && ((reg_read(GA + GPIO_MODER) >> 14) & 3u) == 3u);
    CHECK(((reg_read(GA + GPIO_MODER) >> 20) & 3u) == 3u && ((reg_read(GB + GPIO_MODER) >> 30) & 3u) == 3u);

    /* break (TIM1 side): BKE + BKCMP7E; the MDF1 side is not written yet -> HAL_ENOTIMPL so the app never starts the bridge */
    CHECK(hal_brk_arm(300u) == HAL_ENOTIMPL);
    CHECK((reg_read(T(TIM_BDTR)) & (1u << 12)) && !(reg_read(T(TIM_BDTR)) & (1u << 13)));
    CHECK(reg_read(T(TIM_AF1)) & (1u << 7));
    rf_poke(T(TIM_SR), (1u << 7) | 1u);                           /* hardware: break latched (BIF) + UIF */
    CHECK(hal_brk_latched());
    CHECK(hal_pwm_start() == HAL_BUSY);
    hal_brk_clear();
    CHECK(!hal_brk_latched() && (reg_read(T(TIM_SR)) & 1u));     /* rc_w0: only BIF cleared */
    hal_brk_disarm();
    CHECK(!(reg_read(T(TIM_AF1)) & (1u << 7)) && !(reg_read(T(TIM_BDTR)) & (1u << 12)));
    printf("{\"checks\": %u, \"fails\": %u}\n", checks, fails);
    return fails ? 1 : 0;
}
