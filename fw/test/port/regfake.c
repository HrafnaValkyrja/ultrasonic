/* fw/test/port/regfake.c: recorded-register fake for the U575 port register layer (FW_REG_RECORD). Sparse register file with RM0456 reset
 * values where they matter (GPIO MODER), a write log, and the rc_w0 semantics of TIMx_SR. */
#include <stdint.h>
#include <string.h>

#include "regfake.h"
#include "reg.h"

static uint32_t addr_[512], val_[512], n_;
/* device models */
static uint8_t i2c_regs[256];
static uint32_t i2c_target = 0x6Au, i2c_hold, i2c_ptr, i2c_left, i2c_rd, i2c_auto, i2c_first;
static uint16_t adc_code[20], adc4_code[24];
static uint32_t sda_stuck_clocks, scl_rises, wake_flag;
static rf_write_t log_[4096];
static uint32_t nlog_;

static uint32_t reset_value(uint32_t a)
{
    if (a == PWR_VOSR)
        return 0x8000u;                                /* Range 4, VOSRDY */
    if (a == ADC1_BASE + ADC_CR)
        return 1u << 29;                               /* DEEPPWD = 1 at reset */
    if (a == I2C2_BASE + I2C_ISR)
        return 1u;                                     /* TXE */
    if (a >= 0x42020000u && a < 0x42022400u && (a & 0x3FFu) == GPIO_MODER) {
        uint32_t port = (a - 0x42020000u) / 0x400u;
        return port == 0u ? 0xABFFFFFFu : (port == 1u ? 0xFFFFFEBFu : 0xFFFFFFFFu);   /* RM0456 GPIOx_MODER reset values */
    }
    return 0u;
}

static uint32_t *slot(uint32_t a)
{
    for (uint32_t i = 0; i < n_; i++)
        if (addr_[i] == a)
            return &val_[i];
    if (n_ >= 512u)
        return NULL;
    addr_[n_] = a;
    val_[n_] = reset_value(a);
    return &val_[n_++];
}

void rf_reset(void)
{
    n_ = 0u;
    nlog_ = 0u;
    i2c_hold = 0u;
    memset(i2c_regs, 0, sizeof i2c_regs);
    memset(adc_code, 0, sizeof adc_code);
    memset(adc4_code, 0, sizeof adc4_code);
    sda_stuck_clocks = 0u;
    scl_rises = 0u;
    wake_flag = 0u;
}

#define ISR_I2C (I2C2_BASE + I2C_ISR)
static void i2c_isr(uint32_t v) { rf_poke(ISR_I2C, v); }

void reg_write(uint32_t a, uint32_t v)
{
    uint32_t *s = slot(a);
    if (s == NULL)
        return;
    if (a == TIM1_BASE + TIM_SR)
        *s &= v;                                       /* rc_w0 */
    else if (a == ADC1_BASE + ADC_ISR || a == ADC4_BASE || a == EXTI_FPR1 || a == EXTI_RPR1 || a == ADF1_BASE + ADF_DFLT0ISR)
        *s &= ~v;                                      /* rc_w1 */
    else if (a == PWR_WUSCR || a == RTC_SCR) {
        *s = v;
        rf_poke(a == PWR_WUSCR ? PWR_WUSR : RTC_SR, reg_read(a == PWR_WUSCR ? PWR_WUSR : RTC_SR) & ~v);   /* clear-flag registers */
    }
    else
        *s = v;
    /* RCC: every oscillator / PLL ready (or not) at once */
    if (a == RCC_CR) {
        static const uint8_t on_rdy[][2] = {{0, 2}, {8, 10}, {12, 13}, {14, 15}, {24, 25}, {26, 27}, {28, 29}};
        for (uint32_t i = 0; i < sizeof on_rdy / sizeof on_rdy[0]; i++)
            *s = (*s & ~(1u << on_rdy[i][1])) | (((*s >> on_rdy[i][0]) & 1u) << on_rdy[i][1]);
    }
    if (a == RCC_BDCR)
        *s = (*s & ~((1u << 1) | (1u << 27))) | ((*s & 1u) << 1) | (((*s >> 26) & 1u) << 27);
    if (a == RCC_CFGR1)
        *s = (*s & ~(3u << 2)) | ((*s & 3u) << 2);                 /* SWS follows SW */
    if (a == PWR_VOSR)
        *s = ((*s | (1u << 15)) & ~(1u << 14)) | (((*s >> 18) & 1u) << 14);   /* VOSRDY; BOOSTRDY follows BOOSTEN */
    if (a == RTC_CR && !(v & (1u << 10)))
        rf_poke(RTC_ICSR, reg_read(RTC_ICSR) | (1u << 2));        /* WUTWF while WUTE = 0 */
    if (a == 0x42020400u + GPIO_BSRR && (v & (1u << 13)))
        scl_rises++;                                              /* PB13 SCL released high */
    /* ADC4: same flag behaviour as ADC1, channel from CHSELR */
    if (a == ADC4_BASE + 0x08u) {
        uint32_t *isr = slot(ADC4_BASE + 0x00u);
        if (v & (1u << 28)) *isr |= 1u << 12;
        if (v & (1u << 31)) *s &= ~(1u << 31);
        if (v & 1u) *isr |= 1u;
        if (v & (1u << 2)) {
            uint32_t m = reg_read(ADC4_BASE + ADC4_CHSELR), ch = 0;
            while (ch < 24u && !(m & (1u << ch))) ch++;
            rf_poke(ADC4_BASE + 0x40u, ch < 24u ? adc4_code[ch] : 0u);
            *isr |= 1u << 2;
            *s &= ~(1u << 2);
        }
    }

    /* ADC1 */
    if (a == ADC1_BASE + ADC_CR) {
        uint32_t *isr = slot(ADC1_BASE + ADC_ISR);
        if (v & (1u << 28)) *isr |= 1u << 12;          /* ADVREGEN -> LDORDY */
        if (v & (1u << 31)) *s &= ~(1u << 31);          /* ADCAL completes at once */
        if (v & 1u) *isr |= 1u;                         /* ADEN -> ADRDY */
        if (v & (1u << 4)) *s &= ~((1u << 4) | (1u << 2));   /* ADSTP stops at once */
        if ((v & (1u << 2)) && (reg_read(ADC1_BASE + ADC_CFGR1) & 3u) == 0u) {
            uint32_t ch = (reg_read(ADC1_BASE + ADC_SQR1) >> 6) & 31u;
            rf_poke(ADC1_BASE + ADC_DR, ch < 20u ? adc_code[ch] : 0u);
            *isr |= 1u << 2;                            /* EOC; single conversion: ADSTART clears */
            *s &= ~(1u << 2);
        }
    }
    /* I2C2 controller + one target (register file, auto-increment pointer) */
    if (a == I2C2_BASE + I2C_CR2 && (v & (1u << 13))) {
        uint32_t addr = (v >> 1) & 0x7Fu;
        i2c_rd = (v >> 10) & 1u;
        i2c_left = (v >> 16) & 0xFFu;
        i2c_auto = (v >> 25) & 1u;
        i2c_first = !i2c_rd;
        if (i2c_hold)
            i2c_isr(0u);
        else if (addr != i2c_target)
            i2c_isr((1u << 4) | (1u << 5));
        else if (i2c_rd)
            i2c_isr(1u << 2);
        else
            i2c_isr(1u << 1);
    }
    if (a == I2C2_BASE + I2C_TXDR) {
        if (i2c_first) {
            i2c_ptr = v & 0xFFu;
            i2c_first = 0u;
        } else {
            i2c_regs[i2c_ptr++ & 0xFFu] = (uint8_t)v;
        }
        i2c_left--;
        i2c_isr(i2c_left ? (1u << 1) : (i2c_auto ? (1u << 5) : (1u << 6)));
    }
    if (a == I2C2_BASE + I2C_ICR)
        rf_poke(ISR_I2C, reg_read(ISR_I2C) & ~(v & 0x30u));
    if (nlog_ < 4096u) {
        log_[nlog_].addr = a;
        log_[nlog_].val = *s;
        nlog_++;
    }
}

uint32_t reg_read(uint32_t a)
{
    uint32_t *s = slot(a);
    if (a == I2C2_BASE + I2C_RXDR && s) {
        *s = i2c_regs[i2c_ptr++ & 0xFFu];
        i2c_left--;
        rf_poke(ISR_I2C, i2c_left ? (1u << 2) : (1u << 5));
    }
    if (a == 0x42020400u + GPIO_IDR && s)              /* PB14 SDA: held low by a stuck target for sda_stuck_clocks SCL pulses */
        *s = (*s & ~(1u << 14)) | (scl_rises >= sda_stuck_clocks ? (1u << 14) : 0u);
    if (a == ADC1_BASE + ADC_DR && s)
        rf_poke(ADC1_BASE + ADC_ISR, reg_read(ADC1_BASE + ADC_ISR) & ~(1u << 2));   /* reading DR clears EOC */
    return s ? *s : 0u;
}

uint8_t *rf_i2c_regs(void) { return i2c_regs; }
void rf_sda_stuck(uint32_t clocks) { sda_stuck_clocks = clocks; scl_rises = 0u; }
void rf_adc4_code(uint32_t ch, uint16_t code) { if (ch < 24u) adc4_code[ch] = code; }
void rf_wake(uint32_t which) { wake_flag = which; }
/* TinyUSB stands in: what its dcd_dwc2 init / disconnect write first (core start = connect, stop = soft disconnect) */
void u575_usb_core_start(void)
{
    reg_write(OTG_BASE + OTG_GUSBCFG, reg_read(OTG_BASE + OTG_GUSBCFG) | (1u << 30));
    reg_write(OTG_BASE + OTG_GCCFG, reg_read(OTG_BASE + OTG_GCCFG) | (1u << 16));
    reg_write(OTG_BASE + OTG_DCTL, reg_read(OTG_BASE + OTG_DCTL) & ~(1u << 1));
}
void u575_usb_core_stop(void) { reg_write(OTG_BASE + OTG_DCTL, reg_read(OTG_BASE + OTG_DCTL) | (1u << 1)); }
static uint32_t resets;
void u575_system_reset(void) { resets++; }
uint32_t rf_resets(void) { return resets; }
void u575_wfi(void)                                    /* "hardware": the wake source the test scripted raises its flag */
{
    if (wake_flag == 1u) rf_poke(PWR_WUSR, 1u);
    if (wake_flag == 2u) rf_poke(EXTI_FPR1, 1u << 15);
    if (wake_flag == 3u) rf_poke(EXTI_RPR1, 1u << 1);
    if (wake_flag == 4u) rf_poke(RTC_SR, 1u << 2);
}
void rf_i2c_hold(uint32_t on) { i2c_hold = on; }
void rf_adc_code(uint32_t ch, uint16_t code) { if (ch < 20u) adc_code[ch] = code; }

void rf_poke(uint32_t a, uint32_t v)                   /* hardware-side change (no log) */
{
    uint32_t *s = slot(a);
    if (s)
        *s = v;
}

uint32_t rf_nlog(void) { return nlog_; }
const rf_write_t *rf_log(uint32_t i) { return &log_[i]; }
int32_t rf_find(uint32_t a, uint32_t from)
{
    for (uint32_t i = from; i < nlog_; i++)
        if (log_[i].addr == a)
            return (int32_t)i;
    return -1;
}
