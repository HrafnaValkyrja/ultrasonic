/* fw/core/cdc_frame.c: CDC byte-stream reassembly (see cdc_frame.h). */
#include "cdc_frame.h"

#include <string.h>

void fw_cdc_frame_init(fw_cdc_frame_t *f)
{
    memset(f, 0, sizeof *f);
}

size_t fw_cdc_frame_push(fw_cdc_frame_t *f, const uint8_t *in, size_t len, uint64_t now_us, size_t *frame_len)
{
    *frame_len = 0u;
    if (in == NULL)
        return 0u;
    if (f->n > 0u && now_us - f->last_us > FW_CDC_GAP_US) {    /* stale partial frame */
        f->timeouts++;
        f->dropped_bytes += f->n;
        f->n = 0u;
    }
    size_t i = 0u;
    while (i < len) {
        uint8_t b = in[i++];
        f->last_us = now_us;
        if (f->n == 0u && b != FW_CDC_SOF) {
            f->dropped_bytes++;
            continue;
        }
        if (f->n == 2u && b > FW_CDC_MAX_PAYLOAD) {             /* impossible length: drop the start byte, rescan type and length */
            uint8_t re[2] = {f->buf[1], b};
            f->dropped_bytes++;
            f->n = 0u;
            for (uint32_t k = 0; k < 2u; k++) {
                if (f->n == 0u && re[k] != FW_CDC_SOF)
                    f->dropped_bytes++;
                else
                    f->buf[f->n++] = re[k];
            }
            continue;
        }
        f->buf[f->n++] = b;
        if (f->n >= 3u && f->n == 3u + (uint32_t)f->buf[2]) {
            *frame_len = f->n;
            f->n = 0u;
            f->frames++;
            return i;
        }
    }
    return i;
}
