/* fw/port_u575/boot/boot.c: boot stub decision, see boot.h. Order: DFU flag (the app asked) -> button held at reset with VBUS present
 * (sub-dock-usb.md DK-04 A: the owner's way into DFU when the app is alive but wrong) -> image header -> image CRC -> vectors -> app. */
#include "boot.h"

#include <string.h>

#include "crc32.h"

uint32_t boot_image_crc(const uint8_t *img, uint32_t length)
{
    static const uint8_t zero[4] = {0u, 0u, 0u, 0u};
    uint32_t at = BOOT_HDR_OFFSET + 12u, c = fw_crc32_update(0u, img, at);
    c = fw_crc32_update(c, zero, 4u);
    return fw_crc32_update(c, img + at + 4u, length - at - 4u);
}

boot_action_t boot_decide(uint32_t bkp_flag, bool btn_held, bool vbus, const uint8_t *img, size_t img_avail)
{
    if (bkp_flag == BOOT_DFU_MAGIC)
        return BOOT_DFU_FLAG;
    if (btn_held && vbus)
        return BOOT_DFU_BUTTON;
    if (img == NULL || img_avail < BOOT_HDR_OFFSET + sizeof(boot_hdr_t))
        return BOOT_DFU_NO_APP;
    boot_hdr_t h;
    memcpy(&h, img + BOOT_HDR_OFFSET, sizeof h);
    if (h.magic != BOOT_HDR_MAGIC || h.version != 1u || h.length < BOOT_HDR_OFFSET + sizeof h || h.length > BOOT_APP_MAX ||
        h.length > img_avail)
        return BOOT_DFU_NO_APP;                 /* erased flash (0xFF...) lands here */
    if (boot_image_crc(img, h.length) != h.crc32)
        return BOOT_DFU_CRC;
    uint32_t sp, pc;
    memcpy(&sp, img, 4u);
    memcpy(&pc, img + 4u, 4u);
    if (sp < BOOT_SRAM_LO || sp > BOOT_SRAM_HI || (sp & 7u) || !(pc & 1u) || pc < BOOT_APP_BASE || pc >= BOOT_APP_BASE + h.length)
        return BOOT_DFU_VECTORS;
    return BOOT_APP;
}
