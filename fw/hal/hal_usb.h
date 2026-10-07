/* fw/hal/hal_usb.h: OTG_FS device: VBUS, CDC, DFU handoff (FWSIM-R21, R28). */
#ifndef FW_HAL_USB_H
#define FW_HAL_USB_H
#include "hal_types.h"

bool hal_usb_vbus(void);                              /* PA1 VBUS_SENSE debounced by the port */
hal_status_t hal_usb_enable(bool on);                 /* core clock + PA11/PA12; off = analog, pull-up off */
bool hal_usb_configured(void);                        /* host set a configuration and the bus is not suspended (charger ILIM, R20) */
size_t hal_usb_cdc_write(const uint8_t *buf, size_t len);   /* bytes queued (0 when not enumerated) */
size_t hal_usb_cdc_read(uint8_t *buf, size_t cap);          /* bytes received */
void hal_usb_dfu_request(void);                       /* backup-register flag + reset into the boot stub */
#endif
