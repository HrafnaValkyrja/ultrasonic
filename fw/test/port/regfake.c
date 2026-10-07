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
static uint16_t adc_code[20];
static rf_write_t log_[4096];
static uint32_t nlog_;

static uint32_t reset_value(uint32_t a)
{
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
    else if (a == ADC1_BASE + ADC_ISR)
        *s &= ~v;                                      /* rc_w1 */
    else
        *s = v;
    /* RCC: HSI16 ready at once */
    if (a == RCC_CR && (v & (1u << 8)))
        *s |= 1u << 10;
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
    if (a == ADC1_BASE + ADC_DR && s)
        rf_poke(ADC1_BASE + ADC_ISR, reg_read(ADC1_BASE + ADC_ISR) & ~(1u << 2));   /* reading DR clears EOC */
    return s ? *s : 0u;
}

uint8_t *rf_i2c_regs(void) { return i2c_regs; }
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
