/* fw/port_u575/boot/boot.h: boot stub decision (FWSIM-R21). The stub (stub.c, flash page 0, 8 KB, write-protected) decides once per reset:
 * ROM DFU or the application. Pure logic here so the host tests run the same code the stub runs. */
#ifndef FW_BOOT_H
#define FW_BOOT_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define BOOT_APP_BASE 0x08002000u          /* u575.ld FLASH origin */
#define BOOT_APP_MAX (2048u * 1024u - 8u * 1024u - 16u * 1024u)
#define BOOT_HDR_OFFSET 0x300u             /* header right after the 141-word vector table (u575.ld places .app_header here) */
#define BOOT_HDR_MAGIC 0x41444F50u         /* "PODA" */
#define BOOT_DFU_MAGIC 0xDF00B007u         /* TAMP_BKP0R flag from hal_usb_dfu_request */
#define BOOT_SRAM_LO 0x20000000u
#define BOOT_SRAM_HI 0x200C0000u           /* SRAM1 + SRAM2 + SRAM3 end (RM0456 Rev 7 memory map) */

typedef struct {
    uint32_t magic, version, length, crc32;   /* length: bytes from BOOT_APP_BASE; crc32 over them with this crc32 field read as 0 */
} boot_hdr_t;

typedef enum { BOOT_APP = 0, BOOT_DFU_FLAG, BOOT_DFU_BUTTON, BOOT_DFU_NO_APP, BOOT_DFU_CRC, BOOT_DFU_VECTORS } boot_action_t;

/* img = the application image as mapped at BOOT_APP_BASE (img_avail bytes readable) */
boot_action_t boot_decide(uint32_t bkp_flag, bool btn_held, bool vbus, const uint8_t *img, size_t img_avail);
uint32_t boot_image_crc(const uint8_t *img, uint32_t length);   /* CRC-32 (zlib) with the header crc word as 0 */
#endif
