/* fw/hal/hal_usb.h: OTG_FS device: VBUS, CDC, DFU handoff (FWSIM-R21, R28). */
#ifndef FW_HAL_USB_H
#define FW_HAL_USB_H
#include "hal_types.h"

bool hal_usb_vbus(void);                              /* PA1 VBUS_SENSE debounced by the port */
hal_status_t hal_usb_enable(bool on);                 /* core clock + PA11/PA12; off = analog, pull-up off */
/* bus state seen by the device stack: NONE = no host (dumb supply, not yet enumerated; a suspend before the first bus reset is not a
 * suspend), CONFIGURED = a host set a configuration (500 mA allowed), SUSPENDED = a connected host suspended the bus (2.5 mA allowed) */
typedef enum { HAL_USB_BUS_NONE = 0, HAL_USB_BUS_CONFIGURED = 1, HAL_USB_BUS_SUSPENDED = 2 } hal_usb_bus_t;
hal_usb_bus_t hal_usb_bus(void);
size_t hal_usb_cdc_write(const uint8_t *buf, size_t len);   /* bytes queued (0 when not enumerated) */
size_t hal_usb_cdc_read(uint8_t *buf, size_t cap);          /* bytes received */
void hal_usb_dfu_request(void);                       /* backup-register flag + reset into the boot stub */
#endif
