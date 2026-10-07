/* FWSIM-R23 (Off / Stop 2 sequence and pin audit), FWSIM-R29 (LED duty, volume ticks), spec C9 (idle detector -> IDLE). */
#include <math.h>
#include <string.h>

#include "app.h"
#include "fake.h"
#include "fw.h"
#include "tf.h"
#include "tests.h"

static void boot(fw_app_t *app)
{
    fake_reset();
    fake_bq25180_attach();
    fake_time_set_us(1000u);
    fw_app_boot(app);
}

static void run(fw_app_t *app, uint32_t ms)
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

static int32_t find_after(fake_fn_t fn, int32_t from)
{
    return fake_log_find(fn, from < 0 ? 0u : (uint32_t)from);
}

/* FWSIM-R23: Off -> bridge stopped, break disarmed, PA5 low, PB3/PB4 analog, PB7 released, clocks prepared, RTC set, Stop 2; exit restores
 * the clock plan; the fake's pin/clock audit at every Stop 2 entry finds nothing; the RTC wake keeps the charger watchdog fed for 10 min */
void test_stop2_sequence(void)
{
    static fw_app_t app;
    boot(&app);
    run(&app, 400u);
    TF_CHECK(app.bridge_on && app.mic_on && app.led_duty_ppm > 0u);
    uint32_t mark = fake_log_len();
    fw_sys_fsm(&app.st.sys, &app.st.knobs, FW_FE_G_OFF, hal_time_us());
    fake_wake_source(HAL_WAKE_NONE);
    fw_app_step(&app);                                           /* one step: the whole Off sequence and one Stop 2 (RTC wake) */
    TF_CHECK_EQ(app.st.sys.mode, FW_ST_OFF);
    int32_t m = (int32_t)(mark > 0u ? mark - 1u : 0u);
    int32_t i_stop = find_after(FAKE_FN_hal_pwm_stop, m), i_dis = find_after(FAKE_FN_hal_brk_disarm, m);
    int32_t i_led = find_after(FAKE_FN_hal_led_set, m), i_clk = find_after(FAKE_FN_hal_clock_stop_prep, m);
    int32_t i_rtc = find_after(FAKE_FN_hal_power_rtc_wakeup_s, m), i_s2 = find_after(FAKE_FN_hal_power_stop2, m);
    int32_t i_plan = find_after(FAKE_FN_hal_clock_set_plan, i_s2);
    TF_CHECK(i_stop >= 0 && i_dis > i_stop && i_led > i_dis && i_clk > i_led && i_rtc > i_clk && i_s2 > i_rtc && i_plan > i_s2);
    TF_CHECK_EQ(fake_lp()->stop2_entries, 1);
    TF_CHECK_EQ(fake_lp()->audit_violations, 0);
    TF_CHECK_EQ(fake_lp()->rtc_s, (uint32_t)app.st.knobs.chg_keepalive_s);
    TF_CHECK_EQ(app.last_wake, HAL_WAKE_RTC);
    TF_CHECK(!fake_gpio_output(BOARD_PIN_MIC_VDD));
    TF_CHECK_EQ(fake_gpio_mode_of(BOARD_PIN_MIC_CLK), HAL_GPIO_ANALOG);
    TF_CHECK_EQ(fake_gpio_mode_of(BOARD_PIN_LED_K), HAL_GPIO_ANALOG);
    /* 10 minutes in Off: RTC wakes every 60 s, each one a charger keep-alive: no charger watchdog reset */
    for (uint32_t i = 0; i < 10u; i++)
        fw_app_step(&app);
    TF_CHECK(fake_lp()->stop2_entries >= 11u);
    TF_CHECK_EQ(fake_lp()->audit_violations, 0);
    TF_CHECK_EQ(fake_bq()->hw_resets, 0);
    TF_CHECK(app.chg.services >= 10u);
    /* button wake: stays awake through the gesture; a press in Off = On, mic and LED back */
    fake_wake_source(HAL_WAKE_BUTTON);
    fw_app_step(&app);
    TF_CHECK_EQ(app.last_wake, HAL_WAKE_BUTTON);
    uint32_t stops = fake_lp()->stop2_entries;
    fw_event(&app.st, FW_EV_BTN_EDGE, 1, hal_time_us());
    run(&app, 80u);
    fw_event(&app.st, FW_EV_BTN_EDGE, 0, hal_time_us());
    run(&app, 50u);
    TF_CHECK_EQ(fake_lp()->stop2_entries, stops);                /* no Stop 2 while the gesture ran */
    TF_CHECK_EQ(app.st.sys.mode, FW_ST_TRANSIENT);
    TF_CHECK(app.mic_on && fake_gpio_output(BOARD_PIN_MIC_VDD));
    TF_CHECK(app.led_duty_ppm > 0u);
    /* the audit itself works: Stop 2 with the bridge running is flagged */
    TF_CHECK(app.bridge_on);
    (void)hal_clock_stop_prep();
    (void)hal_power_stop2();
    TF_CHECK(fake_lp()->audit_violations >= 1u);
}

/* FWSIM-R29 LED: duty toward led_target_ua through R14 2k2 from VSYS (4.5 V docked, else VBAT); off in Off */
void test_led_duty(void)
{
    fw_knobs_t k;
    fw_knobs_defaults(&k);
    fw_sys_t s;
    fw_sys_init(&s, &k, 0u);
    uint32_t d45 = fw_led_duty_ppm(&s, &k, 4500u), d37 = fw_led_duty_ppm(&s, &k, 3700u), d30 = fw_led_duty_ppm(&s, &k, 3000u);
    /* I(100 %) = (V - 1.8 V) / 2.2 k: 1.227 / 0.864 / 0.545 mA -> 100 uA target = 8.1 / 11.6 / 18.3 % */
    TF_CHECK(d45 > 80000u && d45 < 83000u);
    TF_CHECK(d37 > 114000u && d37 < 118000u);
    TF_CHECK(d30 > 181000u && d30 < 185000u);
    TF_CHECK_EQ(fw_led_duty_ppm(&s, &k, 1700u), 1000000u);
    s.mode = FW_ST_OFF;
    TF_CHECK_EQ(fw_led_duty_ppm(&s, &k, 4500u), 0);
    static fw_app_t app;
    boot(&app);
    uint16_t vb[1] = {1850u};                                    /* VBAT 3.7 V through the 1 M / 1 M divider */
    fake_adc_script(HAL_ADC_VBAT_SENSE, vb, 1u);
    run(&app, 20u);
    TF_CHECK(fake_lp()->led_duty_ppm > 114000u && fake_lp()->led_duty_ppm < 118000u);
    fake_vbus(true);
    run(&app, 60u);
    TF_CHECK(fake_lp()->led_duty_ppm > 80000u && fake_lp()->led_duty_ppm < 83000u);   /* docked: VSYS 4.5 V */
}

/* FWSIM-R29 volume ticks: a volume step plays vol_idx + 1 ticks (15 ms, 2 kHz, -30 dBFS) through the normal output stage */
void test_volume_ticks(void)
{
    fw_state_t st;
    fw_knobs_t k;
    fw_knobs_defaults(&k);
    k.idle_enable = 0;
    fw_init(&st, &k, 0u);
    int32_t in[FW_HOP_N] = {0};
    uint16_t ccr[FW_CCR_MAX_PER_HOP];
    fw_taps_t t;
    for (uint32_t h = 0; h < 600u; h++) {                         /* past the power-on hold */
        fw_poll(&st, (uint64_t)h * 640u);
        (void)fw_hop(&st, in, ccr, FW_CCR_MAX_PER_HOP, &t);
    }
    fw_sys_fsm(&st.sys, &st.knobs, FW_FE_G_VOL, 600u * 640u);
    uint32_t want = (uint32_t)st.sys.vol_idx + 1u, bursts = 0, gap = 1000u;
    float pk = 0.0f;
    double ccr_dev = 0;
    for (uint32_t h = 600u; h < 600u + 2000u; h++) {
        fw_poll(&st, (uint64_t)h * 640u);
        size_t n = fw_hop(&st, in, ccr, FW_CCR_MAX_PER_HOP, &t);
        for (uint32_t s = 0; s < 8u; s++) {
            float a = fabsf(t.dsp_out[s]);
            pk = a > pk ? a : pk;
            if (a > 0.0f) {                                          /* a new burst after >= 50 silent samples (4 ms) */
                if (gap >= 50u)
                    bursts++;
                gap = 0u;
            } else {
                gap++;
            }
        }
        for (size_t j = 0; j < n; j++)
            ccr_dev = fmax(ccr_dev, fabs(2.0 * ccr[j] / 200.0 - 1.0));
    }
    TF_CHECK_EQ(bursts, want);
    TF_CHECK(pk > 0.025f && pk < 0.04f);                          /* -30 dBFS = 0.0316 */
    TF_CHECK(ccr_dev > 0.01 && ccr_dev <= 0.36624);               /* audible at the bridge, inside the ceiling bound */
}

/* spec C9: in Transient mode, silence -> IDLE (algorithm asleep, bridge stopped); a 40 kHz burst train -> back to Transient;
 * Full mode never goes IDLE (steady tones must stay audible) */
void test_idle_detector(void)
{
    for (int32_t full = 0; full <= 1; full++) {
        fw_state_t st;
        fw_knobs_t k;
        fw_knobs_defaults(&k);
        k.transient_only = full ? 0 : 1;
        k.idle_enable = 1;
        fw_init(&st, &k, 0u);
        int32_t in[FW_HOP_N];
        uint16_t ccr[FW_CCR_MAX_PER_HOP];
        uint32_t seed = 5u, idle_seen = 0, woke = 0;
        double ph = 0;
        for (uint32_t h = 0; h < 12000u; h++) {                      /* 7.7 s: 4 s noise, then 3 ms 40 kHz calls every 60 ms */
            for (uint32_t i = 0; i < FW_HOP_N; i++) {
                double tsec = (h * 128.0 + i) / 200e3;
                seed ^= seed << 13; seed ^= seed >> 17; seed ^= seed << 5;
                double x = ((double)(seed >> 8) / 16777216.0 - 0.5) * 2e-4;   /* mic self-noise stand-in, ~-80 dBFS */
                ph += 2 * 3.14159265358979 * 40e3 / 200e3;
                if (tsec > 4.0 && fmod(tsec, 0.06) < 0.003)
                    x += 0.05 * sin(ph);
                in[i] = (int32_t)lrint(x * 8388607.0) * 256;
            }
            fw_poll(&st, (uint64_t)h * 640u);
            (void)fw_hop(&st, in, ccr, FW_CCR_MAX_PER_HOP, NULL);
            if (st.sys.mode == FW_ST_IDLE)
                idle_seen++;
            if (h > 7000u && idle_seen && st.sys.mode != FW_ST_IDLE)
                woke = 1u;
        }
        if (full) {
            TF_CHECK_EQ(idle_seen, 0);
            TF_CHECK_EQ(st.sys.mode, FW_ST_FULL);
        } else {
            TF_CHECK(idle_seen > 1000u);
            TF_CHECK(woke);
            TF_CHECK(st.idle.hits > 10u);
        }
    }
}
