/* fw/core/knobs.h: versioned knob struct fw_knobs_t (FWSIM-R6). Generated layout: fw/spec/knobs.yaml -> fw/gen/knobs_def.h.
 * Every knob is an int32 in an integer unit (cdB, mA, ms, code) so ranges and hard clamps are compile-time checked. */
#ifndef FW_CORE_KNOBS_H
#define FW_CORE_KNOBS_H
#include <stddef.h>
#include <stdint.h>
#include "knobs_def.h"

#define FW_KNOB_FIELD(id, def, min, max, unit, src) int32_t id;
typedef struct {
    uint32_t version;   /* FW_KNOBS_VERSION */
    uint32_t layout;    /* FW_KNOBS_LAYOUT_HASH */
    FW_KNOBS(FW_KNOB_FIELD)
} fw_knobs_t;
#undef FW_KNOB_FIELD

#define FW_KNOB_ENUM(id, def, min, max, unit, src) FW_KNOB_##id,
typedef enum { FW_KNOBS(FW_KNOB_ENUM) FW_KNOB_COUNT } fw_knob_id_t;
#undef FW_KNOB_ENUM

typedef struct {
    const char *name;
    int32_t def, min, max;   /* min/max already include the hard clamps */
    const char *unit;
    const char *src;
} fw_knob_meta_t;

typedef enum { FW_KNOB_OK = 0, FW_KNOB_EID, FW_KNOB_ERANGE, FW_KNOB_EENUM } fw_knob_status_t;

extern const fw_knob_meta_t fw_knob_meta[FW_KNOB_COUNT];

void fw_knobs_defaults(fw_knobs_t *k);
fw_knob_status_t fw_knob_get(const fw_knobs_t *k, uint32_t id, int32_t *out);
fw_knob_status_t fw_knob_set(fw_knobs_t *k, uint32_t id, int32_t value);   /* rejects out-of-range / not-in-enum; k unchanged */
uint32_t fw_knobs_sanitize(fw_knobs_t *k);
uint8_t fw_knob_is_hard(uint32_t id);      /* 1 if a hard clamp (HC_*) bounds this knob */   /* clamp every field into [min, max] (+enum -> default); returns fields changed */
#endif
