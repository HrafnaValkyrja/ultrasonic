/* fw/port_u575/usb/usb_desc.c: descriptor bytes (USB 2.0 ch. 9; CDC 1.2 / PSTN 1.2 functional descriptors; IAD ECN). */
#include "usb_desc.h"

const uint8_t usb_desc_device[18] = {
    18u, 0x01u, 0x00u, 0x02u,          /* bLength, DEVICE, bcdUSB 2.00 */
    0xEFu, 0x02u, 0x01u, 64u,          /* Misc / Common / IAD (composite with an IAD), EP0 64 bytes */
    (uint8_t)USB_VID, (uint8_t)(USB_VID >> 8), (uint8_t)USB_PID, (uint8_t)(USB_PID >> 8),
    0x00u, 0x01u, 1u, 2u, 3u, 1u,      /* bcdDevice 1.00, iManufacturer, iProduct, iSerialNumber, 1 configuration */
};

const uint8_t usb_desc_config[USB_DESC_CONFIG_LEN] = {
    9u, 0x02u, (uint8_t)USB_DESC_CONFIG_LEN, 0u, 2u, 1u, 0u, 0x80u, (uint8_t)(USB_MAX_POWER_MA / 2u),   /* CONFIGURATION, 2 interfaces, bus powered */
    8u, 0x0Bu, 0u, 2u, 0x02u, 0x02u, 0x01u, 0u,                    /* IAD: interfaces 0-1, CDC / ACM / AT */
    9u, 0x04u, 0u, 0u, 1u, 0x02u, 0x02u, 0x01u, 0u,                /* INTERFACE 0: communication class, 1 endpoint */
    5u, 0x24u, 0x00u, 0x20u, 0x01u,                                /* CDC header, bcdCDC 1.20 */
    5u, 0x24u, 0x01u, 0x00u, 1u,                                   /* call management: none, data interface 1 */
    4u, 0x24u, 0x02u, 0x02u,                                       /* ACM: line coding + control line state */
    5u, 0x24u, 0x06u, 0u, 1u,                                      /* union: master 0, slave 1 */
    7u, 0x05u, USB_EP_NOTIF, 0x03u, 8u, 0u, 16u,                   /* notification IN, interrupt, 8 bytes, 16 ms */
    9u, 0x04u, 1u, 0u, 2u, 0x0Au, 0x00u, 0x00u, 0u,                /* INTERFACE 1: CDC data, 2 endpoints */
    7u, 0x05u, USB_EP_OUT, 0x02u, 64u, 0u, 0u,                     /* bulk OUT 64 */
    7u, 0x05u, USB_EP_IN, 0x02u, 64u, 0u, 0u,                      /* bulk IN 64 */
};

static const char *const strings[3] = {"Stereo Ultrasound", "Ultrasound pod", NULL};

size_t usb_desc_string(uint8_t index, const uint32_t uid[3], uint16_t *out, size_t cap_words)
{
    size_t n = 0u;
    if (cap_words < 2u)
        return 0u;
    if (index == 0u) {
        out[1] = 0x0409u;                                          /* English (US) */
        n = 1u;
    } else if (index == 3u) {
        static const char hex[] = "0123456789ABCDEF";
        for (uint32_t w = 0; w < 3u && n + 8u < cap_words; w++)
            for (int32_t s = 28; s >= 0; s -= 4)
                out[1u + n++] = (uint16_t)hex[(uid[w] >> s) & 0xFu];
    } else if (index <= 2u) {
        for (const char *p = strings[index - 1u]; *p && n + 1u < cap_words; p++)
            out[1u + n++] = (uint16_t)(uint8_t)*p;
    } else {
        return 0u;
    }
    out[0] = (uint16_t)((0x03u << 8) | (2u * n + 2u));
    return n + 1u;
}
