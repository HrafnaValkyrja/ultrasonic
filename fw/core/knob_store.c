#include "knob_store.h"

#include <string.h>

#include "crc32.h"
#include "hal_flash.h"

#define HDR_BYTES 32u
#define PAYLOAD_BYTES (((uint32_t)sizeof(fw_knobs_t) + HAL_FLASH_QW_BYTES - 1u) / HAL_FLASH_QW_BYTES * HAL_FLASH_QW_BYTES)
_Static_assert(HDR_BYTES + PAYLOAD_BYTES <= HAL_FLASH_PAGE_BYTES, "knob record does not fit one flash page");
_Static_assert(HAL_FLASH_KNOB_PAGES >= 2u, "dual slot needs two pages");

typedef struct {
    uint32_t magic, version, layout, size;    /* quad word 0 */
    uint32_t seq, crc, rsv0, rsv1;            /* quad word 1: programmed last of the header */
} rec_hdr_t;
_Static_assert(sizeof(rec_hdr_t) == HDR_BYTES, "header layout");

static uint32_t rec_crc(const rec_hdr_t *h, const uint8_t *payload)
{
    uint32_t c = fw_crc32_update(0u, h, 20u);  /* magic, version, layout, size, seq */
    return fw_crc32_update(c, payload, sizeof(fw_knobs_t));
}

typedef enum { SLOT_EMPTY, SLOT_BAD, SLOT_VERSION, SLOT_OK } slot_state_t;

static slot_state_t read_slot(uint32_t slot, rec_hdr_t *h, uint8_t *payload)
{
    uint32_t base = slot * HAL_FLASH_PAGE_BYTES;
    if (hal_flash_read(base, (uint8_t *)h, HDR_BYTES) != HAL_OK)
        return SLOT_BAD;
    if (h->magic == 0xFFFFFFFFu && h->seq == 0xFFFFFFFFu)
        return SLOT_EMPTY;
    if (h->magic != FW_STORE_MAGIC || h->size != (uint32_t)sizeof(fw_knobs_t))
        return SLOT_BAD;
    if (hal_flash_read(base + HDR_BYTES, payload, sizeof(fw_knobs_t)) != HAL_OK)
        return SLOT_BAD;
    if (rec_crc(h, payload) != h->crc)
        return SLOT_BAD;
    if (h->version != FW_KNOBS_VERSION || h->layout != FW_KNOBS_LAYOUT_HASH)
        return SLOT_VERSION;
    return SLOT_OK;
}

static int newer(uint32_t a, uint32_t b)
{
    return (int32_t)(a - b) > 0;
}

fw_store_info_t fw_store_load(fw_knobs_t *k)
{
    fw_store_info_t info = {0u, 0xFFu, 0u};
    rec_hdr_t h[2];
    uint8_t payload[2][sizeof(fw_knobs_t)];
    slot_state_t s[2];
    int best = -1;
    for (uint32_t i = 0; i < 2u; i++) {
        s[i] = read_slot(i, &h[i], payload[i]);
        if (s[i] == SLOT_BAD)
            info.events |= FW_STORE_EV_BAD;
        if (s[i] == SLOT_VERSION)
            info.events |= FW_STORE_EV_VERSION;
        if (s[i] == SLOT_OK && (best < 0 || newer(h[i].seq, h[best].seq)))
            best = (int)i;
    }
    if (best < 0) {
        if (s[0] == SLOT_EMPTY && s[1] == SLOT_EMPTY)
            info.events |= FW_STORE_EV_EMPTY;
        info.events |= FW_STORE_EV_DEFAULTS;
        fw_knobs_defaults(k);
        /* keep the highest sequence seen so the next save is newer than any record still in flash */
        for (uint32_t i = 0; i < 2u; i++)
            if (s[i] == SLOT_VERSION && newer(h[i].seq, info.seq))
                info.seq = h[i].seq;
        return info;
    }
    memcpy(k, payload[best], sizeof *k);
    info.seq = h[best].seq;
    info.slot = (uint32_t)best;
    if (fw_knobs_sanitize(k) != 0u)
        info.events |= FW_STORE_EV_CLAMPED;
    return info;
}

hal_status_t fw_store_save(const fw_knobs_t *k, fw_store_info_t *info)
{
    uint32_t slot = (info->slot == 0u) ? 1u : 0u;  /* never touch the slot holding the newest valid record */
    uint32_t base = slot * HAL_FLASH_PAGE_BYTES;
    uint8_t buf[PAYLOAD_BYTES];
    rec_hdr_t h;
    memset(buf, 0, sizeof buf);
    memcpy(buf, k, sizeof *k);
    memset(&h, 0, sizeof h);
    h.magic = FW_STORE_MAGIC;
    h.version = FW_KNOBS_VERSION;
    h.layout = FW_KNOBS_LAYOUT_HASH;
    h.size = (uint32_t)sizeof(fw_knobs_t);
    h.seq = info->seq + 1u;
    h.crc = rec_crc(&h, buf);
    hal_status_t st = hal_flash_erase_page(slot);
    for (uint32_t off = 0; st == HAL_OK && off < PAYLOAD_BYTES; off += HAL_FLASH_QW_BYTES)
        st = hal_flash_program_qw(base + HDR_BYTES + off, buf + off);
    if (st == HAL_OK)
        st = hal_flash_program_qw(base, (const uint8_t *)&h);
    if (st == HAL_OK)
        st = hal_flash_program_qw(base + HAL_FLASH_QW_BYTES, (const uint8_t *)&h + HAL_FLASH_QW_BYTES);
    if (st != HAL_OK)
        return st;
    rec_hdr_t rh;
    uint8_t rp[sizeof(fw_knobs_t)];
    if (read_slot(slot, &rh, rp) != SLOT_OK || rh.seq != h.seq)
        return HAL_ERR;
    info->seq = h.seq;
    info->slot = slot;
    info->events = 0u;
    return HAL_OK;
}
