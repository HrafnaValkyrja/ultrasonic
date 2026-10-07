/* fw/port_u575/usb/usb_desc.h: USB descriptors of the pod (FWSIM-R28): one CDC-ACM function behind an IAD. Plain bytes, no TinyUSB
 * types, so the host test (fw/test/port/test_usb_desc.c) parses exactly what the target sends. */
#ifndef FW_USB_DESC_H
#define FW_USB_DESC_H
#include <stddef.h>
#include <stdint.h>

#define USB_VID 0x1209u           /* pid.codes open-source VID */
#define USB_PID 0x0001u           /* pid.codes TEST PID: fine for a personal device, not for distribution [O: own PID from pid.codes] */
#define USB_EP_NOTIF 0x81u
#define USB_EP_OUT 0x02u
#define USB_EP_IN 0x82u
#define USB_DESC_CONFIG_LEN 75u
#define USB_MAX_POWER_MA 500u     /* the charger plan raises ILIM to 500 mA after enumeration (FWSIM-R20) */

extern const uint8_t usb_desc_device[18];
extern const uint8_t usb_desc_config[USB_DESC_CONFIG_LEN];
/* string descriptor index (0 = language list) as a USB string descriptor (bLength, 0x03, UTF-16LE) in out[]; returns words written,
 * 0 for an unknown index. uid: the 3 x 32-bit device UID (serial number = 24 hex digits). */
size_t usb_desc_string(uint8_t index, const uint32_t uid[3], uint16_t *out, size_t cap_words);
#endif
