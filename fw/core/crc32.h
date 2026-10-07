/* fw/core/crc32.h: CRC-32 (IEEE, reflected poly 0xEDB88320, init/xorout 0xFFFFFFFF): knob store, state hash, FWSIM-R57 frames. */
#ifndef FW_CORE_CRC32_H
#define FW_CORE_CRC32_H
#include <stddef.h>
#include <stdint.h>

uint32_t fw_crc32_update(uint32_t crc, const void *data, size_t len);   /* start with crc = 0 */
#endif
