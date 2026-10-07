/* FWSIM-R6 / R30 (host part): dual-slot CRC knob store with power fail at every flash step, CRC and ECC errors, version change. */
#include <string.h>

#include "fake.h"
#include "crc32.h"
#include "knob_store.h"
#include "tf.h"
#include "tests.h"

static void knobs_with(fw_knobs_t *k, int32_t band_lo)
{
    fw_knobs_defaults(k);
    TF_CHECK_EQ(fw_knob_set(k, FW_KNOB_band_lo_hz, band_lo), FW_KNOB_OK);
}

void test_store_roundtrip(void)
{
    fake_reset();
    fw_knobs_t k, r;
    fw_store_info_t info = fw_store_load(&r);
    TF_CHECK(info.events & FW_STORE_EV_EMPTY);
    TF_CHECK(info.events & FW_STORE_EV_DEFAULTS);
    fw_knobs_t d;
    fw_knobs_defaults(&d);
    TF_CHECK(memcmp(&r, &d, sizeof r) == 0);
    for (int32_t i = 0; i < 6; i++) {                  /* alternate slots, sequence grows */
        knobs_with(&k, 20000 + i * 100);
        TF_CHECK_EQ(fw_store_save(&k, &info), HAL_OK);
        TF_CHECK_EQ(info.slot, (uint32_t)(i % 2));
        fw_store_info_t li = fw_store_load(&r);
        TF_CHECK_EQ(li.events, 0);
        TF_CHECK_EQ(li.seq, (uint32_t)(i + 1));
        TF_CHECK_EQ(r.band_lo_hz, 20000 + i * 100);
        TF_CHECK_EQ(li.slot, info.slot);
    }
}

void test_store_power_fail_every_step(void)
{
    /* a save is 1 erase + 13 quad-word programs; tear each step in turn: the load always returns old or new, never defaults */
    uint32_t steps = 0, old_seen = 0, new_seen = 0;
    for (uint32_t tear = 0; tear < 40u; tear++) {
        fake_reset();
        fw_knobs_t k, r;
        fw_store_info_t info = fw_store_load(&r);
        knobs_with(&k, 21000);
        TF_CHECK_EQ(fw_store_save(&k, &info), HAL_OK);          /* the "last good" record */
        knobs_with(&k, 21000);
        TF_CHECK_EQ(fw_store_save(&k, &info), HAL_OK);          /* both slots valid, newest in slot 1 */
        uint32_t ops0 = fake_flash_ops();
        knobs_with(&k, 33000);
        fake_flash_power_fail_after(tear);
        hal_status_t st = fw_store_save(&k, &info);
        uint32_t used = fake_flash_ops() - ops0;
        fake_flash_power_restore();                              /* reboot */
        fw_store_info_t li = fw_store_load(&r);
        TF_CHECK((li.events & FW_STORE_EV_DEFAULTS) == 0u);
        TF_CHECK(r.band_lo_hz == 21000 || r.band_lo_hz == 33000);
        if (st == HAL_OK) {
            TF_CHECK_EQ(r.band_lo_hz, 33000);
            new_seen++;
            if (used <= tear)
                break;                                           /* tear point beyond the save: every step covered */
        } else {
            TF_CHECK_EQ(r.band_lo_hz, 21000);
            old_seen++;
        }
        steps++;
    }
    TF_CHECK(old_seen >= 14u);                                   /* every step of the save was torn once */
    TF_CHECK_EQ(new_seen, 1);
    (void)steps;
}

void test_store_corruption(void)
{
    fake_reset();
    fw_knobs_t k, r;
    fw_store_info_t info = fw_store_load(&r);
    knobs_with(&k, 22000);
    TF_CHECK_EQ(fw_store_save(&k, &info), HAL_OK);               /* slot 0, seq 1 */
    knobs_with(&k, 23000);
    TF_CHECK_EQ(fw_store_save(&k, &info), HAL_OK);               /* slot 1, seq 2 */
    uint8_t *raw = fake_flash_raw();
    /* flip a payload bit in the newest slot: CRC fails -> previous record + BAD event */
    raw[HAL_FLASH_PAGE_BYTES + 40u] ^= 0x01u;
    fw_store_info_t li = fw_store_load(&r);
    TF_CHECK_EQ(r.band_lo_hz, 22000);
    TF_CHECK(li.events & FW_STORE_EV_BAD);
    TF_CHECK_EQ(li.slot, 0);
    /* ECC error on slot 0 as well: nothing usable -> defaults + events */
    fake_flash_ecc_at(32u);
    li = fw_store_load(&r);
    TF_CHECK(li.events & FW_STORE_EV_DEFAULTS);
    TF_CHECK(li.events & FW_STORE_EV_BAD);
    TF_CHECK((li.events & FW_STORE_EV_EMPTY) == 0u);
    fw_knobs_t d;
    fw_knobs_defaults(&d);
    TF_CHECK(memcmp(&r, &d, sizeof r) == 0);
    /* a save after that still works (writes the slot that is not newest) */
    fake_flash_ecc_at(0xFFFFFFFFu);
    knobs_with(&k, 24000);
    TF_CHECK_EQ(fw_store_save(&k, &li), HAL_OK);
    li = fw_store_load(&r);
    TF_CHECK_EQ(r.band_lo_hz, 24000);
}

void test_store_version_and_clamp(void)
{
    fake_reset();
    fw_knobs_t k, r;
    fw_store_info_t info = fw_store_load(&r);
    knobs_with(&k, 25000);
    TF_CHECK_EQ(fw_store_save(&k, &info), HAL_OK);
    /* rewrite it as a record of another knob version, with a valid CRC (what an older/newer firmware leaves behind) */
    uint8_t *raw = fake_flash_raw();
    uint32_t ver = FW_KNOBS_VERSION + 1u, crc;
    memcpy(raw + 4, &ver, 4);
    crc = fw_crc32_update(0u, raw, 20u);
    crc = fw_crc32_update(crc, raw + 32, sizeof(fw_knobs_t));
    memcpy(raw + 20, &crc, 4);
    fw_store_info_t li = fw_store_load(&r);
    TF_CHECK(li.events & FW_STORE_EV_VERSION);
    TF_CHECK(li.events & FW_STORE_EV_DEFAULTS);
    TF_CHECK((li.events & FW_STORE_EV_BAD) == 0u);
    TF_CHECK_EQ(li.seq, 1);                      /* the next save stays newer than the foreign record */
    (void)k;
    /* an out-of-range value in a valid record (older, wider range) is clamped on load + event */
    fake_reset();
    info = fw_store_load(&r);
    knobs_with(&k, 25000);
    k.ceiling_cdb = -300;                        /* would be -3 dBFS: past the hard clamp */
    TF_CHECK_EQ(fw_store_save(&k, &info), HAL_OK);
    li = fw_store_load(&r);
    TF_CHECK(li.events & FW_STORE_EV_CLAMPED);
    TF_CHECK_EQ(r.ceiling_cdb, -1200);
}

void test_store_faults(void)
{
    /* an erase or program error reported by the flash (not a power loss) fails the save and keeps the old record */
    fake_reset();
    fw_knobs_t k, r;
    fw_store_info_t info = fw_store_load(&r);
    knobs_with(&k, 26000);
    TF_CHECK_EQ(fw_store_save(&k, &info), HAL_OK);
    fake_fault(FAKE_FN_hal_flash_program_qw, 3u, 1u, HAL_ERR);
    knobs_with(&k, 27000);
    TF_CHECK(fw_store_save(&k, &info) != HAL_OK);
    fake_fault_clear();
    (void)fw_store_load(&r);
    TF_CHECK_EQ(r.band_lo_hz, 26000);
}
