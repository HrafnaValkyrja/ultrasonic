/* fw/hal/hal_flash.h: knob-store region (RM0456 Rev 7: 8 KB pages, 128-bit quad-word program + ECC; FWSIM-R6, R30).
 * Offsets are relative to the knob region (HAL_FLASH_KNOB_PAGES pages). A quad word can be programmed once after erase. */
#ifndef FW_HAL_FLASH_H
#define FW_HAL_FLASH_H
#include "hal_types.h"

#define HAL_FLASH_PAGE_BYTES 8192u
#define HAL_FLASH_QW_BYTES 16u
#define HAL_FLASH_KNOB_PAGES 2u

hal_status_t hal_flash_erase_page(uint32_t page);                      /* page index within the knob region */
hal_status_t hal_flash_program_qw(uint32_t offset, const uint8_t qw[HAL_FLASH_QW_BYTES]);   /* offset 16-aligned */
hal_status_t hal_flash_read(uint32_t offset, uint8_t *buf, size_t len);  /* HAL_ECC on an uncorrectable word */
#endif
