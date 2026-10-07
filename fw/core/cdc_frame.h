/* fw/core/cdc_frame.h: CDC byte-stream reassembly for the fw_cdc_rx frames (0xA5, type, len, payload). USB delivers the stream in
 * packets of any size: a frame may arrive split across packets or several frames in one packet. Pure, no HAL (FWSIM-R3, R28):
 * resync on a bad start byte or an over-long length (byte dropped, counted), a partial frame older than FW_CDC_GAP_US is discarded. */
#ifndef FW_CORE_CDC_FRAME_H
#define FW_CORE_CDC_FRAME_H
#include <stddef.h>
#include <stdint.h>

#define FW_CDC_SOF 0xA5u
#define FW_CDC_MAX_PAYLOAD 16u          /* longest command payload is 4 bytes; headroom for the FWSIM-R57 codec */
#define FW_CDC_GAP_US 50000u            /* inter-byte timeout: a host that stalls mid-frame cannot leave a half frame armed */

typedef struct {
    uint8_t buf[3u + FW_CDC_MAX_PAYLOAD];
    uint32_t n;
    uint64_t last_us;
    uint32_t frames, dropped_bytes, timeouts;
} fw_cdc_frame_t;

void fw_cdc_frame_init(fw_cdc_frame_t *f);
/* Consume bytes from in[0..len) until one frame completes or the input ends. Returns bytes consumed; *frame_len = length of the
 * complete frame now in f->buf (0 = none yet). Call again with the rest of the input. */
size_t fw_cdc_frame_push(fw_cdc_frame_t *f, const uint8_t *in, size_t len, uint64_t now_us, size_t *frame_len);
#endif
