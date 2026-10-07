/* FWSIM-R18 (mode FSM), R19 (docked interlock), R20 (charger supervision vs the BQ25180 fake), R29 (button gestures), R64 (current clamp on
 * the self-test / CDC paths), R65 (always-on fault break). Host tier, fakes only. */
#include <math.h>
#include <string.h>

#include "app.h"
#include "cdc_frame.h"
#include "fake.h"
#include "fw.h"
#include "tf.h"
#include "tests.h"
#include "variant_config.h"

static uint32_t rng32(uint32_t *s)
{
    uint32_t x = *s;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return *s = x;
}

static void knobs_default(fw_knobs_t *k, int32_t gesture)
{
    fw_knobs_defaults(k);
    TF_CHECK_EQ(fw_knob_set(k, FW_KNOB_gesture_option, gesture), FW_KNOB_OK);
#if FW_VAR_DOCKED_OUTPUT_MAX
    TF_CHECK_EQ(fw_knob_set(k, FW_KNOB_docked_output, 1), FW_KNOB_OK);
#endif
}

/* press for `ms`, with a 3-edge bounce at both ends (<= 6 ms, FWSIM-R29); poll every ms */
static uint64_t press(fw_state_t *st, uint64_t t, uint32_t ms)
{
    fw_event(st, FW_EV_BTN_EDGE, 1, t);
    fw_event(st, FW_EV_BTN_EDGE, 0, t + 2000u);
    fw_event(st, FW_EV_BTN_EDGE, 1, t + 4000u);
    for (uint32_t i = 5; i < ms; i++)
        fw_poll(st, t + i * 1000u);
    t += (uint64_t)ms * 1000u;
    fw_event(st, FW_EV_BTN_EDGE, 0, t);
    fw_event(st, FW_EV_BTN_EDGE, 1, t + 1500u);
    fw_event(st, FW_EV_BTN_EDGE, 0, t + 3000u);
    return t + 3000u;
}

static uint64_t idle(fw_state_t *st, uint64_t t, uint32_t ms)
{
    for (uint32_t i = 1; i <= ms; i++)
        fw_poll(st, t + i * 1000u);
    return t + (uint64_t)ms * 1000u;
}

/* FWSIM-R18: >= 1e6 random FSM events with invariants (a) output only in Full/Transient undocked or the variant-(a) self-test,
 * (b) Off = mic off, bridge stopped, pins parked; (c) every state reached and left */
void test_fsm_random_walk(void)
{
    fw_knobs_t k;
    knobs_default(&k, 2);
    fw_sys_t s;
    fw_sys_init(&s, &k, 0u);
    uint32_t seed = 0xC0FFEEu, bad_a = 0, bad_b = 0, reached[FW_ST_COUNT] = {0}, left[FW_ST_COUNT] = {0};
    uint64_t t = 0;
    for (uint32_t i = 0; i < 1000000u; i++) {
        uint32_t r = rng32(&seed);
        t += 1u + (r >> 22);                                      /* up to ~1 ms per step */
        uint32_t prev = s.mode;
        if ((r & 15u) == 0u)
            fw_sys_vbus_edge(&s, (r >> 4) & 1u, t);
        else if ((r & 15u) == 1u)
            t += 3000000u;                                        /* long gaps: debounce, cool-down, self-test timeout */
        else
            fw_sys_fsm(&s, &k, (r >> 8) % (uint32_t)FW_FE_COUNT, t);
        if ((r & 63u) == 2u) {                                    /* the break path sets its own latch */
            s.brk_latched = 1u;
            s.brk_us = t;
            fw_sys_fsm(&s, &k, FW_FE_FAULT, t);
        }
        fw_sys_poll(&s, &k, t);
        s.brk_clear_req = 0u;
        fw_outputs_t o = fw_sys_outputs(&s);
        uint32_t m = s.mode;
        uint32_t ok_a = !o.output_enable || ((m == FW_ST_FULL || m == FW_ST_TRANSIENT) && !s.vbus && !s.vbus_raw) ||
                        (m == FW_ST_DOCKED_SELFTEST && s.vbus && s.vbus_raw && FW_VAR_DOCKED_OUTPUT_MAX);
        bad_a += !ok_a;
        bad_b += m == FW_ST_OFF && (o.mic_power || o.bridge_run || !o.pins_parked);
        reached[m]++;
        if (prev != m)
            left[prev]++;
    }
    TF_CHECK_EQ(bad_a, 0);
    TF_CHECK_EQ(bad_b, 0);
    for (uint32_t m = 0; m < (uint32_t)FW_ST_COUNT; m++) {
        if (m == FW_ST_DOCKED_SELFTEST && !FW_VAR_DOCKED_OUTPUT_MAX) {
            TF_CHECK_EQ(reached[m], 0);                           /* variant (b): unreachable */
            continue;
        }
        if (reached[m] == 0u || left[m] == 0u)
            fprintf(stderr, "  state %s reached %u left %u\n", fw_mode_name(m), reached[m], left[m]);
        TF_CHECK(reached[m] > 0u);
        TF_CHECK(left[m] > 0u);
    }
}

/* FWSIM-R29 option B: short = Full <-> Transient (after the 0.3 s double window), double = volume step, hold 2 s = Off, press in Off = On */
void test_gestures_b(void)
{
    fw_state_t st;
    fw_knobs_t k;
    knobs_default(&k, 2);
    fw_init(&st, &k, 0u);
    TF_CHECK_EQ(st.sys.mode, FW_ST_TRANSIENT);
    int32_t v0 = st.sys.vol_idx;
    uint64_t t = press(&st, 1000000u, 80u);
    TF_CHECK_EQ(st.sys.mode, FW_ST_TRANSIENT);                      /* still waiting for a possible second press */
    t = idle(&st, t, 400u);
    TF_CHECK_EQ(st.sys.mode, FW_ST_FULL);
    t = press(&st, t + 50000u, 60u);
    t = press(&st, t + 100000u, 60u);                               /* second press inside 300 ms: double */
    t = idle(&st, t, 400u);
    TF_CHECK_EQ(st.sys.mode, FW_ST_FULL);
    TF_CHECK_EQ(st.sys.vol_idx, v0 + 1);
    TF_CHECK_EQ(st.vol_offset_cdb, k.volume_step_cdb);              /* DSP gain follows */
    t = press(&st, t + 50000u, 2300u);                              /* hold >= 2 s */
    TF_CHECK_EQ(st.sys.mode, FW_ST_OFF);
    t = idle(&st, t, 500u);
    TF_CHECK_EQ(st.sys.mode, FW_ST_OFF);                            /* the release of the hold is not a press */
    t = press(&st, t + 50000u, 80u);
    t = idle(&st, t, 50u);
    TF_CHECK_EQ(st.sys.mode, FW_ST_TRANSIENT);                      /* On at the power-on defaults */
    TF_CHECK_EQ(st.sys.vol_idx, v0);
    TF_CHECK_EQ(st.sys.gestures[FW_RG_DOUBLE], 1);
    TF_CHECK(st.sys.bounces >= 10u);
    /* stuck switch: held 6 s -> Off at 2 s, stuck flag at 5 s, nothing else until released */
    t = press(&st, t + 100000u, 6000u);
    TF_CHECK_EQ(st.sys.mode, FW_ST_OFF);
    TF_CHECK_EQ(st.sys.gestures[FW_RG_HOLD1], 2);
}

/* FWSIM-R18 (d), spec D3: from any mode and volume both sides re-match in two presses (B: hold + press; C: long hold + press);
 * option A needs up to three (sub-ui.md issue 5) */
void test_rematch_two_presses(void)
{
    for (int32_t opt = 1; opt <= 3; opt++) {
        uint32_t worst = 0;
        for (uint32_t start = 0; start < 6u; start++) {
            fw_state_t st;
            fw_knobs_t k;
            knobs_default(&k, opt);
            fw_init(&st, &k, 0u);
            uint64_t t = 1000000u;
            st.sys.mode = (start & 1u) ? FW_ST_FULL : FW_ST_TRANSIENT;
            st.sys.vol_idx = (int32_t)(start % 5u);
            uint32_t presses = 0;
            uint32_t off_ms = opt == 2 ? 2300u : (opt == 3 ? 4300u : 80u);
            while (!(st.sys.mode == FW_ST_TRANSIENT && st.sys.vol_idx == k.volume_steps / 2) && presses < 6u) {
                if (st.sys.mode == FW_ST_OFF)
                    t = press(&st, t + 50000u, 80u);
                else
                    t = press(&st, t + 50000u, off_ms);
                t = idle(&st, t, 500u);
                presses++;
            }
            worst = presses > worst ? presses : worst;
        }
        if (opt == 1)
            TF_CHECK(worst == 3u);                                    /* A: up to three, as sub-ui.md says */
        else
            TF_CHECK(worst <= 2u);
    }
}

static void app_boot_docked(fw_app_t *app, int32_t gesture)
{
    fake_reset();
    fake_bq25180_attach();
    fake_time_set_us(1000u);
    fw_app_boot(app);
    TF_CHECK_EQ(fw_knob_set(&app->st.knobs, FW_KNOB_gesture_option, gesture), FW_KNOB_OK);
#if FW_VAR_DOCKED_OUTPUT_MAX
    app->st.knobs.docked_output = 1;
#endif
}

static void app_run(fw_app_t *app, uint32_t ms)
{
    int32_t hop[128] = {0};
    for (uint32_t i = 0; i < ms; i++) {
        fake_time_advance_us(1000u);
        if (i % 2u == 0u) {
            fake_adf_script_hop(hop);
            fake_adf_isr();
        }
        fw_app_step(app);
    }
}

/* FWSIM-R19 docked interlock: plug stops output at once (raw PA1), glitches never enable docked output, PA1 stuck low is caught by the
 * charger's power good, variant (b) has no self-test path, variant (a) self-test stops within one hop of unplug */
void test_docked_interlock(void)
{
    static fw_app_t app;
    app_boot_docked(&app, 2);
    app_run(&app, 400u);                                             /* past the 300 ms power-on hold: listening */
    TF_CHECK(fw_outputs(&app.st).output_enable);
    TF_CHECK(app.bridge_on);
    fake_vbus(true);
    app_run(&app, 1u);
    TF_CHECK(!fw_outputs(&app.st).output_enable);                    /* the same step */
    app_run(&app, 50u);
    TF_CHECK_EQ(app.st.sys.mode, FW_ST_DOCKED_CHARGE);
    TF_CHECK(!app.bridge_on);
    /* glitch: 1 ms unplug while docked does not leave the dock state */
    fake_vbus(false);
    app_run(&app, 1u);
    fake_vbus(true);
    app_run(&app, 40u);
    TF_CHECK_EQ(app.st.sys.mode, FW_ST_DOCKED_CHARGE);
    TF_CHECK(!fw_outputs(&app.st).output_enable);
    /* self-test request */
    uint8_t arm[7] = {0xA5u, 0x01u, 4u, 0x38u, 0xFFu, 0x60u, 0x09u};   /* -200 cdB, 2400 Hz */
    uint8_t rep = 0;
    (void)fw_cdc_rx(&app.st, arm, sizeof arm, &rep, 1u);
#if FW_VAR_DOCKED_OUTPUT_MAX
    TF_CHECK_EQ(rep, 0x06);
    app_run(&app, 20u);
    TF_CHECK_EQ(app.st.sys.mode, FW_ST_DOCKED_SELFTEST);
    TF_CHECK(fw_outputs(&app.st).output_enable);
    fake_vbus(false);                                                /* unplug during the self-test */
    app_run(&app, 1u);
    TF_CHECK(!fw_outputs(&app.st).output_enable);
    app_run(&app, 60u);
    TF_CHECK_EQ(app.st.sys.mode, FW_ST_OFF);
#else
    TF_CHECK_EQ(rep, 0x15);                                          /* variant (b): NACK, no exemption code */
    app_run(&app, 20u);
    TF_CHECK_EQ(app.st.sys.mode, FW_ST_DOCKED_CHARGE);
    fake_vbus(false);
    app_run(&app, 60u);
    TF_CHECK_EQ(app.st.sys.mode, FW_ST_OFF);
#endif
    /* PA1 stuck low while docked: the charger's VIN_PGOOD (read on its /INT) keeps the pod docked */
    app_boot_docked(&app, 2);
    app_run(&app, 400u);
    fake_pa1_stuck(1u);
    fake_vbus(true);
    fw_event(&app.st, FW_EV_CHG_INT, 0, 0u);                         /* docking pulses /INT (PG_INT_MASK = 0) */
    app_run(&app, 50u);
    TF_CHECK(!fw_outputs(&app.st).output_enable);
    TF_CHECK_EQ(app.st.sys.mode, FW_ST_DOCKED_CHARGE);
    /* PA1 stuck high on battery: never listens (fails safe) */
    app_boot_docked(&app, 2);
    fake_pa1_stuck(2u);
    app_run(&app, 400u);
    TF_CHECK(!fw_outputs(&app.st).output_enable);
}

/* FWSIM-R64 on the self-test / CDC paths: whatever amplitude a frame asks for, |2 CCR/ARR - 1| stays within the current clamp, and the
 * tone path also within the -12 dBFS ceiling + shaper bound; random frames never crash */
void test_cdc_paths_clamp(void)
{
#if FW_VAR_DOCKED_OUTPUT_MAX
    static fw_app_t app;
    app_boot_docked(&app, 2);
    fake_vbus(true);
    app_run(&app, 60u);
    uint8_t arm[7] = {0xA5u, 0x01u, 4u, 0x58u, 0x02u, 0x60u, 0x09u};   /* +600 cdB requested (capped at -12 dBFS), 2400 Hz */
    uint8_t rep = 0;
    (void)fw_cdc_rx(&app.st, arm, sizeof arm, &rep, 1u);
    TF_CHECK_EQ(rep, 0x06);
    app_run(&app, 300u);
    double ceil = 0.36624, amp_max = (double)app.st.amp_max_ppm * 1e-6, worst = 0;
    size_t n;
    const uint16_t *c = fake_pwm_last(&n);
    for (size_t i = 0; i < n; i++)
        worst = fmax(worst, fabs(2.0 * c[i] / 200.0 - 1.0));
    TF_CHECK(worst > 0.1 && worst <= ceil);
    uint8_t raw[5] = {0xA5u, 0x03u, 2u, 0xFFu, 0x7Fu};               /* full-scale bring-up drive */
    (void)fw_cdc_rx(&app.st, raw, sizeof raw, &rep, 1u);
    TF_CHECK_EQ(rep, 0x06);
    app_run(&app, 4u);
    c = fake_pwm_last(&n);
    for (size_t i = 0; i < n; i++)
        TF_CHECK(fabs(2.0 * c[i] / 200.0 - 1.0) <= amp_max + 1e-9);
    TF_CHECK(app.st.clamp_hits > 0u);
#endif
    /* fuzz: random frames in any state (both variants) */
    fw_state_t st;
    fw_knobs_t k;
    knobs_default(&k, 2);
    fw_init(&st, &k, 0u);
    uint32_t seed = 77u, bad = 0;
    int32_t in[FW_HOP_N] = {0};
    uint16_t ccr[FW_CCR_MAX_PER_HOP];
    for (uint32_t i = 0; i < 20000u; i++) {
        uint8_t f[16];
        for (uint32_t j = 0; j < sizeof f; j++)
            f[j] = (uint8_t)rng32(&seed);
        if (i & 1u)
            f[0] = 0xA5u;
        if ((i & 7u) == 0u)
            fw_event(&st, (i & 8u) ? FW_EV_VBUS_ON : FW_EV_VBUS_OFF, 0, (uint64_t)i * 1000u);
        uint8_t r[4];
        (void)fw_cdc_rx(&st, f, 1u + (rng32(&seed) % sizeof f), r, sizeof r);
        fw_poll(&st, (uint64_t)i * 1000u + 500000u);
        size_t m = fw_hop(&st, in, ccr, FW_CCR_MAX_PER_HOP, NULL);
        for (size_t j = 0; j < m; j++)
            bad += fabs(2.0 * ccr[j] / (double)st.arr - 1.0) > (double)st.amp_max_ppm * 1e-6 + 1e-9;
    }
    TF_CHECK_EQ(bad, 0);
}

/* FWSIM-R20 charger plan: written in order (limits first, current last), read back, values per SLUSE99C bitfields */
void test_charger_plan(void)
{
    static fw_app_t app;
    app_boot_docked(&app, 2);
    app_run(&app, 2u);
    const uint8_t *r = fake_i2c_regs(0x6Au);
    TF_CHECK(r != NULL);
    TF_CHECK_EQ(r[0x0B] >> 6, 3);                                    /* TS_HOT 45 C */
    TF_CHECK_EQ(r[0x09] & 0x99u, 0);                                 /* EN_PUSH 0, PB_LPRESS_ACTION 00, REG_RST 0 */
    TF_CHECK_EQ(r[0x08] & 7u, 1);                                    /* ILIM 100 mA before enumeration */
    TF_CHECK_EQ((r[0x05] >> 2) & 3u, 0);                             /* VINDPM 4.2 V */
    TF_CHECK_EQ(r[0x07] & 0x13u, 0x11);                              /* 2XTMR_EN, WATCHDOG_SEL 01 */
    TF_CHECK_EQ(r[0x03], 0x46);                                      /* 4.20 V */
    TF_CHECK_EQ(r[0x04], 32);                                        /* not docked: temperature unknown -> 50 mA */
    TF_CHECK(app.chg_ok);
    /* write order: 0x0B first, 0x04 last */
    int32_t first = -1, last = -1;
    for (uint32_t i = 0; i < fake_log_len(); i++) {
        const fake_call_t *c = fake_log_at(i);
        if (c->fn == FAKE_FN_hal_i2c_write && c->a0 == 0x6Au) {
            if (first < 0)
                first = (int32_t)(c->a1 >> 8);
            last = (int32_t)(c->a1 >> 8);
        }
    }
    TF_CHECK_EQ(first, 0x0B);
    TF_CHECK_EQ(last, 0x04);
    /* docked at 25 C -> 170 mA (code 44); at 15 C -> 50 mA; USB enumerated -> ILIM 500 mA */
    uint16_t warm[1] = {(uint16_t)(10000.0 * 38e-6 * 1000.0 * exp(3435.0 * (1.0 / 298.15 - 1.0 / 298.15)) + 0.5)};
    fake_adc_script(HAL_ADC_TS, warm, 1u);
    fake_vbus(true);
    app_run(&app, 30u);
    TF_CHECK_EQ(r[0x04] & 0x7Fu, (uint32_t)app.st.knobs.ichg_code_warm);
    uint16_t cool[1] = {(uint16_t)(10000.0 * 38e-6 * 1000.0 * exp(3435.0 * (1.0 / 288.15 - 1.0 / 298.15)) + 0.5)};
    fake_adc_script(HAL_ADC_TS, cool, 1u);
    app_run(&app, 30u);
    TF_CHECK_EQ(r[0x04] & 0x7Fu, (uint32_t)app.st.knobs.ichg_code_cool);
    fw_event(&app.st, FW_EV_USB_ENUMERATED, 1, 0u);
    fw_event(&app.st, FW_EV_CHG_INT, 0, 0u);
    app_run(&app, 2u);
    TF_CHECK_EQ(r[0x08] & 7u, 5);
    TF_CHECK_EQ(fw_chg_ts_temp_c10(380u), 250);                      /* 10 k x 38 uA = 380 mV = 25.0 C */
}

/* FWSIM-R20: keep-alive keeps the 160 s watchdog from firing; after a revert / HW reset the plan is re-asserted at the next service;
 * I2C loss writes nothing and is retried; an unverifiable plan sets CHG_DIS */
void test_charger_watchdog_faults(void)
{
    static fw_app_t app;
    app_boot_docked(&app, 2);
    for (uint32_t s = 0; s < 600u; s++) {                            /* 10 min, a step every second */
        fake_time_advance_us(1000000u);
        fw_app_step(&app);
    }
    TF_CHECK_EQ(fake_bq()->hw_resets, 0);
    TF_CHECK_EQ(fake_bq()->wd_reverts, 0);
    TF_CHECK(app.st.knobs.chg_keepalive_s * 2 <= 160);
    /* firmware hang: 200 s without I2C -> HW reset to defaults; the next service sees it and re-asserts */
    fake_time_advance_us(200000000u);
    fw_app_step(&app);
    TF_CHECK_EQ(fake_bq()->hw_resets, 1);
    const uint8_t *r = fake_i2c_regs(0x6Au);
    TF_CHECK_EQ(r[0x0B] >> 6, 3);
    TF_CHECK(app.chg.reasserts >= 2u);
    TF_CHECK(app.chg_ok);
    /* I2C dead: no writes, recover called, fault reported, retried every keep-alive */
    uint32_t w0 = fake_calls(FAKE_FN_hal_i2c_write);
    fake_fault(FAKE_FN_hal_i2c_read, 0u, 0xFFFFFFFFu, HAL_NACK);
    for (uint32_t s = 0; s < 200u; s++) {
        fake_time_advance_us(1000000u);
        fw_app_step(&app);
    }
    TF_CHECK_EQ(fake_calls(FAKE_FN_hal_i2c_write), w0);
    TF_CHECK(app.chg.fault && !app.chg_ok);
    TF_CHECK(fake_calls(FAKE_FN_hal_i2c_recover) >= 3u);
    fake_fault_clear();
    /* a write that does not stick -> verify fails -> CHG_DIS */
    fake_i2c_regs(0x6Au)[0x0B] = 0x00u;                              /* plan broken */
    fake_fault(FAKE_FN_hal_i2c_write, 0u, 1u, HAL_NACK);             /* the first re-assert write fails */
    fake_time_advance_us(61000000u);
    fw_app_step(&app);
    TF_CHECK(app.chg.verify_fail >= 1u);
    TF_CHECK(r[0x04] & 0x80u);                                       /* CHG_DIS */
    fake_time_advance_us(61000000u);
    fw_app_step(&app);                                               /* healthy again: re-asserted, CHG_DIS cleared */
    TF_CHECK_EQ(r[0x04] & 0x80u, 0);
    TF_CHECK(app.chg_ok);
}

/* FWSIM-R65: break armed before every PWM start and disarmed only after the stop; an over-current latches it, the FSM goes SAFE, the bridge
 * stays off through the cool-down, then Off; BIF cleared once; a press turns the pod on again with the break re-armed */
void test_break_always_on(void)
{
    static fw_app_t app;
    app_boot_docked(&app, 2);
    app_run(&app, 400u);
    TF_CHECK(app.bridge_on);
    int32_t arm = fake_log_find(FAKE_FN_hal_brk_arm, 0u), start = fake_log_find(FAKE_FN_hal_pwm_start, 0u);
    TF_CHECK(arm >= 0 && start > arm);
    TF_CHECK_EQ(fake_brk()->threshold_ma, fw_app_brk_threshold_ma(&app));
    fake_isense_ma((int32_t)fake_brk()->threshold_ma + 1);
    TF_CHECK(fake_brk()->latched);
    app_run(&app, 1u);
    TF_CHECK_EQ(app.st.sys.mode, FW_ST_SAFE);
    TF_CHECK(!app.bridge_on);
    TF_CHECK(!fake_pwm()->running);
    {   /* stop order in the step that saw the break: PWM stop before the disarm */
        int32_t stop = -1, dis = -1;
        for (uint32_t i = 0; i < fake_log_len(); i++) {
            if (fake_log_at(i)->fn == FAKE_FN_hal_pwm_stop)
                stop = (int32_t)i;
            if (fake_log_at(i)->fn == FAKE_FN_hal_brk_disarm)
                dis = (int32_t)i;
        }
        TF_CHECK(stop >= 0 && dis > stop);
    }
    uint32_t starts = fake_calls(FAKE_FN_hal_pwm_start);
    app_run(&app, (uint32_t)app.st.knobs.brk_cooldown_ms - 50u);
    TF_CHECK_EQ(app.st.sys.mode, FW_ST_SAFE);
    TF_CHECK_EQ(fake_calls(FAKE_FN_hal_pwm_start), starts);
    app_run(&app, 100u);
    TF_CHECK_EQ(app.st.sys.mode, FW_ST_OFF);
    TF_CHECK_EQ(fake_brk()->clears, 1);
    TF_CHECK(!fake_brk()->latched);
    /* on again: the button wakes Stop 2; the app stays awake while the gesture is in progress */
    fake_wake_source(HAL_WAKE_BUTTON);
    app_run(&app, 1u);
    fw_event(&app.st, FW_EV_BTN_EDGE, 1, hal_time_us());
    app_run(&app, 80u);
    fw_event(&app.st, FW_EV_BTN_EDGE, 0, hal_time_us());
    app_run(&app, 50u);
    TF_CHECK_EQ(app.st.sys.mode, FW_ST_TRANSIENT);
    TF_CHECK(app.bridge_on);
    TF_CHECK_EQ(fake_brk()->arms, 2);
    /* a break that cannot be armed keeps the bridge off */
    app_boot_docked(&app, 2);
    fake_fault(FAKE_FN_hal_brk_arm, 0u, 0xFFFFFFFFu, HAL_TIMEOUT);
    app_run(&app, 400u);
    TF_CHECK(!app.bridge_on);
    TF_CHECK(app.start_errors > 0u);
    TF_CHECK_EQ(fake_calls(FAKE_FN_hal_pwm_start), 0);
}

/* FWSIM-R28: CDC stream reassembly. The same byte stream cut into packets of every size 1..23 yields the same frames; garbage between
 * frames and impossible lengths are skipped (counted); a frame stalled longer than FW_CDC_GAP_US is discarded */
void test_cdc_frame_stream(void)
{
    static const uint8_t s[] = {0x00u, 0x13u, 0xA5u, 0x02u, 0x00u,                   /* garbage, ST_STOP */
                                0xA5u, 0x01u, 0x04u, 0x38u, 0xFFu, 0x60u, 0x09u,     /* ST_ARM */
                                0xA5u, 0x07u, 0xFFu,                                 /* impossible length 255: dropped */
                                0xA5u, 0x09u, 0x40u, 0xA5u, 0x03u, 0x02u, 0xFFu, 0x7Fu,   /* length 64: resync, then RAW */
                                0xA5u, 0x04u, 0x00u};                                /* DFU_REQ */
    for (size_t chunk = 1u; chunk <= sizeof s; chunk++) {
        fw_cdc_frame_t f;
        fw_cdc_frame_init(&f);
        uint8_t types[8];
        size_t lens[8], nf = 0u;
        for (size_t at = 0u; at < sizeof s; at += chunk) {
            size_t len = sizeof s - at < chunk ? sizeof s - at : chunk, used = 0u;
            while (used < len) {
                size_t fl = 0u;
                used += fw_cdc_frame_push(&f, &s[at + used], len - used, 1000u, &fl);
                if (fl && nf < 8u) {
                    types[nf] = f.buf[1];
                    lens[nf++] = fl;
                }
            }
        }
        TF_CHECK_EQ(nf, 4u);
        if (nf == 4u) {
            TF_CHECK(types[0] == 0x02u && lens[0] == 3u && types[1] == 0x01u && lens[1] == 7u);
            TF_CHECK(types[2] == 0x03u && lens[2] == 5u && types[3] == 0x04u && lens[3] == 3u);
        }
        TF_CHECK_EQ(f.frames, 4u);
    }
    /* stall mid-frame: the half frame is dropped, the next complete frame decodes */
    fw_cdc_frame_t f;
    fw_cdc_frame_init(&f);
    size_t fl = 0u;
    static const uint8_t half[4] = {0xA5u, 0x01u, 0x04u, 0x38u}, stop[3] = {0xA5u, 0x02u, 0x00u};
    (void)fw_cdc_frame_push(&f, half, sizeof half, 0u, &fl);
    TF_CHECK_EQ(fl, 0u);
    (void)fw_cdc_frame_push(&f, stop, sizeof stop, FW_CDC_GAP_US + 1u, &fl);
    TF_CHECK_EQ(fl, 3u);
    TF_CHECK_EQ(f.timeouts, 1u);
    TF_CHECK_EQ(f.buf[1], 0x02u);
}

/* FWSIM-R28 + R64 through the USB path: OTG_FS powered only while PA1 shows VBUS; commands arrive as CDC bytes in arbitrary packets and
 * are answered; random byte streams in random packet sizes, with VBUS toggling, never drive the bridge past the FWSIM-R64 clamp */
void test_usb_cdc_lifecycle_clamp(void)
{
    static fw_app_t app;
    app_boot_docked(&app, 2);
    app_run(&app, 10u);
    TF_CHECK_EQ(fake_calls(FAKE_FN_hal_usb_enable), 0u);             /* no VBUS: never enabled */
    TF_CHECK(!app.usb_on);
    fake_vbus(true);
    app_run(&app, 60u);
    TF_CHECK(app.usb_on);
    uint8_t arm[7] = {0xA5u, 0x01u, 4u, 0x58u, 0x02u, 0x60u, 0x09u};
    fake_usb_rx(arm, 3u);                                            /* split across two packets */
    app_run(&app, 1u);
    fake_usb_rx(&arm[3], 4u);
    app_run(&app, 1u);
    uint8_t tx[8];
    size_t ntx = fake_usb_tx(tx, sizeof tx);
    TF_CHECK_EQ(ntx, 1u);
#if FW_VAR_DOCKED_OUTPUT_MAX
    TF_CHECK_EQ(tx[0], 0x06u);
#else
    TF_CHECK_EQ(tx[0], 0x15u);
#endif
    fake_vbus(false);
    app_run(&app, 2u);
    TF_CHECK(!app.usb_on);
    /* fuzz */
    uint32_t seed = 2026u, bad = 0u;
    app_boot_docked(&app, 2);
    fake_vbus(true);
    app_run(&app, 60u);
    for (uint32_t i = 0; i < 3000u; i++) {
        uint8_t b[24];
        size_t n = 1u + rng32(&seed) % sizeof b;
        for (size_t j = 0; j < n; j++)
            b[j] = (uint8_t)rng32(&seed);
        if (i % 3u == 0u) {                                          /* a well-formed frame with random payload */
            static const uint8_t ty[4] = {1u, 2u, 3u, 4u}, ln[4] = {4u, 0u, 2u, 0u};
            uint32_t k = rng32(&seed) % 4u;
            b[0] = 0xA5u;
            b[1] = k == 3u ? 2u : ty[k];                              /* no DFU reset in the fuzz */
            b[2] = ln[k == 3u ? 1u : k];
            n = 3u + b[2];
        }
        fake_usb_rx(b, n);
        if (i % 500u == 250u)
            fake_vbus(false);
        if (i % 500u == 260u)
            fake_vbus(true);
        app_run(&app, 1u);
        size_t m;
        const uint16_t *c = fake_pwm_last(&m);
        for (size_t j = 0; c != NULL && j < m; j++)
            bad += fabs(2.0 * c[j] / (double)app.st.arr - 1.0) > (double)app.st.amp_max_ppm * 1e-6 + 1e-9;
        uint8_t sink[64];
        (void)fake_usb_tx(sink, sizeof sink);
    }
    TF_CHECK_EQ(bad, 0u);
    TF_CHECK(app.cdc_replies >= 950u);                               /* ~1000 well-formed frames answered (garbage may swallow a few) */
}

/* FWSIM-R20 + R28: charger ILIM follows USB configuration: 100 mA docked on a dumb supply, 500 mA once a host configures the device,
 * back to 100 mA on suspend / bus reset, and a replug starts again at 100 mA */
void test_usb_ilim(void)
{
    static fw_app_t app;
    app_boot_docked(&app, 2);
    const uint8_t *r = fake_i2c_regs(0x6Au);
    fake_vbus(true);
    app_run(&app, 60u);
    TF_CHECK_EQ(r[0x08] & 7u, 1);                                    /* dumb supply / not yet enumerated: 100 mA */
    fake_usb_bus(HAL_USB_BUS_CONFIGURED);
    app_run(&app, 2u);
    TF_CHECK(app.usb_cfg && app.st.usb_enumerated);
    TF_CHECK_EQ(r[0x08] & 7u, 5);                                    /* 500 mA in the same pass */
    fake_usb_bus(HAL_USB_BUS_SUSPENDED);                             /* host suspends */
    TF_CHECK(fake_bq_iin_ua() > 2500u);
    app_run(&app, 2u);
    TF_CHECK_EQ((r[0x0A] >> 2) & 3u, 1);                             /* SYS_MODE 01: IN disconnected, SYS from the cell */
    TF_CHECK(fake_bq_iin_ua() <= 2500u);                              /* USB 2.0 suspend budget */
    TF_CHECK(app.chg_ok);                                            /* the suspend plan is verified, not a fault */
    TF_CHECK_EQ(r[0x04] & 0x80u, 0);                                  /* no CHG_DIS fallback */
    app_run(&app, 200u);
    TF_CHECK_EQ((r[0x0A] >> 2) & 3u, 1);                             /* held (keep-alive re-verifies it) */
    fake_usb_bus(HAL_USB_BUS_CONFIGURED);                            /* resume */
    app_run(&app, 2u);
    TF_CHECK_EQ(r[0x08] & 7u, 5);
    TF_CHECK_EQ((r[0x0A] >> 2) & 3u, 0);                             /* IN back */
    fake_usb_bus(HAL_USB_BUS_SUSPENDED);
    app_run(&app, 2u);
    TF_CHECK_EQ((r[0x0A] >> 2) & 3u, 1);
    fake_vbus(false);                                                /* unplug while suspended: VIN toggle resets SYS_MODE (and the core) */
    app_run(&app, 60u);
    TF_CHECK(!app.st.usb_enumerated && !app.usb_cfg);
    fake_usb_bus(HAL_USB_BUS_NONE);
    fake_vbus(true);                                                 /* replug on a dumb charger */
    app_run(&app, 60u);
    TF_CHECK_EQ(r[0x08] & 7u, 1);
    TF_CHECK_EQ((r[0x0A] >> 2) & 3u, 0);                             /* charges again */
    /* flat cell: the charger refuses SYS_MODE 01; accepted (counted), charging stays enabled, no fault */
    fake_bq_flat(true);
    fake_usb_bus(HAL_USB_BUS_CONFIGURED);
    app_run(&app, 2u);
    fake_usb_bus(HAL_USB_BUS_SUSPENDED);
    app_run(&app, 2u);
    TF_CHECK_EQ((r[0x0A] >> 2) & 3u, 0);
    TF_CHECK(app.chg_ok && app.chg.sys_mode_refused >= 1u);
    TF_CHECK_EQ(r[0x04] & 0x80u, 0);
}

/* FWSIM-R21 DFU handoff via CDC: accepted only while charging docked; guards re-checked after the settle time; charger watchdog off
 * (WATCHDOG_SEL 11) and verified before the request; USB soft-disconnected before it; any failed guard aborts back to DOCKED_CHARGE */
void test_dfu_handoff(void)
{
    static fw_app_t app;
    static const uint8_t dfu[3] = {0xA5u, 0x04u, 0x00u};
    uint8_t tx[8];
    /* happy path */
    app_boot_docked(&app, 2);
    const uint8_t *r = fake_i2c_regs(0x6Au);
    fake_vbus(true);
    fake_usb_bus(HAL_USB_BUS_CONFIGURED);
    app_run(&app, 60u);
    TF_CHECK_EQ(app.st.sys.mode, FW_ST_DOCKED_CHARGE);
    fake_usb_rx(dfu, sizeof dfu);
    app_run(&app, 2u);
    TF_CHECK_EQ(fake_usb_tx(tx, sizeof tx), 1u);
    TF_CHECK_EQ(tx[0], 0x06u);
    TF_CHECK_EQ(app.st.sys.mode, FW_ST_DFU_PENDING);
    TF_CHECK_EQ(fake_dfu_requests(), 0u);                            /* not before the settle time */
    app_run(&app, 60u);
    TF_CHECK_EQ(fake_dfu_requests(), 1u);
    TF_CHECK_EQ(r[0x07] & 3u, 3);                                    /* charger watchdog off for the ROM loader */
    int32_t i_off = fake_log_find(FAKE_FN_hal_usb_enable, 0u), i_req = fake_log_find(FAKE_FN_hal_usb_dfu_request, 0u);
    while (i_off >= 0 && fake_log_find(FAKE_FN_hal_usb_enable, (uint32_t)i_off + 1u) >= 0 &&
           fake_log_find(FAKE_FN_hal_usb_enable, (uint32_t)i_off + 1u) < i_req)
        i_off = fake_log_find(FAKE_FN_hal_usb_enable, (uint32_t)i_off + 1u);
    TF_CHECK(i_off >= 0 && i_req > i_off && fake_log_at((uint32_t)i_off)->a0 == 0u);   /* soft disconnect right before the request */
    TF_CHECK(!fake_pwm()->running);
    /* guard: no configured host -> abort to charging, watchdog back on */
    app_boot_docked(&app, 2);
    r = fake_i2c_regs(0x6Au);
    fake_vbus(true);
    app_run(&app, 60u);
    fake_usb_rx(dfu, sizeof dfu);
    app_run(&app, 80u);
    TF_CHECK_EQ(fake_dfu_requests(), 0u);
    TF_CHECK_EQ(app.dfu_refusals, 1u);
    TF_CHECK_EQ(app.st.sys.mode, FW_ST_DOCKED_CHARGE);
    TF_CHECK_EQ(r[0x07] & 3u, 1);
    /* guard: charger unreachable (plan not verifiable) -> abort */
    app_boot_docked(&app, 2);
    fake_vbus(true);
    fake_usb_bus(HAL_USB_BUS_CONFIGURED);
    app_run(&app, 60u);
    fake_usb_rx(dfu, sizeof dfu);
    app_run(&app, 2u);
    fake_fault(FAKE_FN_hal_i2c_write, 0u, 0xFFFFFFFFu, HAL_NACK);
    fake_fault(FAKE_FN_hal_i2c_read, 0u, 0xFFFFFFFFu, HAL_NACK);
    app_run(&app, 80u);
    TF_CHECK_EQ(fake_dfu_requests(), 0u);
    TF_CHECK(app.dfu_refusals >= 1u);
    TF_CHECK(app.st.sys.mode != (uint32_t)FW_ST_DFU_PENDING);
    fake_fault_clear();
    /* not docked: DFU_REQ is NACKed (listening, output path live) */
    app_boot_docked(&app, 2);
    app_run(&app, 400u);
    uint8_t rep = 0;
    (void)fw_cdc_rx(&app.st, dfu, sizeof dfu, &rep, 1u);
    TF_CHECK_EQ(rep, 0x15u);
    TF_CHECK(app.st.sys.mode != (uint32_t)FW_ST_DFU_PENDING);
#if FW_VAR_DOCKED_OUTPUT_MAX
    /* docked self-test running: NACK, the drive keeps its own state machine */
    app_boot_docked(&app, 2);
    fake_vbus(true);
    app_run(&app, 60u);
    uint8_t arm[7] = {0xA5u, 0x01u, 4u, 0x38u, 0xFFu, 0x60u, 0x09u};
    (void)fw_cdc_rx(&app.st, arm, sizeof arm, &rep, 1u);
    app_run(&app, 20u);
    TF_CHECK_EQ(app.st.sys.mode, FW_ST_DOCKED_SELFTEST);
    (void)fw_cdc_rx(&app.st, dfu, sizeof dfu, &rep, 1u);
    TF_CHECK_EQ(rep, 0x15u);
    TF_CHECK_EQ(app.st.sys.mode, FW_ST_DOCKED_SELFTEST);
#endif
}
