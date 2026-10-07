/* The portable main loop on the fakes: boot order, hop -> fw_hop -> TIM1 submit, VBUS events, watchdog. */
#include "app.h"
#include "fake.h"
#include "tf.h"
#include "tests.h"

void test_app_loop(void)
{
    static fw_app_t app;
    fake_reset();
    fake_time_set_us(500u);
    fw_app_boot(&app);
    TF_CHECK(app.store.events & FW_STORE_EV_EMPTY);
    TF_CHECK_EQ(app.st.event_count[FW_EV_KNOBS_DEFAULTED], 1);
    /* UCPD dead-battery release comes before any PWM configuration (ECR-0013, FWSIM-R41 rule) */
    int32_t i_ucpd = fake_log_find(FAKE_FN_hal_power_ucpd_dbdis, 0u), i_pwm = fake_log_find(FAKE_FN_hal_pwm_config, 0u);
    TF_CHECK(i_ucpd >= 0 && i_pwm > i_ucpd);
    TF_CHECK_EQ(fake_pwm()->arr, 200);
    TF_CHECK_EQ(fake_pwm()->rcr, 1);
    TF_CHECK(fake_pwm()->dtg_rise >= 1u);
    int32_t hop[128] = {0};
    for (int i = 0; i < 3; i++)
        fake_adf_script_hop(hop);
    for (int i = 0; i < 3; i++)
        fake_adf_isr();
    fw_app_step(&app);
    TF_CHECK_EQ(app.hops, 3);
    TF_CHECK_EQ(app.submit_errors, 0);
    TF_CHECK_EQ(fake_pwm_hops(), 3);
    size_t n;
    const uint16_t *c = fake_pwm_last(&n);
    TF_CHECK_EQ(n, 128);
    TF_CHECK_EQ(c[0], 100);
    TF_CHECK_EQ(c[127], 100);
    TF_CHECK_EQ(fake_calls(FAKE_FN_hal_adf_hop_release), 3);
    TF_CHECK(fake_wdt_kicks() >= 1u);
    /* VBUS edge -> event; power-on hold releases with injected time */
    fake_vbus(true);
    fake_time_advance_us(400000u);
    fw_app_step(&app);
    TF_CHECK_EQ(app.st.vbus, 1);
    TF_CHECK_EQ(app.st.squelched, 0);
    fake_vbus(false);
    fw_app_step(&app);
    TF_CHECK_EQ(app.st.vbus, 0);
    TF_CHECK_EQ(app.st.event_count[FW_EV_VBUS_ON], 1);
    TF_CHECK_EQ(app.st.event_count[FW_EV_VBUS_OFF], 1);
    /* a TIM1 submit error is counted, never fatal */
    fake_fault(FAKE_FN_hal_pwm_submit, 0u, 1u, HAL_BUSY);
    fake_adf_script_hop(hop);
    fake_adf_isr();
    fw_app_step(&app);
    TF_CHECK_EQ(app.submit_errors, 1);
}
