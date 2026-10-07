/* fw/port_u575/usb/hal_u575_usb.c: CDC-ACM on TinyUSB 0.18.0 (fw/vendor/tinyusb, MIT) over the OTG_FS DWC2 core (FWSIM-R28).
 * hal_usb_enable (hal_u575_sys.c) powers clocks, VDDUSB and pins, then calls u575_usb_core_start / _stop here. The device stack runs
 * from hal_usb_cdc_read / hal_usb_cdc_write (tud_task: the main loop polls both every pass), the OTG_FS interrupt only latches events
 * (tud_int_handler), so no USB work runs in interrupt context beyond TinyUSB's own ISR bookkeeping. */
#include "hal.h"
#include "tusb.h"
#include "usb_desc.h"

#define UID_BASE 0x0BFA0700u                   /* RM0456 Rev 7 s75.1: 96-bit unique device ID */

uint32_t SystemCoreClock = 4000000u;           /* TinyUSB's dwc2_stm32.h reads it for the turnaround time (USBTRD) */
static uint32_t core_up;

void OTG_FS_IRQHandler(void) { tud_int_handler(0); }

void u575_usb_core_start(void)
{
    SystemCoreClock = hal_clock_hclk_hz();
    if (!core_up) {
        tusb_rhport_init_t init = {.role = TUSB_ROLE_DEVICE, .speed = TUSB_SPEED_FULL};
        (void)tusb_init(0, &init);             /* core reset, FS PHY on (PWRDWN), device mode, soft connect */
        core_up = 1u;
    } else {
        tud_connect();
    }
}

void u575_usb_core_stop(void)
{
    if (core_up) {
        tud_disconnect();                       /* SDIS = 1 before the PHY and clock go away */
        (void)tud_deinit(0);
        core_up = 0u;
    }
}

size_t hal_usb_cdc_write(const uint8_t *buf, size_t len)
{
    if (!core_up || buf == NULL)
        return 0u;
    tud_task();
    if (!tud_cdc_connected())
        return 0u;                              /* host gone or port closed: drop, never block (no TX deadlock) */
    uint32_t n = tud_cdc_write(buf, (uint32_t)len);
    (void)tud_cdc_write_flush();
    return n;
}

size_t hal_usb_cdc_read(uint8_t *buf, size_t cap)
{
    if (!core_up || buf == NULL)
        return 0u;
    tud_task();
    return tud_cdc_available() ? tud_cdc_read(buf, (uint32_t)cap) : 0u;
}

/* ---- TinyUSB descriptor callbacks */
uint8_t const *tud_descriptor_device_cb(void) { return usb_desc_device; }

uint8_t const *tud_descriptor_configuration_cb(uint8_t index)
{
    (void)index;
    return usb_desc_config;
}

uint16_t const *tud_descriptor_string_cb(uint8_t index, uint16_t langid)
{
    static uint16_t s[32];
    (void)langid;
    const uint32_t uid[3] = {*(const volatile uint32_t *)UID_BASE, *(const volatile uint32_t *)(UID_BASE + 4u),
                             *(const volatile uint32_t *)(UID_BASE + 8u)};
    return usb_desc_string(index, uid, s, 32u) ? s : NULL;
}

hal_usb_bus_t hal_usb_bus(void)
{
    if (!core_up)
        return HAL_USB_BUS_NONE;
    tud_task();
    if (tud_suspended())                        /* TinyUSB counts a suspend only after a bus reset: a dumb supply never "suspends" */
        return HAL_USB_BUS_SUSPENDED;
    return tud_mounted() ? HAL_USB_BUS_CONFIGURED : HAL_USB_BUS_NONE;
}
