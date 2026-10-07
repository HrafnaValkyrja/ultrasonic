/* fw/port_host/fake.h: control API of the stateful host fakes behind every fw/hal function (FWSIM-R2).
 * Fakes, not mocks: they keep device state (pins, flash array with program-once quad words, I2C register files, PWM sequence,
 * simulated time), take scripted inputs, log every call, and inject faults per function. Not thread-safe (single test thread). */
#ifndef FW_PORT_HOST_FAKE_H
#define FW_PORT_HOST_FAKE_H
#include "hal.h"
#include "ring.h"

/* every HAL function, once: the coverage test and fw/tools/lint.py both check this list against fw/hal/hal_*.h */
#define FAKE_HAL_FUNCS(X) \
    X(hal_clock_set_plan) X(hal_clock_hclk_hz) \
    X(hal_power_stop2) X(hal_power_reset_cause) X(hal_power_system_reset) X(hal_power_ucpd_dbdis) \
    X(hal_gpio_mode) X(hal_gpio_write) X(hal_gpio_read) \
    X(hal_adf_start) X(hal_adf_stop) X(hal_adf_hop_take) X(hal_adf_hop_release) X(hal_adf_flags) \
    X(hal_pwm_config) X(hal_pwm_start) X(hal_pwm_stop) X(hal_pwm_submit) X(hal_pwm_underruns) \
    X(hal_adc_read_mv) \
    X(hal_i2c_write) X(hal_i2c_read) X(hal_i2c_recover) \
    X(hal_usb_vbus) X(hal_usb_enable) X(hal_usb_configured) X(hal_usb_cdc_write) X(hal_usb_cdc_read) X(hal_usb_dfu_request) \
    X(hal_flash_erase_page) X(hal_flash_program_qw) X(hal_flash_read) \
    X(hal_wdt_start) X(hal_wdt_kick) \
    X(hal_time_us) X(hal_time_cycles) \
    X(hal_irq_save) X(hal_irq_restore) \
    X(hal_fmac_fir_bank) \
    X(hal_brk_arm) X(hal_brk_disarm) X(hal_brk_latched) X(hal_brk_clear) \
    X(hal_power_rtc_wakeup_s) X(hal_clock_stop_prep) X(hal_led_set)

#define FAKE_FN_ID(f) FAKE_FN_##f,
typedef enum { FAKE_HAL_FUNCS(FAKE_FN_ID) FAKE_FN_COUNT } fake_fn_t;
#undef FAKE_FN_ID
extern const char *const fake_fn_name[FAKE_FN_COUNT];

/* ---- lifecycle */
void fake_reset(void);                         /* every fake back to power-on state, log cleared, faults cleared */

/* ---- call log */
typedef struct { uint16_t fn; uint16_t pad; uint32_t a0; uint32_t a1; uint64_t t_us; } fake_call_t;
uint32_t fake_dfu_requests(void);
#define FAKE_LOG_CAP 4096u
uint32_t fake_log_len(void);                   /* entries kept (<= FAKE_LOG_CAP; older ones roll off) */
const fake_call_t *fake_log_at(uint32_t i);
uint32_t fake_calls(fake_fn_t fn);             /* total calls since reset (not limited by the log cap) */
int32_t fake_log_find(fake_fn_t fn, uint32_t from);   /* index of the next entry for fn at or after `from`, -1 if none */

/* ---- fault injection: the call number `nth` (0-based, counted from now) of fn and the `count - 1` after it return `err`
 * (a NULL/0/false result for non-status functions). count 0xFFFFFFFF = forever. */
void fake_fault(fake_fn_t fn, uint32_t nth, uint32_t count, hal_status_t err);
void fake_fault_clear(void);

/* ---- simulated time */
void fake_time_set_us(uint64_t t);
void fake_time_advance_us(uint64_t dt);

/* ---- scripted inputs */
void fake_gpio_input(board_pin_t pin, bool level);
bool fake_gpio_output(board_pin_t pin);                 /* last level written */
hal_gpio_mode_t fake_gpio_mode_of(board_pin_t pin);
void fake_adc_script(hal_adc_ch_t ch, const uint16_t *mv, uint32_t n);   /* returned in order; last value repeats */
void fake_reset_cause(hal_reset_cause_t c);
void fake_wake_source(hal_wake_t w);
void fake_vbus(bool present);
void fake_usb_configured(bool cfg);                      /* the host configured (true) / suspended or reset (false) the device */
void fake_usb_rx(const uint8_t *buf, size_t len);       /* bytes the host sends; read by hal_usb_cdc_read */
size_t fake_usb_tx(uint8_t *buf, size_t cap);           /* bytes the firmware wrote */

/* ADF: scripted hops go through the fake DMA ISR, which moves one into a DMA buffer and pushes it on the ring (FWSIM-R3) */
void fake_adf_script_hop(const int32_t hop[128]);       /* queue (up to 16) */
void fake_adf_isr(void);                                /* "DMA half/complete": move one scripted hop, set the flag */
void fake_adf_set_flags(uint32_t flags);
fw_ring_t *fake_adf_ring(void);

/* I2C: register-file devices (256 x 8 bit) per 7-bit address; absent address -> HAL_NACK */
void fake_i2c_attach(uint8_t addr7);
/* BQ25180 behaviour (SLUSE99C Rev C, registers 0x00-0x0C, reset values Table 8-9..8-21): watchdog per IC_CTRL WATCHDOG_SEL starts at the
 * first transaction, any transaction restarts it; 00 = registers back to reset values after 160 s, 01 = HW reset after 160 s, 10 = after
 * 40 s, 11 = off; REG_RST; STAT0 VIN_PGOOD follows fake_vbus. Evaluated at each access to 0x6A (lazily, with simulated time). */
typedef struct { uint32_t wd_reverts, hw_resets, sw_resets, txns; } fake_bq_state_t;
void fake_bq25180_attach(void);
const fake_bq_state_t *fake_bq(void);
/* FWSIM-R65 break model: supply current seen by the MDF1 detector; above the armed threshold -> latched, PWM MOE cleared */
void fake_isense_ma(int32_t ma);
void fake_pa1_stuck(uint32_t mode);
/* low power (FWSIM-R23): Stop 2 entries and the pin/clock audit at each entry; with no scripted wake source the RTC wakes the core after its
 * period (simulated time advances by it) */
typedef struct { uint32_t stop2_entries, audit_violations, rtc_s, clocks_prepped, led_duty_ppm; } fake_lp_state_t;
const fake_lp_state_t *fake_lp(void);   /* 0 = follows fake_vbus, 1 = PA1 reads low, 2 = PA1 reads high (FWSIM-R19 faults) */
typedef struct { uint32_t armed, threshold_ma, latched, trips, arms, disarms, clears; } fake_brk_state_t;
const fake_brk_state_t *fake_brk(void);
uint8_t *fake_i2c_regs(uint8_t addr7);                  /* NULL if not attached */

/* PWM: the CCR streams submitted, in order */
typedef struct { uint16_t arr; uint8_t rcr, dtg_rise, dtg_fall; uint8_t configured, running; } fake_pwm_state_t;
const fake_pwm_state_t *fake_pwm(void);
uint32_t fake_pwm_hops(void);
const uint16_t *fake_pwm_last(size_t *n);
void fake_pwm_underrun(void);                           /* the port repeated the centre CCR (no hop in time) */

/* flash: knob region of HAL_FLASH_KNOB_PAGES pages; program-once quad words; power fail; ECC */
uint8_t *fake_flash_raw(void);                          /* direct view (tests corrupt bytes with it) */
void fake_flash_power_fail_after(uint32_t ops);         /* the op number `ops` (0-based, erase or program) is torn, then all ops fail */
void fake_flash_power_restore(void);
void fake_flash_ecc_at(uint32_t offset);                /* reads covering this quad word return HAL_ECC (0xFFFFFFFF = none) */
uint32_t fake_flash_ops(void);

/* WDT / reset */
uint32_t fake_wdt_kicks(void);
uint32_t fake_resets(void);
#endif
