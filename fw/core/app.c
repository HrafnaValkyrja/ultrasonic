#include "app.h"

#include "hal.h"

void fw_app_boot(fw_app_t *app)
{
    fw_knobs_t k;
    app->store = fw_store_load(&k);
    fw_init(&app->st, &k, hal_time_us());
    if (app->store.events & FW_STORE_EV_DEFAULTS)
        fw_event(&app->st, FW_EV_KNOBS_DEFAULTED, (int32_t)app->store.events, hal_time_us());
    if (app->store.events & FW_STORE_EV_CLAMPED)
        fw_event(&app->st, FW_EV_KNOBS_CLAMPED, 0, hal_time_us());
    hal_power_ucpd_dbdis();                     /* ECR-0013: release PB15/PA15 dead-battery pull-downs before PWM */
    hal_pwm_cfg_t cfg = {(uint16_t)app->st.arr, 1u, (uint8_t)app->st.knobs.dead_time_rise_ticks, (uint8_t)app->st.knobs.dead_time_fall_ticks};
    (void)hal_pwm_config(&cfg);
    (void)hal_wdt_start((uint32_t)app->st.knobs.iwdg_ms);
    app->hops = 0u;
    app->submit_errors = 0u;
    app->vbus_seen = 0u;
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
    uint32_t vbus = hal_usb_vbus() ? 1u : 0u;
    if (vbus != app->vbus_seen) {
        app->vbus_seen = vbus;
        fw_event(&app->st, vbus ? FW_EV_VBUS_ON : FW_EV_VBUS_OFF, 0, hal_time_us());
    }
    fw_poll(&app->st, hal_time_us());
    hal_wdt_kick();
}
