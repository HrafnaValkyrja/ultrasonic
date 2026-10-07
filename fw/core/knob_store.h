/* fw/core/knob_store.h: dual-slot CRC knob store in two flash pages (FWSIM-R6, R30).
 * Record in each 8 KB page: [header 32 B = 2 quad words][fw_knobs_t padded to quad words]. A save erases the slot that does
 * NOT hold the newest valid record, programs the payload, then the header LAST (the CRC is in the second header quad word),
 * then reads back. Power loss at any step leaves the previous record intact: the half-written slot fails magic or CRC.
 * Load picks the valid record with the highest sequence; none valid (or a version/layout change) -> defaults + an event flag. */
#ifndef FW_CORE_KNOB_STORE_H
#define FW_CORE_KNOB_STORE_H
#include <stdint.h>
#include "hal_types.h"
#include "knobs.h"

#define FW_STORE_MAGIC 0xC0DE4B4Eu             /* "NK" + C0DE; outside every U5 address range (lint) */

#define FW_STORE_EV_EMPTY   (1u << 0)          /* both slots erased: first boot */
#define FW_STORE_EV_BAD     (1u << 1)          /* a slot failed magic/CRC/ECC (power loss or corruption) */
#define FW_STORE_EV_VERSION (1u << 2)          /* a record from another knob version/layout was ignored */
#define FW_STORE_EV_CLAMPED (1u << 3)          /* loaded values outside today's ranges were clamped */
#define FW_STORE_EV_DEFAULTS (1u << 4)         /* nothing usable: defaults in use */

typedef struct {
    uint32_t seq;          /* sequence of the loaded record (0 = defaults) */
    uint32_t slot;         /* 0/1, or 0xFF for defaults */
    uint32_t events;       /* FW_STORE_EV_* */
} fw_store_info_t;

fw_store_info_t fw_store_load(fw_knobs_t *k);
hal_status_t fw_store_save(const fw_knobs_t *k, fw_store_info_t *info);   /* info: in = last load/save, out = this save */
#endif
