/* fw/test/port/test_regs.c: U575 register layer (fw/port_u575/hal_u575_periph.c) against RM0456 Rev 7 values, recorded-register fake.
 * Prints one JSON line; exit 1 on any failure. Run by fwsim (row port_u575.regs). */
#include <stdio.h>

#include "hal.h"
#include "reg.h"
#include "regfake.h"

const uint32_t *u575_burst_buf(uint32_t i);
void u575_dma_tc_isr(void);
#define LLR_BITS ((1u << 29) | (1u << 28) | (1u << 16))

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

    /* ---- I2C2 (charger, 100 kHz from HSI16): clock + pins + timing, write and read transactions, NACK, timeout */
    rf_reset();
    uint8_t w2[2] = {0xC0u, 0x00u}, rb[3] = {0};
    CHECK(hal_i2c_write(0x6Au, 0x0Bu, w2, 2u) == HAL_OK);
    CHECK(reg_read(RCC_CR) & (1u << 10));
    CHECK(((reg_read(RCC_CCIPR1) >> 12) & 3u) == 2u);
    CHECK(reg_read(RCC_APB1ENR1) & (1u << 22));
    CHECK(reg_read(I2C2_BASE + I2C_TIMINGR) == 0x30420F13u);
    CHECK((reg_read(GB + GPIO_OTYPER) & ((1u << 13) | (1u << 14))) == ((1u << 13) | (1u << 14)));
    CHECK(((reg_read(GB + GPIO_AFRH) >> 20) & 0xFu) == 4u && ((reg_read(GB + GPIO_AFRH) >> 24) & 0xFu) == 4u);   /* AF4 I2C2 */
    CHECK(rf_find(I2C2_BASE + I2C_TIMINGR, 0u) < rf_find(I2C2_BASE + I2C_CR1, (uint32_t)rf_find(I2C2_BASE + I2C_TIMINGR, 0u)));
    CHECK(rf_i2c_regs()[0x0B] == 0xC0u && rf_i2c_regs()[0x0C] == 0x00u);
    {
        int32_t c2 = rf_find(I2C2_BASE + I2C_CR2, 0u);
        CHECK(c2 >= 0 && rf_log((uint32_t)c2)->val == ((0x6Au << 1) | (3u << 16) | (1u << 25) | (1u << 13)));
    }
    rf_i2c_regs()[3] = 0x46u;
    rf_i2c_regs()[4] = 0x2Cu;
    rf_i2c_regs()[5] = 0x2Cu;
    CHECK(hal_i2c_read(0x6Au, 0x03u, rb, 3u) == HAL_OK);
    CHECK(rb[0] == 0x46u && rb[1] == 0x2Cu && rb[2] == 0x2Cu);
    CHECK(hal_i2c_read(0x55u, 0x00u, rb, 1u) == HAL_NACK);
    CHECK((reg_read(I2C2_BASE + I2C_ISR) & 0x30u) == 0u);           /* NACKF / STOPF cleared */
    rf_i2c_hold(1u);
    CHECK(hal_i2c_write(0x6Au, 0x04u, w2, 1u) == HAL_TIMEOUT);
    rf_i2c_hold(0u);
    CHECK(hal_i2c_recover() == HAL_OK);
    CHECK(hal_i2c_write(0x6Au, 0x04u, w2, 1u) == HAL_OK);

    /* ---- ADC1: power-up order (DEEPPWD off -> ADVREGEN -> LDORDY -> ADCAL -> ADEN -> ADRDY), single conversions in mV */
    rf_reset();
    rf_adc_code(7u, 2075u);                                           /* TS: 2075 / 16383 x 3000 = 380 mV (25 C on the 10 k NTC) */
    uint16_t mv = 0;
    CHECK(hal_adc_read_mv(HAL_ADC_TS, &mv) == HAL_OK);
    CHECK(mv == 380u);
    {
        int32_t i_deep = -1, i_reg = -1, i_cal = -1, i_en = -1;
        for (uint32_t i = 0; i < rf_nlog(); i++) {
            const rf_write_t *w = rf_log(i);
            if (w->addr != ADC1_BASE + ADC_CR) continue;
            if (i_deep < 0 && !(w->val & (1u << 29))) i_deep = (int32_t)i;
            if (i_reg < 0 && (w->val & (1u << 28))) i_reg = (int32_t)i;
            if (i_en < 0 && (w->val & 1u)) i_en = (int32_t)i;
        }
        i_cal = rf_find(ADC1_BASE + ADC_CR, (uint32_t)(i_reg + 1));
        CHECK(i_deep >= 0 && i_reg >= i_deep && i_cal > i_reg && i_en > i_cal);
    }
    CHECK(reg_read(RCC_AHB2ENR1) & (1u << 10));
    CHECK(((reg_read(ADC1_BASE + ADC_SQR1) >> 6) & 31u) == 7u && (reg_read(ADC1_BASE + ADC_PCSEL) == (1u << 7)));
    CHECK(((reg_read(ADC1_BASE + ADC_SMPR1) >> 21) & 7u) == 7u);
    CHECK(hal_adc_read_mv(HAL_ADC_VBAT_SENSE, &mv) == HAL_OK && (reg_read(RCC_AHB3ENR) & (1u << 5)));   /* ADC4 powered up */

    /* ---- break, full chain (FWSIM-R65): ADC1 continuous I_SENSE -> MDF1 OLD window -> mdf_break0 -> TIM1 BKCMP7 */
    CHECK(hal_brk_arm(300u) == HAL_OK);
    CHECK(reg_read(ADC1_BASE + ADC_CFGR1) == (2u | (1u << 13)));     /* DMNGT = 10 MDF, CONT */
    CHECK(reg_read(ADC1_BASE + ADC_PCSEL) == (1u << 11) && ((reg_read(ADC1_BASE + ADC_SQR1) >> 6) & 31u) == 11u);
    CHECK(reg_read(ADC1_BASE + ADC_CR) & (1u << 2));                 /* streaming */
    CHECK(reg_read(RCC_AHB1ENR) & (1u << 3));
    CHECK(reg_read(MDF1_BASE + MDF_CKGCR) & 1u);
    CHECK(reg_read(MDF1_BASE + MDF_DFLT0CICR) == 2u);                /* DATSRC ADCITF1 */
    CHECK(reg_read(MDF1_BASE + MDF_OLD0THHR) == 164u);               /* 300 mA x 0.1 ohm = 30 mV = 164 codes */
    CHECK(reg_read(MDF1_BASE + MDF_OLD0THLR) == ((0u - 164u) & 0x03FFFFFFu));
    CHECK(reg_read(MDF1_BASE + MDF_OLD0CR) == ((1u << 4) | 1u));     /* BKOLD = mdf_break0, FastSinc, THINB 0, OLDEN */
    {
        int32_t i_thh = rf_find(MDF1_BASE + MDF_OLD0THHR, 0u), i_last = -1;
        for (int32_t j = rf_find(MDF1_BASE + MDF_OLD0CR, 0u); j >= 0; j = rf_find(MDF1_BASE + MDF_OLD0CR, (uint32_t)j + 1u))
            i_last = j;
        CHECK(i_thh >= 0 && i_last > i_thh);                          /* thresholds before OLDEN */
        CHECK(rf_find(TIM1_BASE + TIM_AF1, 0u) > i_last);            /* TIM side armed after the detector */
    }
    CHECK((reg_read(T(TIM_BDTR)) & (1u << 12)) && (reg_read(T(TIM_AF1)) & (1u << 7)));
    CHECK(hal_adc_read_mv(HAL_ADC_TS, &mv) == HAL_BUSY);             /* ADC1 dedicated while armed */
    rf_poke(T(TIM_SR), (1u << 7) | 1u);
    CHECK(hal_brk_latched());
    hal_brk_clear();
    CHECK(!hal_brk_latched() && (reg_read(T(TIM_SR)) & 1u));
    hal_brk_disarm();
    CHECK(!(reg_read(T(TIM_AF1)) & (1u << 7)) && !(reg_read(T(TIM_BDTR)) & (1u << 12)));
    CHECK(!(reg_read(MDF1_BASE + MDF_OLD0CR) & 1u) && !(reg_read(ADC1_BASE + ADC_CR) & (1u << 2)) && reg_read(ADC1_BASE + ADC_CFGR1) == 0u);
    CHECK(hal_adc_read_mv(HAL_ADC_TS, &mv) == HAL_OK);

    /* ---- GPDMA -> TIM1 DMAR bursts: 2-node linked list (ping-pong), started once both buffers are primed; underruns counted */
    rf_reset();
    CHECK(hal_pwm_config(&cfg) == HAL_OK);
    uint16_t c128[128];
    for (uint32_t i = 0; i < 128u; i++)
        c128[i] = (uint16_t)(60u + i % 80u);
    CHECK(hal_pwm_submit(c128, 128u) == HAL_OK);
    CHECK(!(reg_read(DMA_REG(DMA_CCR)) & 1u));                        /* not started with one buffer */
    CHECK(hal_pwm_submit(c128, 128u) == HAL_OK);
    CHECK(reg_read(TIM1_BASE + TIM_DCR) == (13u | (2u << 8)));
    CHECK(reg_read(T(TIM_DIER)) & (1u << 8));
    CHECK(reg_read(RCC_AHB1ENR) & 1u);
    CHECK(reg_read(DMA_REG(DMA_CTR1)) == (2u | (1u << 3) | (2u << 4) | (2u << 16) | (2u << 20)));
    CHECK(reg_read(DMA_REG(DMA_CTR2)) == 46u && reg_read(DMA_REG(DMA_CBR1)) == 128u * 12u);
    CHECK(reg_read(DMA_REG(DMA_CDAR)) == TIM1_BASE + TIM_DMAR);
    CHECK((reg_read(DMA_REG(0xCCu)) & (LLR_BITS)) == LLR_BITS);       /* node link updates SAR, BR1 and LLR */
    CHECK(reg_read(DMA_REG(DMA_CCR)) == (1u | (1u << 8)) && (uint32_t)rf_find(DMA_REG(DMA_CCR), 0u) == rf_nlog() - 1u);   /* EN + TCIE last */
    {
        const uint32_t *b = u575_burst_buf(0u);
        CHECK(b[0] == 60u && b[1] == 0u && b[2] == 140u && b[3 * 127] == 60u + 127u % 80u && b[3 * 127 + 2] == 200u - (60u + 127u % 80u));
    }
    CHECK(hal_pwm_submit(c128, 128u) == HAL_BUSY);                    /* both queued */
    u575_dma_tc_isr();                                                /* hop 0 played */
    CHECK(hal_pwm_submit(c128, 128u) == HAL_OK);
    u575_dma_tc_isr();
    u575_dma_tc_isr();                                                /* hops 1, 2 played; hop 3 never submitted ... */
    u575_dma_tc_isr();                                                /* ... underrun */
    CHECK(hal_pwm_underruns() == 1u);
    CHECK(u575_burst_buf(0u)[0] == 100u && u575_burst_buf(0u)[2] == 100u);   /* refilled with the centre (silence) */
    CHECK(hal_pwm_submit(c128, 513u) == HAL_EINVAL);
    CHECK(hal_pwm_submit(c128, 64u) == HAL_EINVAL);                   /* length fixed while running */

    /* ==== round 9 ==== */
    /* ADC4 VBAT (12 bit, IN9) - also while the break owns ADC1 */
    rf_reset();
    rf_adc4_code(9u, 2526u);                                         /* 2526 / 4095 x 3000 = 1850 mV = VBAT 3.70 V / 2 */
    CHECK(hal_brk_arm(300u) == HAL_OK);
    CHECK(hal_adc_read_mv(HAL_ADC_VBAT_SENSE, &mv) == HAL_OK && mv == 1851u);
    CHECK(reg_read(ADC4_BASE + ADC4_CHSELR) == (1u << 9));
    hal_brk_disarm();
    /* I2C bus clear: SDA held for 3 clocks -> released, STOP, HAL_OK; held forever -> HAL_BUSY after 9 */
    rf_sda_stuck(3u);
    CHECK(hal_i2c_recover() == HAL_OK);
    CHECK(reg_read(I2C2_BASE + I2C_CR1) & 1u);                      /* controller re-initialised */
    CHECK(((reg_read(GB + GPIO_MODER) >> 26) & 3u) == 2u);           /* SCL back on AF */
    rf_sda_stuck(100u);
    CHECK(hal_i2c_recover() == HAL_BUSY);

    /* clock plans: P80 from reset (Range 4) -> Range 2 + booster + 2 WS before PLL1 runs; P52 lowers range after; P112 = Range 1 */
    rf_reset();
    CHECK(hal_clock_set_plan(HAL_CLK_P80) == HAL_OK);
    CHECK(hal_clock_hclk_hz() == 80009000u);
    CHECK(((reg_read(PWR_VOSR) >> 16) & 3u) == 2u && (reg_read(PWR_VOSR) & (1u << 18)));
    CHECK((reg_read(FLASH_ACR) & 0xFu) == 2u);
    CHECK(reg_read(RCC_PLL1CFGR) == (1u | (3u << 2) | (2u << 8) | (2u << 12) | (1u << 18)));
    CHECK(reg_read(RCC_PLL1DIVR) == (19u | (3u << 24)));
    CHECK((reg_read(RCC_CFGR1) & 3u) == 3u);
    CHECK(reg_read(PWR_CR3) & 2u);                                   /* SMPS */
    {
        int32_t i_vos = rf_find(PWR_VOSR, 0u), i_lat = rf_find(FLASH_ACR, 0u), i_pll = -1, i_sw = -1;
        for (uint32_t i = 0; i < rf_nlog(); i++) {
            if (rf_log(i)->addr == RCC_CR && (rf_log(i)->val & (1u << 24)) && i_pll < 0) i_pll = (int32_t)i;
            if (rf_log(i)->addr == RCC_CFGR1 && (rf_log(i)->val & 3u) == 3u && i_sw < 0) i_sw = (int32_t)i;
        }
        CHECK(i_vos >= 0 && i_lat > i_vos && i_pll > i_lat && i_sw > i_pll);
    }
    uint32_t mk = rf_nlog();
    CHECK(hal_clock_set_plan(HAL_CLK_P52) == HAL_OK);
    CHECK(((reg_read(PWR_VOSR) >> 16) & 3u) == 1u && !(reg_read(PWR_VOSR) & (1u << 18)));   /* Range 3, no booster */
    CHECK(reg_read(RCC_PLL1DIVR) == (12u | (3u << 24)) && (reg_read(FLASH_ACR) & 0xFu) == 2u);
    CHECK(rf_find(PWR_VOSR, mk) > rf_find(RCC_CFGR1, mk));           /* range lowered after the clock */
    CHECK(hal_clock_set_plan(HAL_CLK_P112) == HAL_OK);
    CHECK(((reg_read(PWR_VOSR) >> 16) & 3u) == 3u && (reg_read(FLASH_ACR) & 0xFu) == 3u && hal_clock_hclk_hz() == 112012000u);
    CHECK(hal_clock_set_plan(HAL_CLK_P72) == HAL_OK);
    CHECK(((reg_read(PWR_VOSR) >> 16) & 3u) == 2u && reg_read(RCC_PLL1DIVR) == (17u | (3u << 24)));
    rf_poke(T(TIM_CR1), 1u);
    CHECK(hal_clock_set_plan(HAL_CLK_P80) == HAL_BUSY);              /* TIM1 running */
    rf_poke(T(TIM_CR1), 0u);
    /* Stop 2 prep: PLL2/PLL3/HSI48/SHSI off and not ready */
    rf_poke(RCC_CR, reg_read(RCC_CR) | (1u << 26) | (1u << 27) | (1u << 12) | (1u << 13));
    CHECK(hal_clock_stop_prep() == HAL_OK);
    CHECK((reg_read(RCC_CR) & ((1u << 26) | (1u << 27) | (1u << 12) | (1u << 13) | (1u << 28) | (1u << 14))) == 0u);
    /* RTC wake-up 60 s on the LSE: unlock 0xCA 0x53, WUTE off, WUTR 59, ck_spre, WUTE + WUTIE, relock */
    CHECK(hal_power_rtc_wakeup_s(60u) == HAL_OK);
    CHECK(reg_read(PWR_DBPR) & 1u);
    CHECK(((reg_read(RCC_BDCR) >> 8) & 3u) == 1u && (reg_read(RCC_BDCR) & (1u << 15)));
    CHECK(reg_read(RTC_WUTR) == 59u && (reg_read(RTC_CR) & 7u) == 4u && (reg_read(RTC_CR) & (1u << 10)) && (reg_read(RTC_CR) & (1u << 14)));
    {
        int32_t k1 = rf_find(RTC_WPR, 0u);
        CHECK(k1 >= 0 && rf_log((uint32_t)k1)->val == 0xCAu && rf_log((uint32_t)k1 + 1u)->addr == RTC_WPR && rf_log((uint32_t)k1 + 1u)->val == 0x53u);
        CHECK(reg_read(RTC_WPR) == 0xFFu);
    }
    /* Stop 2: LPMS 010, SLEEPDEEP around WFI, wake sources decoded and their flags cleared */
    rf_wake(4u);
    CHECK(hal_power_stop2() == HAL_WAKE_RTC);
    CHECK((reg_read(PWR_CR1) & 7u) == 2u && !(reg_read(SCB_SCR) & 4u) && !(reg_read(RTC_SR) & 4u));
    CHECK(reg_read(PWR_WUCR1) & 1u && (reg_read(EXTI_IMR1) & ((1u << 1) | (1u << 15))) == ((1u << 1) | (1u << 15)));
    CHECK(reg_read(EXTI_FTSR1) & (1u << 15) && reg_read(EXTI_RTSR1) & (1u << 1));
    rf_wake(1u);
    CHECK(hal_power_stop2() == HAL_WAKE_BUTTON && !(reg_read(PWR_WUSR) & 1u));
    rf_wake(2u);
    CHECK(hal_power_stop2() == HAL_WAKE_CHG_INT && !(reg_read(EXTI_FPR1) & (1u << 15)));
    rf_wake(3u);
    CHECK(hal_power_stop2() == HAL_WAKE_VBUS);
    CHECK(hal_clock_hclk_hz() == 48005000u);                          /* Stop exit on MSIS: plan restored by the caller */

    /* ADF1 D1 at P80: CCK = 80.009 / 2 / 10 = 4.0009 MHz (PROCDIV+1 2, CCKDIV+1 10), normal SPI, Sinc5 /5, RSFLT /4, HPF 1.9 kHz, DMA 98 */
    rf_reset();
    CHECK(hal_clock_set_plan(HAL_CLK_P80) == HAL_OK);
    CHECK(hal_adf_start(4000450u) == HAL_OK);
    CHECK(reg_read(ADF1_BASE + ADF_CKGCR) == ((1u << 24) | (9u << 16) | (1u << 5) | (1u << 1) | 1u));
    CHECK(reg_read(ADF1_BASE + ADF_SITF0CR) == ((4u << 8) | (1u << 4) | 1u));
    CHECK(reg_read(ADF1_BASE + ADF_DFLT0CICR) == ((5u << 4) | (4u << 8)) && reg_read(ADF1_BASE + ADF_DFLT0RSFR) == (3u << 8));
    CHECK(reg_read(GPDMA1_BASE + 0x80u * DMA_ADF_CH + DMA_CTR2) == 98u);
    CHECK((uint32_t)rf_find(ADF1_BASE + ADF_DFLT0CR, 0u) == rf_nlog() - 1u && reg_read(ADF1_BASE + ADF_DFLT0CR) == 3u);
    CHECK(((reg_read(GB + GPIO_AFRL) >> 12) & 0xFu) == 3u);          /* PB3 AF3 ADF1_CCK0 */
    CHECK(hal_clock_set_plan(HAL_CLK_P72) == HAL_BUSY);              /* ADF running */
    hal_adf_stop();
    CHECK(!(reg_read(ADF1_BASE + ADF_DFLT0CR) & 1u) && !(reg_read(ADF1_BASE + ADF_CKGCR) & 2u));

    /* USB lifecycle (R28): nothing without VBUS; with VBUS: HSI48, USV, OTGEN, AF10 pins, transceiver on, connect; off reverses */
    CHECK(hal_usb_enable(true) == HAL_EINVAL);
    rf_poke(GA + GPIO_IDR, 1u << 1);                                 /* PA1 VBUS_SENSE high */
    CHECK(hal_usb_vbus());
    CHECK(hal_usb_enable(true) == HAL_OK);
    CHECK((reg_read(RCC_CR) & (1u << 13)) && (reg_read(PWR_SVMCR) & (1u << 28)) && (reg_read(RCC_AHB2ENR1) & (1u << 14)));
    CHECK(((reg_read(GA + GPIO_AFRH) >> 12) & 0xFu) == 10u && ((reg_read(GA + GPIO_AFRH) >> 16) & 0xFu) == 10u);
    CHECK((reg_read(OTG_BASE + OTG_GCCFG) & (1u << 16)) && !(reg_read(OTG_BASE + OTG_DCTL) & 2u) && (reg_read(OTG_BASE + OTG_GUSBCFG) & (1u << 30)));
    mk = rf_nlog();
    CHECK(hal_usb_enable(false) == HAL_OK);
    CHECK(rf_log(mk)->addr == OTG_BASE + OTG_DCTL && (rf_log(mk)->val & 2u));   /* soft disconnect first */
    CHECK(((reg_read(GA + GPIO_MODER) >> 22) & 3u) == 3u && ((reg_read(GA + GPIO_MODER) >> 24) & 3u) == 3u);
    CHECK(!(reg_read(RCC_AHB2ENR1) & (1u << 14)) && !(reg_read(PWR_SVMCR) & (1u << 28)));
    printf("{\"checks\": %u, \"fails\": %u}\n", checks, fails);
    return fails ? 1 : 0;
}
