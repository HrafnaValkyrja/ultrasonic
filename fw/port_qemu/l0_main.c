/* fw/port_qemu/l0_main.c: ARM L0 driver (FWSIM-R7) on QEMU mps2-an505 (Cortex-M33 + FPv5-SP + DSP, as the U575). Runs the SAME
 * fw/core objects as the product build (fwsim ARM_FLAGS) over a golden vector and writes every CCR word and tap through semihosting;
 * sim/fw/l0_arm.py compares the bytes with the host build. Not product firmware: no HAL, no peripherals.
 * l0_in.bin : u32 magic 'FWL0', n_hops, d2 (bit 0; bits 8..: hops not counted in L0_COUNT builds), t0_us_lo, t0_us_hi, n_knobs, then n_knobs x (u32 id, i32 value), then the words.
 * l0_count.bin (L0_COUNT): u64 ticks in fw_hop, u32 hops counted, u32 calibration ticks (2 x 65536 instructions), u32 ticks inside the FMAC model.
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

#if defined(L0_COUNT)
/* instruction counting (FWSIM-R47 E2): QEMU -icount shift=0 advances virtual time 1 ns per guest instruction; SysTick (processor clock)
 * counts that virtual time, so ticks around fw_hop x (instructions per tick, calibrated with a 2-instruction loop) = instructions. */
#define SYST_CSR (*(volatile uint32_t *)0xE000E010u)
#define SYST_RVR (*(volatile uint32_t *)0xE000E014u)
#define SYST_CVR (*(volatile uint32_t *)0xE000E018u)
static uint32_t ticks_between(uint32_t a, uint32_t b) { return (a - b) & 0xFFFFFFu; }   /* down-counter */
extern uint32_t l0_fmac_ticks;                                     /* hal_fmac_qemu.c: ticks inside the FMAC model */
#endif

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
#if defined(L0_COUNT)
    SYST_RVR = 0xFFFFFFu;
    SYST_CVR = 0u;
    SYST_CSR = 5u;                                                 /* enable, processor clock, no interrupt */
    uint32_t c0 = SYST_CVR;
    __asm__ volatile("mov r0, #0x10000\n1: subs r0, r0, #1\n bne 1b" ::: "r0", "cc");   /* 65536 x 2 instructions */
    uint32_t calib = ticks_between(c0, SYST_CVR);
    uint64_t ticks = 0u, fmac_ticks = 0u;
    uint32_t counted = 0u, skip = hdr[2] >> 8;                     /* hops before `skip` (power-on hold) are not counted */
#endif
    uint32_t per_in = (hdr[2] & 1u) ? 2u * FW_HOP_N : FW_HOP_N, fill = 0;
    for (uint32_t h = 0; h < hdr[1]; h++) {
        if (s_read(hi, words, per_in * 4u) != 0)
            s_exit(5u);
        fw_poll(&st, t0 + (uint64_t)st.hop_count * 640u);
        uint16_t ccr[FW_CCR_MAX_PER_HOP];
        fw_taps_t t;
#if defined(L0_COUNT)
        l0_fmac_ticks = 0u;
        uint32_t a = SYST_CVR;
#endif
        size_t n = (hdr[2] & 1u) ? fw_hop_d2(&st, words, ccr, FW_CCR_MAX_PER_HOP, &t) : fw_hop(&st, words, ccr, FW_CCR_MAX_PER_HOP, &t);
#if defined(L0_COUNT)
        uint32_t bb = SYST_CVR;
        if (h >= skip) {
            ticks += ticks_between(a, bb);
            fmac_ticks += l0_fmac_ticks;
            counted++;
        }
#endif
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
#if defined(L0_COUNT)
    uint32_t rec[5] = {(uint32_t)ticks, (uint32_t)(ticks >> 32), counted, calib, (uint32_t)fmac_ticks};
    int32_t hc = s_open("l0_count.bin", 5u);
    s_write(hc, rec, sizeof rec);
#endif
    s_exit(0u);
    return 0;
}
