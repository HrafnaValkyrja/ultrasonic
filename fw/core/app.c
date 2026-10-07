#include "app.h"

#include <string.h>

#include "hal.h"
#include "variant_config.h"

void fw_app_boot(fw_app_t *app)
{
    memset(app, 0, sizeof *app);                /* a boot is a power-on: nothing survives (the target's app is static, the tests reuse one) */
    fw_knobs_t k;
    app->store = fw_store_load(&k);
    fw_init(&app->st, &k, hal_time_us());
    if (app->store.events & FW_STORE_EV_DEFAULTS)
        fw_event(&app->st, FW_EV_KNOBS_DEFAULTED, (int32_t)app->store.events, hal_time_us());
    if (app->store.events & FW_STORE_EV_CLAMPED)
        fw_event(&app->st, FW_EV_KNOBS_CLAMPED, 0, hal_time_us());
    hal_power_ucpd_dbdis();                     /* ECR-0013: release PB15/PA15 dead-battery pull-downs before PWM */
    hal_pwm_cfg_t cfg = {(uint16_t)app->st.arr, 1u, (uint8_t)app->st.dt_rise, (uint8_t)app->st.dt_fall};
    (void)hal_pwm_config(&cfg);
    (void)hal_wdt_start((uint32_t)app->st.knobs.iwdg_ms);
    app->hops = 0u;
    app->submit_errors = 0u;
    app->vbus_seen = 0u;
    app->bridge_on = app->brk_reported = app->start_errors = 0u;
    app->chg_temp_class = 0xFFu;
    memset(&app->chg, 0, sizeof app->chg);
}

uint32_t fw_app_brk_threshold_ma(const fw_app_t *app)
{
    int32_t i = app->st.knobs.out_i_peak_ma < FW_VAR_I_PEAK_MA_MAX ? app->st.knobs.out_i_peak_ma : FW_VAR_I_PEAK_MA_MAX;
    return (uint32_t)(i + app->st.knobs.brk_margin_ma);   /* FWSIM-R65: i_peak_max (FWSIM-R64) + margin */
}

/* bridge on/off with the break armed before the first PWM edge and disarmed only after MOE = 0 (FWSIM-R65) */
static void apply_outputs(fw_app_t *app)
{
    fw_outputs_t o = fw_outputs(&app->st);
    if (o.brk_clear) {
        hal_brk_clear();
        fw_brk_clear_done(&app->st);
        app->brk_reported = 0u;
    }
    if (o.bridge_run && !app->bridge_on) {
        if (hal_brk_arm(fw_app_brk_threshold_ma(app)) == HAL_OK && hal_pwm_start() == HAL_OK)
            app->bridge_on = 1u;
        else
            app->start_errors++;                 /* never run the bridge without the break armed */
    } else if (!o.bridge_run && app->bridge_on) {
        hal_pwm_stop();
        hal_brk_disarm();
        app->bridge_on = 0u;
    }
    if (app->bridge_on && !app->brk_reported && hal_brk_latched()) {
        app->brk_reported = 1u;
        fw_event(&app->st, FW_EV_BREAK, 0, hal_time_us());
        hal_pwm_stop();                          /* MOE is already 0 in hardware; keep the software state consistent */
        hal_brk_disarm();
        app->bridge_on = 0u;
    }
}

/* mic power + ADF pins and the LED follow the mode (sub-ui.md issue 7: LED duty from VSYS = 4.5 V docked, else VBAT) */
static void apply_mic_led(fw_app_t *app)
{
    fw_outputs_t o = fw_outputs(&app->st);
    if (o.mic_power != app->mic_on) {
        app->mic_on = o.mic_power;
        if (o.mic_power) {
            hal_gpio_write(BOARD_PIN_MIC_VDD, true);
            (void)hal_gpio_mode(BOARD_PIN_MIC_CLK, HAL_GPIO_AF);
            (void)hal_gpio_mode(BOARD_PIN_MIC_DATA, HAL_GPIO_AF);
            (void)hal_adf_start(4000450u);
        } else {
            hal_adf_stop();
            hal_gpio_write(BOARD_PIN_MIC_VDD, false);
            (void)hal_gpio_mode(BOARD_PIN_MIC_CLK, HAL_GPIO_ANALOG);
            (void)hal_gpio_mode(BOARD_PIN_MIC_DATA, HAL_GPIO_ANALOG);
        }
    }
    uint32_t vsys = 4500u;
    if (!app->st.vbus) {
        uint16_t mv = 0u;
        vsys = hal_adc_read_mv(HAL_ADC_VBAT_SENSE, &mv) == HAL_OK ? 2u * mv : 3700u;   /* R8/R9 1 M / 1 M divider */
    }
    uint32_t duty = fw_led_duty_ppm(&app->st.sys, &app->st.knobs, vsys);
    uint32_t diff = duty > app->led_duty_ppm ? duty - app->led_duty_ppm : app->led_duty_ppm - duty;
    if (diff > 10000u || (duty == 0u) != (app->led_duty_ppm == 0u)) {   /* re-write on > 1 % change */
        if (duty && !app->led_duty_ppm)
            (void)hal_gpio_mode(BOARD_PIN_LED_K, HAL_GPIO_AF);
        if (hal_led_set(duty) == HAL_OK)
            app->led_duty_ppm = duty;
        if (!duty)
            (void)hal_gpio_mode(BOARD_PIN_LED_K, HAL_GPIO_ANALOG);
    }
}

static void service_charger(fw_app_t *app, uint32_t force);

/* FWSIM-R23 Off: bridge stopped (break disarmed after) -> squelch (core) -> PA5 low -> PB3/PB4 analog, no pull -> PB7 released ->
 * PLL2/PLL3/HSI48/SHSI off with RDY clear -> RTC wake for the charger keep-alive -> Stop 2 (SMPS) -> exit restores the clock plan */
static void enter_stop2(fw_app_t *app)
{
    if (app->bridge_on) {
        hal_pwm_stop();
        hal_brk_disarm();
        app->bridge_on = 0u;
    }
    hal_adf_stop();
    hal_gpio_write(BOARD_PIN_MIC_VDD, false);
    (void)hal_gpio_mode(BOARD_PIN_MIC_CLK, HAL_GPIO_ANALOG);
    (void)hal_gpio_mode(BOARD_PIN_MIC_DATA, HAL_GPIO_ANALOG);
    app->mic_on = 0u;
    (void)hal_led_set(0u);
    (void)hal_gpio_mode(BOARD_PIN_LED_K, HAL_GPIO_ANALOG);
    app->led_duty_ppm = 0u;
    if (hal_clock_stop_prep() != HAL_OK)
        return;                                  /* never enter Stop 2 with the PLLs still requested */
    (void)hal_power_rtc_wakeup_s((uint32_t)app->st.knobs.chg_keepalive_s);
    hal_wake_t w = hal_power_stop2();
    (void)hal_clock_set_plan((hal_clock_plan_t)app->st.knobs.clock_plan);
    app->stops++;
    app->last_wake = (uint32_t)w;
    if (w == HAL_WAKE_RTC)
        service_charger(app, 1u);                /* keep-alive inside the 160 s charger watchdog, then back to Stop 2 */
    else if (w == HAL_WAKE_CHG_INT)
        fw_event(&app->st, FW_EV_CHG_INT, 0, hal_time_us());
}

static void service_charger(fw_app_t *app, uint32_t force)
{
    uint32_t tv = 0u;
    int32_t t = 0;
    if (app->st.vbus) {                          /* TS is meaningful only with VIN present (SLUSE99C Table 8-6) */
        uint16_t mv = 0u;
        if (hal_adc_read_mv(HAL_ADC_TS, &mv) == HAL_OK) {
            t = fw_chg_ts_temp_c10(mv);
            tv = t > -400 && t < 1000 ? 1u : 0u;
        }
    }
    uint32_t cls = tv ? (t >= 200 ? 1u : 0u) : 2u;
    if (cls != app->chg_temp_class) {
        app->chg_temp_class = cls;
        force = 1u;
    }
    fw_chg_plan_t p = fw_chg_plan(&app->st.knobs, app->st.usb_enumerated, app->st.usb_suspended, tv, t);
    if (app->dfu_prep)
        p.want[0x07] = (uint8_t)((p.want[0x07] & ~0x03u) | 0x03u);   /* WATCHDOG_SEL 11: the ROM loader never talks I2C (sub-dock-usb DFU path 3) */
    app->chg_ok = fw_chg_service(&app->chg, &app->st.knobs, &p, hal_time_us(), force);
}

/* FWSIM-R28: USB core and pins only while PA1 shows VBUS; CDC bytes reassembled into frames, each answered (ACK/NACK). Every drive
 * a frame can cause goes through fw_ccr_from_amp (FWSIM-R64) in fw_hop / fw_selftest_hop. */
static void service_usb(fw_app_t *app, uint32_t pa1)
{
    if (pa1 != app->usb_on) {
        if (hal_usb_enable(pa1 != 0u) == HAL_OK || !pa1)
            app->usb_on = pa1;
        fw_cdc_frame_init(&app->cdc);
    }
    uint32_t cfg = app->usb_on ? (uint32_t)hal_usb_bus() : 0u;
    if (cfg != app->usb_cfg) {                   /* enumeration / suspend / reset: charger input follows at once */
        app->usb_cfg = cfg;
        fw_event(&app->st, FW_EV_USB_ENUMERATED, (int32_t)cfg, hal_time_us());
        service_charger(app, 1u);
    }
    if (!app->usb_on)
        return;
    uint8_t rx[64];
    size_t n = hal_usb_cdc_read(rx, sizeof rx), used = 0u;
    while (used < n) {
        size_t flen = 0u;
        used += fw_cdc_frame_push(&app->cdc, &rx[used], n - used, hal_time_us(), &flen);
        if (flen) {
            uint8_t rep[4];
            size_t r = fw_cdc_rx(&app->st, app->cdc.buf, flen, rep, sizeof rep);
            app->cdc_replies += (uint32_t)hal_usb_cdc_write(rep, r);
        }
    }
}

/* FWSIM-R21 DFU handoff. DFU_PENDING is reachable only from DOCKED_CHARGE (fsm.yaml): no output path is live. After FW_DFU_SETTLE_US (the
 * ACK leaves on CDC) the guards are re-checked; all must hold, else DFU_ABORT back to charging (counted):
 *   bridge off and break disarmed; PA1 VBUS present; USB configured (a host is there to run DFU); charger plan verified and no fault.
 * Then: charger plan re-written with WATCHDOG_SEL = 11 and verified (the ROM loader never services I2C; a 160 s watchdog reset mid-update
 * would drop the plan), mic and LED off, USB soft-disconnect (the host re-enumerates the ROM's DFU device), hal_usb_dfu_request. */
#define FW_DFU_SETTLE_US 50000u
static void service_dfu(fw_app_t *app)
{
    if (app->dfu_handoffs)
        return;                                  /* the request returned: only the host fake does that */
    if (app->st.sys.mode != (uint32_t)FW_ST_DFU_PENDING) {
        app->dfu_since_us = 0u;
        if (app->dfu_prep) {                     /* left DFU_PENDING (unplug, fault): watchdog back on */
            app->dfu_prep = 0u;
            service_charger(app, 1u);
        }
        return;
    }
    uint64_t now = hal_time_us();
    if (app->dfu_since_us == 0u)
        app->dfu_since_us = now;
    if (now - app->dfu_since_us < FW_DFU_SETTLE_US)
        return;
    uint32_t ok = !app->bridge_on && hal_usb_vbus() && app->usb_cfg == (uint32_t)HAL_USB_BUS_CONFIGURED && app->chg_ok && !app->chg.fault;
    if (ok) {
        app->dfu_prep = 1u;
        service_charger(app, 1u);                /* watchdog off, read back */
        ok = app->chg_ok;
    }
    if (!ok) {
        app->dfu_refusals++;
        fw_event(&app->st, FW_EV_DFU_ABORT, 0, now);
        app->dfu_prep = 0u;
        service_charger(app, 1u);
        return;
    }
    hal_adf_stop();
    hal_gpio_write(BOARD_PIN_MIC_VDD, false);
    app->mic_on = 0u;
    (void)hal_led_set(0u);
    app->led_duty_ppm = 0u;
    (void)hal_usb_enable(false);
    app->usb_on = 0u;
    app->dfu_handoffs++;
    hal_usb_dfu_request();                       /* target: backup-register flag + reset into the ROM loader; does not return */
}

void fw_app_step(fw_app_t *app)
{
    const int32_t *hop;
    while ((hop = hal_adf_hop_take()) != NULL) {
        uint32_t c0 = hal_time_cycles();
        size_t n = fw_hop(&app->st, hop, app->ccr, FW_CCR_MAX_PER_HOP, &app->taps);
        hal_adf_hop_release();
        app->taps.cycles_hop = hal_time_cycles() - c0;
        if (n == 0u || hal_pwm_submit(app->ccr, n) != HAL_OK)
            app->submit_errors++;
        app->hops++;
    }
    /* docked if PA1 shows VBUS OR the charger reports power good (FWSIM-R19: a PA1 stuck low cannot enable docked output); a PA1 edge
     * re-reads the charger at once so a stale power-good never outlives the plug */
    uint32_t pa1 = hal_usb_vbus() ? 1u : 0u, force_chg = 0u;
    if (pa1 != app->pa1_seen) {
        app->pa1_seen = pa1;
        service_charger(app, 1u);
    }
    uint32_t vbus = (pa1 || app->chg.pgood) ? 1u : 0u;
    if (vbus != app->vbus_seen) {
        app->vbus_seen = vbus;
        fw_event(&app->st, vbus ? FW_EV_VBUS_ON : FW_EV_VBUS_OFF, 0, hal_time_us());
        force_chg = 1u;                          /* power-good change: re-assert the charger plan */
    }
    if (app->st.event_count[FW_EV_CHG_INT] != app->chg_int_seen) {   /* /INT pulse (power good, faults): re-check the plan */
        app->chg_int_seen = app->st.event_count[FW_EV_CHG_INT];
        force_chg = 1u;
    }
    service_usb(app, pa1);
    fw_poll(&app->st, hal_time_us());
    service_dfu(app);
    apply_outputs(app);
    apply_mic_led(app);
    service_charger(app, force_chg);
    hal_wdt_kick();
    if (app->st.sys.mode == (uint32_t)FW_ST_OFF && fw_sys_can_sleep(&app->st.sys))
        enter_stop2(app);
}
