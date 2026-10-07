/* fw/port_u575/hal_u575.c: target HAL. FOUNDATION: only the time base, IRQ masking and flash read are real; every other
 * function returns HAL_ENOTIMPL (or its safe value) until its register code is written (ST LL + direct ADF1 code,
 * FWSIM architecture.layers.port_u575). This is the only file family allowed to touch registers. */
#include <string.h>

#include "hal.h"
#include "fmac_model.h"

#define DEMCR      (*(volatile uint32_t *)0xE000EDFCu)
#define DWT_CTRL   (*(volatile uint32_t *)0xE0001000u)
#define DWT_CYCCNT (*(volatile uint32_t *)0xE0001004u)
#define KNOB_BASE  0x081FC000u   /* fw/port_u575/u575.ld KNOBS */

static uint32_t hclk_hz = 4000000u;   /* MSIS 4 MHz after reset (RM0456 Rev 7 RCC) until hal_clock_set_plan runs */
static uint32_t last_cyc;
static uint64_t cyc_total;

hal_status_t hal_clock_set_plan(hal_clock_plan_t plan) { (void)plan; return HAL_ENOTIMPL; }
uint32_t hal_clock_hclk_hz(void) { return hclk_hz; }

hal_wake_t hal_power_stop2(void) { return HAL_WAKE_NONE; }
hal_reset_cause_t hal_power_reset_cause(void) { return HAL_RESET_OTHER; }
void hal_power_system_reset(void)
{
    *(volatile uint32_t *)0xE000ED0Cu = (0x5FAu << 16) | (1u << 2);   /* SCB_AIRCR: VECTKEY | SYSRESETREQ */
    for (;;) {
    }
}
void hal_power_ucpd_dbdis(void) {}


hal_status_t hal_adf_start(uint32_t cck_hz) { (void)cck_hz; return HAL_ENOTIMPL; }
void hal_adf_stop(void) {}
const int32_t *hal_adf_hop_take(void) { return NULL; }
void hal_adf_hop_release(void) {}
uint32_t hal_adf_flags(void) { return 0u; }




bool hal_usb_vbus(void) { return false; }
hal_status_t hal_usb_enable(bool on) { (void)on; return HAL_ENOTIMPL; }
size_t hal_usb_cdc_write(const uint8_t *buf, size_t len) { (void)buf; (void)len; return 0u; }
size_t hal_usb_cdc_read(uint8_t *buf, size_t cap) { (void)buf; (void)cap; return 0u; }
void hal_usb_dfu_request(void) {}

hal_status_t hal_flash_erase_page(uint32_t page) { (void)page; return HAL_ENOTIMPL; }
hal_status_t hal_flash_program_qw(uint32_t offset, const uint8_t qw[HAL_FLASH_QW_BYTES]) { (void)offset; (void)qw; return HAL_ENOTIMPL; }
hal_status_t hal_flash_read(uint32_t offset, uint8_t *buf, size_t len)
{
    if ((size_t)offset + len > (size_t)HAL_FLASH_KNOB_PAGES * HAL_FLASH_PAGE_BYTES)
        return HAL_EINVAL;
    memcpy(buf, (const void *)(uintptr_t)(KNOB_BASE + offset), len);   /* ECC double errors -> NMI: handler later */
    return HAL_OK;
}

hal_status_t hal_wdt_start(uint32_t timeout_ms) { (void)timeout_ms; return HAL_ENOTIMPL; }
void hal_wdt_kick(void) {}

uint32_t hal_time_cycles(void)
{
    if (!(DWT_CTRL & 1u)) {
        DEMCR |= 1u << 24;          /* TRCENA */
        DWT_CYCCNT = 0u;
        DWT_CTRL |= 1u;             /* CYCCNTENA */
    }
    return DWT_CYCCNT;
}
uint64_t hal_time_us(void)
{
    uint32_t c = hal_time_cycles();   /* foundation: CYCCNT extended to 64 bit; must be called at least once per 2^32 cycles */
    cyc_total += (uint32_t)(c - last_cyc);
    last_cyc = c;
    return cyc_total / (hclk_hz / 1000000u);
}

uint32_t hal_irq_save(void)
{
    uint32_t primask;
    __asm volatile("mrs %0, primask\n cpsid i" : "=r"(primask)::"memory");
    return primask;
}
void hal_irq_restore(uint32_t state)
{
    __asm volatile("msr primask, %0" ::"r"(state) : "memory");
}

/* FMAC (RM0456 s26): register driver (polling or GPDMA, docs/research/drastic/V5-fmac-cordic.yaml dma_timing_plan) lands with bring-up
 * (E4). Until then the target runs the bit-accurate model in software, so the ELF behaves exactly like host and QEMU (FWSIM-R7 L0). */
hal_status_t hal_fmac_fir_bank(const int16_t *coef, uint32_t n_phase, uint32_t taps, uint32_t r_gain, const int16_t *x, uint32_t n_new, int16_t *y)
{
    if (coef == NULL || x == NULL || y == NULL || taps == 0u || taps > 127u || r_gain > 7u)
        return HAL_EINVAL;
    fw_fmac_model_bank(coef, n_phase, taps, r_gain, x, n_new, y);
    return HAL_OK;
}

hal_status_t hal_power_rtc_wakeup_s(uint32_t seconds) { (void)seconds; return HAL_ENOTIMPL; }
hal_status_t hal_clock_stop_prep(void) { return HAL_ENOTIMPL; }
hal_status_t hal_led_set(uint32_t duty_ppm) { (void)duty_ppm; return HAL_ENOTIMPL; }
