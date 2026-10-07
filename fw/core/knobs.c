/* fw/core/knobs.c: knob table, compile-time hard clamps (FWSIM-R6, FWSIM-R64). */
#include "knobs.h"

#include <string.h>

/* ---- compile-time checks: default inside [min, max]; hard clamps never passable */
#define FW_KNOB_LIMITS(id, def, min, max, unit, src) FW_KNOB_MIN_##id = (min), FW_KNOB_MAX_##id = (max), FW_KNOB_DEF_##id = (def),
enum { FW_KNOBS(FW_KNOB_LIMITS) FW_KNOB_LIMITS_END };
#undef FW_KNOB_LIMITS

#define FW_KNOB_ASSERT(id, def, min, max, unit, src) \
    _Static_assert(FW_KNOB_MIN_##id <= FW_KNOB_DEF_##id && FW_KNOB_DEF_##id <= FW_KNOB_MAX_##id, "knob " #id ": default outside [min, max]");
FW_KNOBS(FW_KNOB_ASSERT)
#undef FW_KNOB_ASSERT

#define FW_KNOB_HARD_max(id, hc) (FW_KNOB_MAX_##id <= (hc))
#define FW_KNOB_HARD_min(id, hc) (FW_KNOB_MIN_##id >= (hc))
#define FW_KNOB_HARD_ASSERT(id, bound, hc) _Static_assert(FW_KNOB_HARD_##bound(id, hc), "knob " #id ": range passes hard clamp " #hc);
FW_KNOBS_HARD(FW_KNOB_HARD_ASSERT)
#undef FW_KNOB_HARD_ASSERT

_Static_assert(HC_CEILING_CDB_MAX <= -1200, "listening ceiling hard clamp must stay <= -12 dBFS (FWSIM design_binding.ceiling_dbfs)");
_Static_assert(HC_ICHG_CODE_MAX <= 44, "ICHG <= 170 mA (code 44) for every cell (FWSIM hard_clamps)");
_Static_assert(HC_VBATREG_CODE_MAX <= 0x46, "VBATREG <= 4.20 V (cell limit)");
_Static_assert(HC_DEADTIME_TICKS_MIN >= 1, "dead time >= 1 tick");
_Static_assert(HC_ARR_MIN >= 50, "ARR >= 50");
_Static_assert(sizeof(fw_knobs_t) == 8u + 4u * (size_t)FW_KNOB_COUNT, "fw_knobs_t has padding: the flash record would be ambiguous");

/* ---- table */
#define FW_KNOB_HARD_FLAG(id, bound, hc) [FW_KNOB_##id] = 1,
static const uint8_t knob_hard[FW_KNOB_COUNT] = {FW_KNOBS_HARD(FW_KNOB_HARD_FLAG)};
#undef FW_KNOB_HARD_FLAG

#define FW_KNOB_META(id, def, min, max, unit, src) [FW_KNOB_##id] = {#id, (def), (min), (max), unit, src},
const fw_knob_meta_t fw_knob_meta[FW_KNOB_COUNT] = {FW_KNOBS(FW_KNOB_META)};
#undef FW_KNOB_META

#define FW_KNOB_OFFSET(id, def, min, max, unit, src) [FW_KNOB_##id] = offsetof(fw_knobs_t, id),
static const uint16_t knob_offset[FW_KNOB_COUNT] = {FW_KNOBS(FW_KNOB_OFFSET)};
#undef FW_KNOB_OFFSET

static int32_t *knob_ptr(fw_knobs_t *k, uint32_t id)
{
    return (int32_t *)(void *)((uint8_t *)k + knob_offset[id]);
}

static int enum_ok(uint32_t id, int32_t v)
{
    int has = 0, ok = 0;
#define FW_KNOB_ENUM_CHECK(kid, val) \
    if (id == (uint32_t)FW_KNOB_##kid) { has = 1; if (v == (val)) ok = 1; }
    FW_KNOBS_ENUM(FW_KNOB_ENUM_CHECK)
#undef FW_KNOB_ENUM_CHECK
    return !has || ok;
}

void fw_knobs_defaults(fw_knobs_t *k)
{
    memset(k, 0, sizeof *k);
    k->version = FW_KNOBS_VERSION;
    k->layout = FW_KNOBS_LAYOUT_HASH;
    for (uint32_t i = 0; i < (uint32_t)FW_KNOB_COUNT; i++)
        *knob_ptr(k, i) = fw_knob_meta[i].def;
}

fw_knob_status_t fw_knob_get(const fw_knobs_t *k, uint32_t id, int32_t *out)
{
    if (id >= (uint32_t)FW_KNOB_COUNT)
        return FW_KNOB_EID;
    *out = *knob_ptr((fw_knobs_t *)(uintptr_t)k, id);
    return FW_KNOB_OK;
}

fw_knob_status_t fw_knob_set(fw_knobs_t *k, uint32_t id, int32_t value)
{
    if (id >= (uint32_t)FW_KNOB_COUNT)
        return FW_KNOB_EID;
    if (value < fw_knob_meta[id].min || value > fw_knob_meta[id].max)
        return FW_KNOB_ERANGE;
    if (!enum_ok(id, value))
        return FW_KNOB_EENUM;
    *knob_ptr(k, id) = value;
    return FW_KNOB_OK;
}

uint32_t fw_knobs_sanitize(fw_knobs_t *k)
{
    uint32_t changed = 0;
    for (uint32_t i = 0; i < (uint32_t)FW_KNOB_COUNT; i++) {
        int32_t *p = knob_ptr(k, i), v = *p;
        if (v < fw_knob_meta[i].min)
            v = fw_knob_meta[i].min;
        if (v > fw_knob_meta[i].max)
            v = fw_knob_meta[i].max;
        if (!enum_ok(i, v))
            v = fw_knob_meta[i].def;
        if (v != *p) {
            *p = v;
            changed++;
        }
    }
    return changed;
}

uint8_t fw_knob_is_hard(uint32_t id)
{
    return id < (uint32_t)FW_KNOB_COUNT ? knob_hard[id] : 0u;
}
