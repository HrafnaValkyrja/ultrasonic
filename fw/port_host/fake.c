/* fw/port_host/fake.c: stateful fakes of every fw/hal function (FWSIM-R2). */
#include "fake.h"

#include <string.h>

#include "fmac_model.h"

#define FAKE_NAME(f) #f,
const char *const fake_fn_name[FAKE_FN_COUNT] = {FAKE_HAL_FUNCS(FAKE_NAME)};
#undef FAKE_NAME

#define ADF_SCRIPT_CAP 16u
#define I2C_DEV_CAP 4u
#define FLASH_BYTES (HAL_FLASH_KNOB_PAGES * HAL_FLASH_PAGE_BYTES)

typedef struct { uint32_t active, start, end; hal_status_t err; } fault_t;

static struct {
    fake_call_t log[FAKE_LOG_CAP];
    uint32_t log_n;                       /* total entries ever written */
    uint32_t calls[FAKE_FN_COUNT];
    fault_t fault[FAKE_FN_COUNT];
    uint64_t t_us;
    hal_clock_plan_t plan;
    hal_reset_cause_t reset_cause;
    hal_wake_t wake;
    uint32_t resets, ucpd_dbdis;
    hal_gpio_mode_t gpio_mode[BOARD_PIN_COUNT];
    bool gpio_out[BOARD_PIN_COUNT], gpio_in[BOARD_PIN_COUNT];
    uint16_t adc[HAL_ADC_CH_COUNT][64];
    uint32_t adc_n[HAL_ADC_CH_COUNT], adc_i[HAL_ADC_CH_COUNT];
    int32_t adf_script[ADF_SCRIPT_CAP][128];
    uint32_t adf_head, adf_count;
    int32_t adf_dma[FW_RING_CAP][128];
    uint32_t adf_dma_next;
    fw_ring_t adf_ring;
    uint32_t adf_flags, adf_running, adf_cck_hz, adf_taken;
    uint8_t adf_taken_idx;
    fake_pwm_state_t pwm;
    uint16_t pwm_last[FW_RING_CAP * 64u];
    size_t pwm_last_n;
    uint32_t pwm_hops, pwm_underruns;
    uint8_t i2c_addr[I2C_DEV_CAP];
    uint8_t i2c_reg[I2C_DEV_CAP][256];
    uint32_t i2c_n;
    uint32_t bq_attached, bq_wd_started, pa1_stuck;
    uint64_t bq_last_us;
    fake_bq_state_t bq;
    fake_brk_state_t brk;
    fake_lp_state_t lp;
    bool vbus, usb_on;
    uint8_t usb_rx[512], usb_tx[512];
    size_t usb_rx_n, usb_rx_i, usb_tx_n;
    uint32_t dfu_requests, usb_cfg, bq_flat;
    uint8_t flash[FLASH_BYTES];
    uint32_t flash_ops, flash_fail_at, flash_dead, flash_ecc;
    uint32_t wdt_started, wdt_ms, wdt_kicks;
    uint32_t irq_state;
} F;

/* ------------------------------------------------------------------------------------------- plumbing */
static void log_call(fake_fn_t fn, uint32_t a0, uint32_t a1)
{
    fake_call_t *c = &F.log[F.log_n % FAKE_LOG_CAP];
    c->fn = (uint16_t)fn;
    c->pad = 0u;
    c->a0 = a0;
    c->a1 = a1;
    c->t_us = F.t_us;
    F.log_n++;
}

/* log the call, count it, and return the injected fault for this call (HAL_OK if none) */
static hal_status_t enter(fake_fn_t fn, uint32_t a0, uint32_t a1)
{
    uint32_t n = F.calls[fn]++;
    log_call(fn, a0, a1);
    fault_t *f = &F.fault[fn];
    if (f->active && n >= f->start && (f->end == 0xFFFFFFFFu || n < f->end))
        return f->err;
    return HAL_OK;
}

void fake_reset(void)
{
    memset(&F, 0, sizeof F);
    F.plan = HAL_CLK_P80;
    F.reset_cause = HAL_RESET_POWER_LOSS;
    memset(F.flash, 0xFF, sizeof F.flash);
    F.flash_fail_at = 0xFFFFFFFFu;
    F.flash_ecc = 0xFFFFFFFFu;
    for (uint32_t i = 0; i < (uint32_t)BOARD_PIN_COUNT; i++)
        F.gpio_mode[i] = HAL_GPIO_ANALOG;
}

uint32_t fake_log_len(void) { return F.log_n < FAKE_LOG_CAP ? F.log_n : FAKE_LOG_CAP; }
const fake_call_t *fake_log_at(uint32_t i)
{
    uint32_t first = F.log_n < FAKE_LOG_CAP ? 0u : F.log_n - FAKE_LOG_CAP;
    return &F.log[(first + i) % FAKE_LOG_CAP];
}
uint32_t fake_calls(fake_fn_t fn) { return F.calls[fn]; }
int32_t fake_log_find(fake_fn_t fn, uint32_t from)
{
    for (uint32_t i = from; i < fake_log_len(); i++)
        if (fake_log_at(i)->fn == (uint16_t)fn)
            return (int32_t)i;
    return -1;
}

void fake_fault(fake_fn_t fn, uint32_t nth, uint32_t count, hal_status_t err)
{
    fault_t *f = &F.fault[fn];
    f->active = 1u;
    f->start = F.calls[fn] + nth;
    f->end = count == 0xFFFFFFFFu ? 0xFFFFFFFFu : f->start + count;
    f->err = err;
}
void fake_fault_clear(void) { memset(F.fault, 0, sizeof F.fault); }

void fake_time_set_us(uint64_t t) { F.t_us = t; }
void fake_time_advance_us(uint64_t dt) { F.t_us += dt; }

/* ------------------------------------------------------------------------------------------- clock */
static const uint32_t plan_hz[HAL_CLK_PLAN_COUNT] = {80009000u, 160018000u, 64007000u, 48005000u, 112012000u, 104011000u, 72008000u, 52006000u};   /* A3 s2 + variant plans (PCM = HCLK/400) */

hal_status_t hal_clock_set_plan(hal_clock_plan_t plan)
{
    hal_status_t e = enter(FAKE_FN_hal_clock_set_plan, (uint32_t)plan, 0u);
    if (e != HAL_OK)
        return e;
    if ((uint32_t)plan >= (uint32_t)HAL_CLK_PLAN_COUNT)
        return HAL_EINVAL;
    if (F.pwm.running || F.adf_running)
        return HAL_BUSY;                  /* FWSIM-R25: change only with ADF1 and TIM1 stopped */
    F.plan = plan;
    return HAL_OK;
}
uint32_t hal_clock_hclk_hz(void)
{
    (void)enter(FAKE_FN_hal_clock_hclk_hz, 0u, 0u);
    return plan_hz[F.plan];
}

/* ------------------------------------------------------------------------------------------- power */
hal_wake_t hal_power_stop2(void)
{
    if (enter(FAKE_FN_hal_power_stop2, 0u, 0u) != HAL_OK)
        return HAL_WAKE_NONE;
    /* pin / clock audit at entry (FWSIM-R23): bridge stopped, break disarmed, mic power off, ADF/mic and LED pins parked, clocks prepared */
    F.lp.stop2_entries++;
    uint32_t bad = 0u;
    bad += F.pwm.running != 0u;
    bad += F.brk.armed != 0u;
    bad += F.gpio_out[BOARD_PIN_MIC_VDD] != false;
    bad += F.gpio_mode[BOARD_PIN_MIC_CLK] != HAL_GPIO_ANALOG;
    bad += F.gpio_mode[BOARD_PIN_MIC_DATA] != HAL_GPIO_ANALOG;
    bad += F.gpio_mode[BOARD_PIN_LED_K] != HAL_GPIO_ANALOG;
    bad += F.lp.led_duty_ppm != 0u;
    bad += F.lp.clocks_prepped == 0u;
    bad += F.adf_running != 0u;
    F.lp.audit_violations += bad;
    F.lp.clocks_prepped = 0u;                    /* Stop 2 exit: the caller must restore the clock plan */
    hal_wake_t w = F.wake;
    F.wake = HAL_WAKE_NONE;
    if (w == HAL_WAKE_NONE && F.lp.rtc_s != 0u) {
        F.t_us += (uint64_t)F.lp.rtc_s * 1000000u;
        w = HAL_WAKE_RTC;
    }
    return w;
}
hal_status_t hal_power_rtc_wakeup_s(uint32_t seconds)
{
    hal_status_t e = enter(FAKE_FN_hal_power_rtc_wakeup_s, seconds, 0u);
    if (e != HAL_OK)
        return e;
    F.lp.rtc_s = seconds;
    return HAL_OK;
}
hal_status_t hal_clock_stop_prep(void)
{
    hal_status_t e = enter(FAKE_FN_hal_clock_stop_prep, 0u, 0u);
    if (e != HAL_OK)
        return e;
    F.lp.clocks_prepped = 1u;
    return HAL_OK;
}
hal_status_t hal_led_set(uint32_t duty_ppm)
{
    hal_status_t e = enter(FAKE_FN_hal_led_set, duty_ppm, 0u);
    if (e != HAL_OK)
        return e;
    F.lp.led_duty_ppm = duty_ppm > 1000000u ? 1000000u : duty_ppm;
    return HAL_OK;
}
const fake_lp_state_t *fake_lp(void) { return &F.lp; }
hal_reset_cause_t hal_power_reset_cause(void)
{
    (void)enter(FAKE_FN_hal_power_reset_cause, 0u, 0u);
    return F.reset_cause;
}
void hal_power_system_reset(void)
{
    (void)enter(FAKE_FN_hal_power_system_reset, 0u, 0u);
    F.resets++;
    F.reset_cause = HAL_RESET_SOFT;
}
void hal_power_ucpd_dbdis(void)
{
    (void)enter(FAKE_FN_hal_power_ucpd_dbdis, 0u, 0u);
    F.ucpd_dbdis = 1u;
}
void fake_reset_cause(hal_reset_cause_t c) { F.reset_cause = c; }
void fake_wake_source(hal_wake_t w) { F.wake = w; }

/* ------------------------------------------------------------------------------------------- gpio */
hal_status_t hal_gpio_mode(board_pin_t pin, hal_gpio_mode_t mode)
{
    hal_status_t e = enter(FAKE_FN_hal_gpio_mode, (uint32_t)pin, (uint32_t)mode);
    if (e != HAL_OK)
        return e;
    if ((uint32_t)pin >= (uint32_t)BOARD_PIN_COUNT || (uint32_t)mode >= (uint32_t)HAL_GPIO_MODE_COUNT)
        return HAL_EINVAL;
    F.gpio_mode[pin] = mode;
    return HAL_OK;
}
void hal_gpio_write(board_pin_t pin, bool high)
{
    (void)enter(FAKE_FN_hal_gpio_write, (uint32_t)pin, high ? 1u : 0u);
    if ((uint32_t)pin < (uint32_t)BOARD_PIN_COUNT)
        F.gpio_out[pin] = high;
}
bool hal_gpio_read(board_pin_t pin)
{
    if (enter(FAKE_FN_hal_gpio_read, (uint32_t)pin, 0u) != HAL_OK || (uint32_t)pin >= (uint32_t)BOARD_PIN_COUNT)
        return false;
    hal_gpio_mode_t m = F.gpio_mode[pin];
    if (m == HAL_GPIO_OUTPUT_PP)
        return F.gpio_out[pin];
    return F.gpio_in[pin];
}
void fake_gpio_input(board_pin_t pin, bool level) { F.gpio_in[pin] = level; }
bool fake_gpio_output(board_pin_t pin) { return F.gpio_out[pin]; }
hal_gpio_mode_t fake_gpio_mode_of(board_pin_t pin) { return F.gpio_mode[pin]; }

/* ------------------------------------------------------------------------------------------- adf */
hal_status_t hal_adf_start(uint32_t cck_hz)
{
    hal_status_t e = enter(FAKE_FN_hal_adf_start, cck_hz, 0u);
    if (e != HAL_OK)
        return e;
    if (cck_hz < 1000000u || cck_hz > 4800000u)
        return HAL_EINVAL;               /* D13: 3.072-4.8 MHz in use, 2.0 MHz standard-mode start */
    F.adf_running = 1u;
    F.adf_cck_hz = cck_hz;
    return HAL_OK;
}
void hal_adf_stop(void)
{
    (void)enter(FAKE_FN_hal_adf_stop, 0u, 0u);
    F.adf_running = 0u;
}
const int32_t *hal_adf_hop_take(void)
{
    if (enter(FAKE_FN_hal_adf_hop_take, 0u, 0u) != HAL_OK)
        return NULL;
    uint8_t i;
    if (!fw_ring_pop(&F.adf_ring, &i))
        return NULL;
    F.adf_taken = 1u;
    F.adf_taken_idx = i;
    return F.adf_dma[i];
}
void hal_adf_hop_release(void)
{
    (void)enter(FAKE_FN_hal_adf_hop_release, F.adf_taken_idx, 0u);
    F.adf_taken = 0u;
}
uint32_t hal_adf_flags(void)
{
    if (enter(FAKE_FN_hal_adf_flags, 0u, 0u) != HAL_OK)
        return 0u;
    uint32_t f = F.adf_flags;
    F.adf_flags = 0u;
    return f;
}
void fake_adf_script_hop(const int32_t hop[128])
{
    if (F.adf_count >= ADF_SCRIPT_CAP)
        return;
    memcpy(F.adf_script[(F.adf_head + F.adf_count) % ADF_SCRIPT_CAP], hop, sizeof F.adf_script[0]);
    F.adf_count++;
}
void fake_adf_isr(void)
{
    if (F.adf_count == 0u)
        return;
    if ((F.adf_ring.head + 1u) % FW_RING_CAP == F.adf_ring.tail) {   /* consumer too slow: drop the new hop, count it */
        F.adf_head = (F.adf_head + 1u) % ADF_SCRIPT_CAP;
        F.adf_count--;
        F.adf_ring.dropped = F.adf_ring.dropped + 1u;
        return;
    }
    uint8_t slot = (uint8_t)(F.adf_dma_next % FW_RING_CAP);
    memcpy(F.adf_dma[slot], F.adf_script[F.adf_head], sizeof F.adf_dma[0]);   /* the "DMA" moves data */
    F.adf_head = (F.adf_head + 1u) % ADF_SCRIPT_CAP;
    F.adf_count--;
    F.adf_dma_next++;
    (void)fw_ring_push(&F.adf_ring, slot);                                     /* ... and sets the flag */
}
void fake_adf_set_flags(uint32_t flags) { F.adf_flags |= flags; }
fw_ring_t *fake_adf_ring(void) { return &F.adf_ring; }

/* ------------------------------------------------------------------------------------------- pwm */
hal_status_t hal_pwm_config(const hal_pwm_cfg_t *cfg)
{
    hal_status_t e = enter(FAKE_FN_hal_pwm_config, cfg ? cfg->arr : 0u, cfg ? ((uint32_t)cfg->dtg_rise << 8 | cfg->dtg_fall) : 0u);
    if (e != HAL_OK)
        return e;
    if (cfg == NULL || cfg->arr < 50u || cfg->dtg_rise < 1u || cfg->dtg_fall < 1u || F.pwm.running)
        return HAL_EINVAL;               /* HC_ARR_MIN, HC_DEADTIME_TICKS_MIN; reconfigure only stopped */
    F.pwm.arr = cfg->arr;
    F.pwm.rcr = cfg->rcr;
    F.pwm.dtg_rise = cfg->dtg_rise;
    F.pwm.dtg_fall = cfg->dtg_fall;
    F.pwm.configured = 1u;
    return HAL_OK;
}
hal_status_t hal_pwm_start(void)
{
    hal_status_t e = enter(FAKE_FN_hal_pwm_start, 0u, 0u);
    if (e != HAL_OK)
        return e;
    if (!F.pwm.configured)
        return HAL_EINVAL;
    if (F.brk.latched)
        return HAL_BUSY;                          /* MOE cannot be set while BIF is latched */
    F.pwm.running = 1u;
    return HAL_OK;
}
void hal_pwm_stop(void)
{
    (void)enter(FAKE_FN_hal_pwm_stop, 0u, 0u);
    F.pwm.running = 0u;
}
hal_status_t hal_pwm_submit(const uint16_t *ccr, size_t n)
{
    hal_status_t e = enter(FAKE_FN_hal_pwm_submit, (uint32_t)n, ccr && n ? ccr[0] : 0u);
    if (e != HAL_OK)
        return e;
    if (ccr == NULL || n == 0u || n > sizeof F.pwm_last / sizeof F.pwm_last[0])
        return HAL_EINVAL;
    for (size_t i = 0; i < n; i++)
        if (F.pwm.configured && ccr[i] > F.pwm.arr)
            return HAL_EINVAL;          /* a CCR above ARR is a firmware bug, never a clip */
    memcpy(F.pwm_last, ccr, n * sizeof ccr[0]);
    F.pwm_last_n = n;
    F.pwm_hops++;
    return HAL_OK;
}
uint32_t hal_pwm_underruns(void)
{
    (void)enter(FAKE_FN_hal_pwm_underruns, 0u, 0u);
    return F.pwm_underruns;
}
const fake_pwm_state_t *fake_pwm(void) { return &F.pwm; }
uint32_t fake_pwm_hops(void) { return F.pwm_hops; }
const uint16_t *fake_pwm_last(size_t *n) { *n = F.pwm_last_n; return F.pwm_last; }
void fake_pwm_underrun(void) { F.pwm_underruns++; }

/* ------------------------------------------------------------------------------------------- adc */
hal_status_t hal_adc_read_mv(hal_adc_ch_t ch, uint16_t *mv)
{
    hal_status_t e = enter(FAKE_FN_hal_adc_read_mv, (uint32_t)ch, 0u);
    if (e != HAL_OK)
        return e;
    if ((uint32_t)ch >= (uint32_t)HAL_ADC_CH_COUNT || mv == NULL)
        return HAL_EINVAL;
    uint32_t n = F.adc_n[ch];
    if (n == 0u) {
        *mv = 0u;
        return HAL_OK;
    }
    uint32_t i = F.adc_i[ch] < n ? F.adc_i[ch] : n - 1u;
    *mv = F.adc[ch][i];
    if (F.adc_i[ch] < n)
        F.adc_i[ch]++;
    return HAL_OK;
}
void fake_adc_script(hal_adc_ch_t ch, const uint16_t *mv, uint32_t n)
{
    if (n > 64u)
        n = 64u;
    memcpy(F.adc[ch], mv, n * sizeof mv[0]);
    F.adc_n[ch] = n;
    F.adc_i[ch] = 0u;
}

/* ------------------------------------------------------------------------------------------- i2c */
static int i2c_dev(uint8_t addr7)
{
    for (uint32_t i = 0; i < F.i2c_n; i++)
        if (F.i2c_addr[i] == addr7)
            return (int)i;
    return -1;
}
#define BQ_ADDR 0x6Au
static const uint8_t bq_reset[13] = {0x00u, 0x00u, 0x00u, 0x46u, 0x05u, 0x2Cu, 0x56u, 0x84u, 0x4Du, 0x11u, 0x40u, 0x00u, 0xC0u};
static void bq_defaults(uint8_t *r)
{
    memcpy(&r[3], &bq_reset[3], 10u);
}
static void bq_access(int d)                      /* watchdog + status before every transaction to the charger */
{
    uint8_t *r = F.i2c_reg[d];
    if (F.bq_wd_started) {
        uint32_t sel = r[7] & 3u;
        uint64_t limit = sel == 2u ? 40000000u : 160000000u;
        if (sel != 3u && F.t_us - F.bq_last_us >= limit) {
            bq_defaults(r);
            if (sel == 0u)
                F.bq.wd_reverts++;
            else
                F.bq.hw_resets++;
            F.bq_wd_started = 0u;                 /* restarts at the next transaction */
        }
    }
    r[0] = (uint8_t)((r[0] & 0xFEu) | (F.vbus ? 1u : 0u));   /* STAT0 VIN_PGOOD */
    F.bq_last_us = F.t_us;
    F.bq_wd_started = 1u;
    F.bq.txns++;
}
void fake_bq25180_attach(void)
{
    fake_i2c_attach(BQ_ADDR);
    int d = i2c_dev(BQ_ADDR);
    if (d >= 0)
        bq_defaults(F.i2c_reg[d]);
    F.bq_attached = 1u;
}
const fake_bq_state_t *fake_bq(void) { return &F.bq; }

hal_status_t hal_i2c_write(uint8_t addr7, uint8_t reg, const uint8_t *buf, size_t len)
{
    hal_status_t e = enter(FAKE_FN_hal_i2c_write, addr7, (uint32_t)reg << 8 | (len ? buf[0] : 0u));
    if (e != HAL_OK)
        return e;
    int d = i2c_dev(addr7);
    if (d < 0)
        return HAL_NACK;
    if (buf == NULL || (size_t)reg + len > 256u)
        return HAL_EINVAL;
    if (F.bq_attached && addr7 == BQ_ADDR)
        bq_access(d);
    memcpy(&F.i2c_reg[d][reg], buf, len);
    if (F.bq_attached && addr7 == BQ_ADDR && F.bq_flat && reg <= 0x0Au && (size_t)reg + len > 0x0Au && ((F.i2c_reg[d][0x0A] >> 2) & 3u) == 1u)
        F.i2c_reg[d][0x0A] &= (uint8_t)~0x0Cu;    /* SLUSE99C 8.3.4: SYS_MODE 01 ignored while VBAT < VBUVLO */
    if (F.bq_attached && addr7 == BQ_ADDR && reg <= 9u && (size_t)reg + len > 9u && (F.i2c_reg[d][9] & 0x80u)) {
        bq_defaults(F.i2c_reg[d]);                /* SHIP_RST.REG_RST: software reset (self-clearing) */
        F.bq.sw_resets++;
    }
    return HAL_OK;
}
hal_status_t hal_i2c_read(uint8_t addr7, uint8_t reg, uint8_t *buf, size_t len)
{
    hal_status_t e = enter(FAKE_FN_hal_i2c_read, addr7, reg);
    if (e != HAL_OK)
        return e;
    int d = i2c_dev(addr7);
    if (d < 0)
        return HAL_NACK;
    if (buf == NULL || (size_t)reg + len > 256u)
        return HAL_EINVAL;
    if (F.bq_attached && addr7 == BQ_ADDR)
        bq_access(d);
    memcpy(buf, &F.i2c_reg[d][reg], len);
    return HAL_OK;
}
hal_status_t hal_i2c_recover(void) { return enter(FAKE_FN_hal_i2c_recover, 0u, 0u); }
void fake_i2c_attach(uint8_t addr7)
{
    if (F.i2c_n < I2C_DEV_CAP && i2c_dev(addr7) < 0)
        F.i2c_addr[F.i2c_n++] = addr7;
}
uint8_t *fake_i2c_regs(uint8_t addr7)
{
    int d = i2c_dev(addr7);
    return d < 0 ? NULL : F.i2c_reg[d];
}

/* ------------------------------------------------------------------------------------------- usb */
bool hal_usb_vbus(void)
{
    if (enter(FAKE_FN_hal_usb_vbus, 0u, 0u) != HAL_OK)
        return false;
    return F.pa1_stuck ? F.pa1_stuck == 2u : F.vbus;
}
hal_status_t hal_usb_enable(bool on)
{
    hal_status_t e = enter(FAKE_FN_hal_usb_enable, on ? 1u : 0u, 0u);
    if (e != HAL_OK)
        return e;
    if (on && !F.vbus)
        return HAL_EINVAL;               /* FWSIM-R28: USB only while VBUS is present */
    F.usb_on = on;
    return HAL_OK;
}
hal_usb_bus_t hal_usb_bus(void)
{
    if (enter(FAKE_FN_hal_usb_bus, 0u, 0u) != HAL_OK || !F.usb_on)
        return HAL_USB_BUS_NONE;
    return (hal_usb_bus_t)F.usb_cfg;
}
void fake_usb_bus(hal_usb_bus_t b) { F.usb_cfg = (uint32_t)b; }
void fake_bq_flat(bool flat) { F.bq_flat = flat; }
/* VBUS input current of the charger: none without VIN; SYS_MODE 01 (SYS from BAT, IN disconnected): IQ_IN only, 1 mA max (SLUSE99C 7.5,
 * charge enabled, ICHG 0 - the closest stated condition [A]); otherwise the input runs at its ILIM (a charging pod at full system load) */
uint32_t fake_bq_iin_ua(void)
{
    int d = i2c_dev(0x6Au);
    if (!F.vbus || d < 0)
        return 0u;
    const uint8_t *r = F.i2c_reg[d];
    if (((r[0x0A] >> 2) & 3u) == 1u)
        return 1000u;
    static const uint32_t ilim_ma[8] = {50u, 100u, 200u, 300u, 400u, 500u, 700u, 1100u};
    return ilim_ma[r[0x08] & 7u] * 1000u;
}
uint32_t fake_dfu_requests(void) { return F.dfu_requests; }
size_t hal_usb_cdc_write(const uint8_t *buf, size_t len)
{
    if (enter(FAKE_FN_hal_usb_cdc_write, (uint32_t)len, 0u) != HAL_OK || !F.usb_on || buf == NULL)
        return 0u;
    size_t room = sizeof F.usb_tx - F.usb_tx_n, n = len < room ? len : room;
    memcpy(&F.usb_tx[F.usb_tx_n], buf, n);
    F.usb_tx_n += n;
    return n;
}
size_t hal_usb_cdc_read(uint8_t *buf, size_t cap)
{
    if (enter(FAKE_FN_hal_usb_cdc_read, (uint32_t)cap, 0u) != HAL_OK || !F.usb_on || buf == NULL)
        return 0u;
    size_t avail = F.usb_rx_n - F.usb_rx_i, n = cap < avail ? cap : avail;
    memcpy(buf, &F.usb_rx[F.usb_rx_i], n);
    F.usb_rx_i += n;
    return n;
}
void hal_usb_dfu_request(void)
{
    (void)enter(FAKE_FN_hal_usb_dfu_request, 0u, 0u);
    F.dfu_requests++;
}
void fake_vbus(bool present)
{
    int dbq = F.bq_attached ? i2c_dev(0x6Au) : -1;
    if (dbq >= 0 && present != (F.vbus != 0u))
        F.i2c_reg[dbq][0x0A] &= (uint8_t)~0x0Cu;    /* SLUSE99C 8.3.4: toggling VIN resets SYS_MODE to 00 */
    F.vbus = present;
    if (!present)
        F.usb_on = false;
}
void fake_usb_rx(const uint8_t *buf, size_t len)
{
    memmove(F.usb_rx, &F.usb_rx[F.usb_rx_i], F.usb_rx_n - F.usb_rx_i);   /* drop what the firmware already read */
    F.usb_rx_n -= F.usb_rx_i;
    F.usb_rx_i = 0u;
    size_t room = sizeof F.usb_rx - F.usb_rx_n, n = len < room ? len : room;
    memcpy(&F.usb_rx[F.usb_rx_n], buf, n);
    F.usb_rx_n += n;
}
size_t fake_usb_tx(uint8_t *buf, size_t cap)
{
    size_t n = cap < F.usb_tx_n ? cap : F.usb_tx_n;
    memcpy(buf, F.usb_tx, n);
    memmove(F.usb_tx, &F.usb_tx[n], F.usb_tx_n - n);   /* the host read them */
    F.usb_tx_n -= n;
    return n;
}

/* ------------------------------------------------------------------------------------------- flash */
static uint32_t xs = 0x9E3779B9u;
static uint8_t garbage(void)
{
    xs ^= xs << 13;
    xs ^= xs >> 17;
    xs ^= xs << 5;
    return (uint8_t)xs;
}

/* power-fail bookkeeping: returns 1 if this op is torn (caller tears it), 2 if power is already gone */
static int flash_power(void)
{
    if (F.flash_dead)
        return 2;
    uint32_t op = F.flash_ops++;
    if (op == F.flash_fail_at) {
        F.flash_dead = 1u;
        return 1;
    }
    return 0;
}

hal_status_t hal_flash_erase_page(uint32_t page)
{
    hal_status_t e = enter(FAKE_FN_hal_flash_erase_page, page, 0u);
    if (e != HAL_OK)
        return e;
    if (page >= HAL_FLASH_KNOB_PAGES)
        return HAL_EINVAL;
    uint8_t *p = &F.flash[page * HAL_FLASH_PAGE_BYTES];
    int pw = flash_power();
    if (pw == 2)
        return HAL_ERR;
    if (pw == 1) {                       /* torn erase: part erased, part garbage */
        for (uint32_t i = 0; i < HAL_FLASH_PAGE_BYTES; i++)
            p[i] = (i < HAL_FLASH_PAGE_BYTES / 2u) ? 0xFFu : garbage();
        return HAL_ERR;
    }
    memset(p, 0xFF, HAL_FLASH_PAGE_BYTES);
    return HAL_OK;
}

hal_status_t hal_flash_program_qw(uint32_t offset, const uint8_t qw[HAL_FLASH_QW_BYTES])
{
    hal_status_t e = enter(FAKE_FN_hal_flash_program_qw, offset, 0u);
    if (e != HAL_OK)
        return e;
    if (qw == NULL || offset % HAL_FLASH_QW_BYTES != 0u || offset + HAL_FLASH_QW_BYTES > FLASH_BYTES)
        return HAL_EINVAL;
    uint8_t *p = &F.flash[offset];
    for (uint32_t i = 0; i < HAL_FLASH_QW_BYTES; i++)
        if (p[i] != 0xFFu)
            return HAL_ERR;              /* RM0456: a quad word programs once after erase (PROGERR) */
    int pw = flash_power();
    if (pw == 2)
        return HAL_ERR;
    if (pw == 1) {
        for (uint32_t i = 0; i < HAL_FLASH_QW_BYTES; i++)
            p[i] = garbage();
        return HAL_ERR;
    }
    memcpy(p, qw, HAL_FLASH_QW_BYTES);
    return HAL_OK;
}

hal_status_t hal_flash_read(uint32_t offset, uint8_t *buf, size_t len)
{
    hal_status_t e = enter(FAKE_FN_hal_flash_read, offset, (uint32_t)len);
    if (e != HAL_OK)
        return e;
    if (buf == NULL || (size_t)offset + len > FLASH_BYTES)
        return HAL_EINVAL;
    if (F.flash_ecc != 0xFFFFFFFFu) {
        uint32_t q = F.flash_ecc / HAL_FLASH_QW_BYTES * HAL_FLASH_QW_BYTES;
        if (q < offset + len && offset < q + HAL_FLASH_QW_BYTES)
            return HAL_ECC;
    }
    memcpy(buf, &F.flash[offset], len);
    return HAL_OK;
}
uint8_t *fake_flash_raw(void) { return F.flash; }
void fake_flash_power_fail_after(uint32_t ops) { F.flash_fail_at = F.flash_ops + ops; F.flash_dead = 0u; }
void fake_flash_power_restore(void) { F.flash_dead = 0u; F.flash_fail_at = 0xFFFFFFFFu; }
void fake_flash_ecc_at(uint32_t offset) { F.flash_ecc = offset; }
uint32_t fake_flash_ops(void) { return F.flash_ops; }

/* ------------------------------------------------------------------------------------------- wdt, time, irq */
hal_status_t hal_wdt_start(uint32_t timeout_ms)
{
    hal_status_t e = enter(FAKE_FN_hal_wdt_start, timeout_ms, 0u);
    if (e != HAL_OK)
        return e;
    F.wdt_started = 1u;
    F.wdt_ms = timeout_ms;
    return HAL_OK;
}
void hal_wdt_kick(void)
{
    if (enter(FAKE_FN_hal_wdt_kick, 0u, 0u) == HAL_OK)
        F.wdt_kicks++;
}
uint32_t fake_wdt_kicks(void) { return F.wdt_kicks; }
uint32_t fake_resets(void) { return F.resets; }

uint64_t hal_time_us(void)
{
    (void)enter(FAKE_FN_hal_time_us, 0u, 0u);
    return F.t_us;
}
uint32_t hal_time_cycles(void)
{
    (void)enter(FAKE_FN_hal_time_cycles, 0u, 0u);
    return (uint32_t)(F.t_us * (plan_hz[F.plan] / 1000000u));
}
uint32_t hal_irq_save(void)
{
    (void)enter(FAKE_FN_hal_irq_save, F.irq_state, 0u);
    uint32_t s = F.irq_state;
    F.irq_state = 1u;
    return s;
}
void hal_irq_restore(uint32_t state)
{
    (void)enter(FAKE_FN_hal_irq_restore, state, 0u);
    F.irq_state = state;
}

hal_status_t hal_fmac_fir_bank(const int16_t *coef, uint32_t n_phase, uint32_t taps, uint32_t r_gain, const int16_t *x, uint32_t n_new, int16_t *y)
{
    hal_status_t e = enter(FAKE_FN_hal_fmac_fir_bank, n_phase * taps, n_new);
    if (e != HAL_OK)
        return e;
    if (coef == NULL || x == NULL || y == NULL || taps == 0u || taps > 127u || r_gain > 7u)
        return HAL_EINVAL;
    fw_fmac_model_bank(coef, n_phase, taps, r_gain, x, n_new, y);   /* bit-accurate FMAC model (fw/core/fmac_model.c) */
    return HAL_OK;
}

/* ------------------------------------------------------------------------------------------- break (FWSIM-R65) */
hal_status_t hal_brk_arm(uint32_t threshold_ma)
{
    hal_status_t e = enter(FAKE_FN_hal_brk_arm, threshold_ma, 0u);
    if (e != HAL_OK)
        return e;
    F.brk.armed = 1u;
    F.brk.threshold_ma = threshold_ma;
    F.brk.arms++;
    return HAL_OK;
}
void hal_brk_disarm(void)
{
    (void)enter(FAKE_FN_hal_brk_disarm, 0u, 0u);
    F.brk.armed = 0u;
    F.brk.disarms++;
}
bool hal_brk_latched(void)
{
    if (enter(FAKE_FN_hal_brk_latched, 0u, 0u) != HAL_OK)
        return true;                              /* an unreadable break status reads as tripped (fail safe) */
    return F.brk.latched != 0u;
}
void hal_brk_clear(void)
{
    (void)enter(FAKE_FN_hal_brk_clear, 0u, 0u);
    F.brk.latched = 0u;
    F.brk.clears++;
}
void fake_isense_ma(int32_t ma)
{
    uint32_t a = (uint32_t)(ma < 0 ? -ma : ma);
    if (F.brk.armed && a > F.brk.threshold_ma) {
        F.brk.latched = 1u;
        F.brk.trips++;
        F.pwm.running = 0u;                       /* hardware: MOE cleared, outputs to the safe idle state */
    }
}
const fake_brk_state_t *fake_brk(void) { return &F.brk; }
void fake_pa1_stuck(uint32_t mode) { F.pa1_stuck = mode; }
