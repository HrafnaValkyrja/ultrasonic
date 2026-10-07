/* fw/port_qemu/l0_main.c: ARM L0 driver (FWSIM-R7) on QEMU mps2-an505 (Cortex-M33 + FPv5-SP + DSP, as the U575). Runs the SAME
 * fw/core objects as the product build (fwsim ARM_FLAGS) over a golden vector and writes every CCR word and tap through semihosting;
 * sim/fw/l0_arm.py compares the bytes with the host build. Not product firmware: no HAL, no peripherals.
 * l0_in.bin : u32 magic 'FWL0', n_hops, d2, t0_us_lo, t0_us_hi, n_knobs, then n_knobs x (u32 id, i32 value), then the words.
 * l0_out.bin: per hop: u16 ccr[n] (n = 128*200/ARR), f32 dsp[8], band[28], floor[28], peak, norm[3], u32 sq, clamp. */
#include <stdint.h>
#include <string.h>

#include "fw.h"

static int32_t semi(int32_t op, const void *arg)
{
    register int32_t r0 __asm__("r0") = op;
    register const void *r1 __asm__("r1") = arg;
    __asm__ volatile("bkpt 0xAB" : "+r"(r0) : "r"(r1) : "memory");
    return r0;
}
static int32_t s_open(const char *name, uint32_t mode)
{
    uint32_t a[3] = {(uint32_t)(uintptr_t)name, mode, (uint32_t)strlen(name)};
    return semi(0x01, a);
}
static int32_t s_read(int32_t h, void *buf, uint32_t n)          /* returns bytes NOT read */
{
    uint32_t a[3] = {(uint32_t)h, (uint32_t)(uintptr_t)buf, n};
    return semi(0x06, a);
}
static int32_t s_write(int32_t h, const void *buf, uint32_t n)
{
    uint32_t a[3] = {(uint32_t)h, (uint32_t)(uintptr_t)buf, n};
    return semi(0x05, a);
}
static void s_exit(uint32_t code)
{
    uint32_t a[2] = {0x20026u, code};                             /* ADP_Stopped_ApplicationExit */
    (void)semi(0x20, a);                                          /* SYS_EXIT_EXTENDED */
    for (;;) {}
}

static fw_state_t st;
static int32_t words[2u * FW_HOP_N];
static uint8_t obuf[64u * 1024u];

int main(void)
{
    int32_t hi = s_open("l0_in.bin", 1u), ho = s_open("l0_out.bin", 5u);   /* 1 = "rb", 5 = "wb" */
    if (hi < 0 || ho < 0)
        s_exit(2u);
    uint32_t hdr[6];
    if (s_read(hi, hdr, sizeof hdr) != 0 || hdr[0] != 0x304C5746u)
        s_exit(3u);
    fw_knobs_t k;
    fw_knobs_defaults(&k);
    for (uint32_t i = 0; i < hdr[5]; i++) {
        int32_t kv[2];
        if (s_read(hi, kv, sizeof kv) != 0 || fw_knob_set(&k, (uint32_t)kv[0], kv[1]) != FW_KNOB_OK)
            s_exit(4u);
    }
    fw_init(&st, &k, 0u);
    uint64_t t0 = (uint64_t)hdr[3] | ((uint64_t)hdr[4] << 32);
    uint32_t per_in = hdr[2] ? 2u * FW_HOP_N : FW_HOP_N, fill = 0;
    for (uint32_t h = 0; h < hdr[1]; h++) {
        if (s_read(hi, words, per_in * 4u) != 0)
            s_exit(5u);
        fw_poll(&st, t0 + (uint64_t)st.hop_count * 640u);
        uint16_t ccr[FW_CCR_MAX_PER_HOP];
        fw_taps_t t;
        size_t n = hdr[2] ? fw_hop_d2(&st, words, ccr, FW_CCR_MAX_PER_HOP, &t) : fw_hop(&st, words, ccr, FW_CCR_MAX_PER_HOP, &t);
        uint32_t rec = (uint32_t)n * 2u + (8u + 28u + 28u + 1u + 3u) * 4u + 8u;
        if (fill + rec > sizeof obuf) {
            s_write(ho, obuf, fill);
            fill = 0;
        }
        uint8_t *p = &obuf[fill];
        memcpy(p, ccr, n * 2u), p += n * 2u;
        memcpy(p, t.dsp_out, 32u), p += 32u;
        memcpy(p, t.band_energy, 112u), p += 112u;
        memcpy(p, t.floor, 112u), p += 112u;
        memcpy(p, &t.pre_q_true_peak, 4u), p += 4u;
        memcpy(p, t.shaper_norm, 12u), p += 12u;
        memcpy(p, &t.squelch_state, 4u), p += 4u;
        memcpy(p, &t.clamp_hits, 4u);
        fill += rec;
    }
    s_write(ho, obuf, fill);
    s_exit(0u);
    return 0;
}
