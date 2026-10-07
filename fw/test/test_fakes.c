/* FWSIM-R2: every hal function has a stateful fake with scripted inputs, a call log and fault injection. */
#include <string.h>

#include "fake.h"
#include "tf.h"
#include "tests.h"

static void call_every_hal_function(void)
{
    uint16_t mv;
    uint8_t b[4] = {0};
    uint16_t ccr[4] = {100, 100, 100, 100};
    hal_pwm_cfg_t cfg = {200u, 1u, 1u, 1u};
    (void)hal_clock_set_plan(HAL_CLK_P80);
    (void)hal_clock_hclk_hz();
    (void)hal_power_stop2();
    (void)hal_power_reset_cause();
    hal_power_system_reset();
    hal_power_ucpd_dbdis();
    (void)hal_gpio_mode(BOARD_PIN_MIC_VDD, HAL_GPIO_OUTPUT_PP);
    hal_gpio_write(BOARD_PIN_MIC_VDD, true);
    (void)hal_gpio_read(BOARD_PIN_MIC_VDD);
    (void)hal_adf_start(2000000u);
    hal_adf_stop();
    (void)hal_adf_hop_take();
    hal_adf_hop_release();
    (void)hal_adf_flags();
    (void)hal_pwm_config(&cfg);
    (void)hal_pwm_start();
    hal_pwm_stop();
    (void)hal_pwm_submit(ccr, 4u);
    (void)hal_pwm_underruns();
    (void)hal_adc_read_mv(HAL_ADC_VBAT_SENSE, &mv);
    (void)hal_i2c_write(0x6Au, 0x04u, b, 1u);
    (void)hal_i2c_read(0x6Au, 0x04u, b, 1u);
    (void)hal_i2c_recover();
    (void)hal_usb_vbus();
    (void)hal_usb_enable(false);
    (void)hal_usb_cdc_write(b, 1u);
    (void)hal_usb_cdc_read(b, 1u);
    hal_usb_dfu_request();
    (void)hal_flash_erase_page(0u);
    (void)hal_flash_program_qw(0u, (const uint8_t *)"0123456789abcdef");
    (void)hal_flash_read(0u, b, 4u);
    (void)hal_wdt_start(1000u);
    hal_wdt_kick();
    (void)hal_time_us();
    (void)hal_time_cycles();
    hal_irq_restore(hal_irq_save());
    {
        int16_t c[2] = {16384, 0}, x[3] = {0, 1000, 2000}, y[2] = {0, 0};
        (void)hal_fmac_fir_bank(c, 1u, 2u, 0u, x, 2u, y);
    }
    (void)hal_brk_arm(300u);
    hal_brk_disarm();
    (void)hal_brk_latched();
    hal_brk_clear();
}

void test_fakes_coverage(void)
{
    fake_reset();
    call_every_hal_function();
    for (uint32_t f = 0; f < (uint32_t)FAKE_FN_COUNT; f++) {
        if (fake_calls((fake_fn_t)f) == 0u)
            fprintf(stderr, "  not covered: %s\n", fake_fn_name[f]);
        TF_CHECK(fake_calls((fake_fn_t)f) >= 1u);
        TF_CHECK(fake_log_find((fake_fn_t)f, 0u) >= 0);
    }
    TF_CHECK_EQ(fake_log_len(), FAKE_FN_COUNT);
    TF_CHECK_EQ(FAKE_FN_COUNT, 42);
}

void test_fakes_fault_injection(void)
{
    /* every status-returning function returns the injected error; the others degrade to their safe value */
    fake_reset();
    for (uint32_t f = 0; f < (uint32_t)FAKE_FN_COUNT; f++)
        fake_fault((fake_fn_t)f, 0u, 0xFFFFFFFFu, HAL_TIMEOUT);
    uint16_t mv = 1234;
    uint8_t b[4] = {0};
    uint16_t ccr[1] = {100};
    hal_pwm_cfg_t cfg = {200u, 1u, 1u, 1u};
    fake_vbus(true);
    TF_CHECK_EQ(hal_clock_set_plan(HAL_CLK_P160), HAL_TIMEOUT);
    TF_CHECK_EQ(hal_gpio_mode(BOARD_PIN_MIC_VDD, HAL_GPIO_OUTPUT_PP), HAL_TIMEOUT);
    TF_CHECK_EQ(hal_adf_start(2000000u), HAL_TIMEOUT);
    TF_CHECK(hal_adf_hop_take() == NULL);
    TF_CHECK_EQ(hal_pwm_config(&cfg), HAL_TIMEOUT);
    TF_CHECK_EQ(hal_pwm_start(), HAL_TIMEOUT);
    TF_CHECK_EQ(hal_pwm_submit(ccr, 1u), HAL_TIMEOUT);
    TF_CHECK_EQ(hal_adc_read_mv(HAL_ADC_TS, &mv), HAL_TIMEOUT);
    TF_CHECK_EQ(hal_i2c_write(0x6Au, 0u, b, 1u), HAL_TIMEOUT);
    TF_CHECK_EQ(hal_i2c_read(0x6Au, 0u, b, 1u), HAL_TIMEOUT);
    TF_CHECK_EQ(hal_i2c_recover(), HAL_TIMEOUT);
    TF_CHECK(!hal_usb_vbus());
    TF_CHECK_EQ(hal_usb_enable(true), HAL_TIMEOUT);
    TF_CHECK_EQ(hal_usb_cdc_write(b, 1u), 0);
    TF_CHECK_EQ(hal_usb_cdc_read(b, 1u), 0);
    TF_CHECK_EQ(hal_flash_erase_page(0u), HAL_TIMEOUT);
    TF_CHECK_EQ(hal_flash_program_qw(0u, (const uint8_t *)"0123456789abcdef"), HAL_TIMEOUT);
    TF_CHECK_EQ(hal_flash_read(0u, b, 1u), HAL_TIMEOUT);
    TF_CHECK_EQ(hal_wdt_start(10u), HAL_TIMEOUT);
    TF_CHECK_EQ(hal_power_stop2(), HAL_WAKE_NONE);
    /* windowed fault: only calls 2 and 3 fail */
    fake_fault_clear();
    fake_i2c_attach(0x6Au);
    fake_fault(FAKE_FN_hal_i2c_read, 2u, 2u, HAL_NACK);
    hal_status_t r[5];
    for (int i = 0; i < 5; i++)
        r[i] = hal_i2c_read(0x6Au, 0u, b, 1u);
    TF_CHECK_EQ(r[0], HAL_OK);
    TF_CHECK_EQ(r[1], HAL_OK);
    TF_CHECK_EQ(r[2], HAL_NACK);
    TF_CHECK_EQ(r[3], HAL_NACK);
    TF_CHECK_EQ(r[4], HAL_OK);
}

void test_fakes_state(void)
{
    fake_reset();
    /* time + cycles at the clock plan */
    fake_time_set_us(1000u);
    TF_CHECK_EQ(hal_time_us(), 1000);
    TF_CHECK_EQ(hal_time_cycles(), 80000u);
    TF_CHECK_EQ(hal_clock_hclk_hz(), 80009000u);
    /* scripted ADC sequence, last value repeats */
    uint16_t seq[3] = {1800, 1810, 1820}, mv = 0;
    fake_adc_script(HAL_ADC_VBAT_SENSE, seq, 3u);
    for (int i = 0; i < 5; i++) {
        TF_CHECK_EQ(hal_adc_read_mv(HAL_ADC_VBAT_SENSE, &mv), HAL_OK);
        TF_CHECK_EQ(mv, seq[i < 3 ? i : 2]);
    }
    /* GPIO: inputs from the script, outputs read back */
    fake_gpio_input(BOARD_PIN_BTN, true);
    TF_CHECK(hal_gpio_read(BOARD_PIN_BTN));
    TF_CHECK_EQ(hal_gpio_mode(BOARD_PIN_MIC_VDD, HAL_GPIO_OUTPUT_PP), HAL_OK);
    hal_gpio_write(BOARD_PIN_MIC_VDD, true);
    TF_CHECK(fake_gpio_output(BOARD_PIN_MIC_VDD));
    TF_CHECK(hal_gpio_read(BOARD_PIN_MIC_VDD));
    TF_CHECK_EQ(fake_gpio_mode_of(BOARD_PIN_GA_P), HAL_GPIO_ANALOG);   /* reset state: analog */
    /* I2C register file; absent device NACKs */
    uint8_t w[2] = {0x2C, 0x46}, rd[2] = {0, 0};
    TF_CHECK_EQ(hal_i2c_write(0x6Au, 0x03u, w, 2u), HAL_NACK);
    fake_i2c_attach(0x6Au);
    TF_CHECK_EQ(hal_i2c_write(0x6Au, 0x03u, w, 2u), HAL_OK);
    TF_CHECK_EQ(hal_i2c_read(0x6Au, 0x03u, rd, 2u), HAL_OK);
    TF_CHECK(rd[0] == 0x2C && rd[1] == 0x46);
    TF_CHECK_EQ(fake_i2c_regs(0x6Au)[4], 0x46);
    /* flash: program-once quad words, alignment */
    const uint8_t *qw = (const uint8_t *)"0123456789abcdef";
    TF_CHECK_EQ(hal_flash_program_qw(16u, qw), HAL_OK);
    TF_CHECK_EQ(hal_flash_program_qw(16u, qw), HAL_ERR);
    TF_CHECK_EQ(hal_flash_program_qw(8u, qw), HAL_EINVAL);
    TF_CHECK_EQ(hal_flash_erase_page(0u), HAL_OK);
    TF_CHECK_EQ(hal_flash_program_qw(16u, qw), HAL_OK);
    TF_CHECK_EQ(hal_flash_erase_page(2u), HAL_EINVAL);
    /* PWM: config rules (ARR >= 50, dead time >= 1), CCR above ARR rejected */
    hal_pwm_cfg_t bad = {40u, 1u, 1u, 1u}, nodt = {200u, 1u, 0u, 1u}, ok = {200u, 1u, 1u, 2u};
    TF_CHECK_EQ(hal_pwm_config(&bad), HAL_EINVAL);
    TF_CHECK_EQ(hal_pwm_config(&nodt), HAL_EINVAL);
    TF_CHECK_EQ(hal_pwm_config(&ok), HAL_OK);
    uint16_t over[2] = {100, 201};
    TF_CHECK_EQ(hal_pwm_submit(over, 2u), HAL_EINVAL);
    TF_CHECK_EQ(hal_pwm_start(), HAL_OK);
    TF_CHECK_EQ(hal_pwm_config(&ok), HAL_EINVAL);                      /* no reconfigure while running */
    TF_CHECK_EQ(hal_clock_set_plan(HAL_CLK_P160), HAL_BUSY);            /* FWSIM-R25 */
    hal_pwm_stop();
    TF_CHECK_EQ(hal_clock_set_plan(HAL_CLK_P160), HAL_OK);
    /* USB only with VBUS */
    TF_CHECK_EQ(hal_usb_enable(true), HAL_EINVAL);
    fake_vbus(true);
    TF_CHECK_EQ(hal_usb_enable(true), HAL_OK);
    fake_usb_rx((const uint8_t *)"hi", 2u);
    uint8_t buf[8];
    TF_CHECK_EQ(hal_usb_cdc_read(buf, sizeof buf), 2);
    TF_CHECK_EQ(hal_usb_cdc_write((const uint8_t *)"ok", 2u), 2);
    TF_CHECK_EQ(fake_usb_tx(buf, sizeof buf), 2);
    fake_vbus(false);
    TF_CHECK_EQ(hal_usb_cdc_write((const uint8_t *)"ok", 2u), 0);
    /* wake source + reset */
    fake_wake_source(HAL_WAKE_BUTTON);
    TF_CHECK_EQ(hal_power_stop2(), HAL_WAKE_BUTTON);
    TF_CHECK_EQ(hal_power_stop2(), HAL_WAKE_NONE);
    hal_power_system_reset();
    TF_CHECK_EQ(fake_resets(), 1);
    TF_CHECK_EQ(hal_power_reset_cause(), HAL_RESET_SOFT);
    /* log roll-over keeps the newest FAKE_LOG_CAP entries */
    for (uint32_t i = 0; i < FAKE_LOG_CAP + 10u; i++)
        hal_wdt_kick();
    TF_CHECK_EQ(fake_log_len(), FAKE_LOG_CAP);
    TF_CHECK_EQ(fake_log_at(FAKE_LOG_CAP - 1u)->fn, FAKE_FN_hal_wdt_kick);
}

void test_fakes_adf_isr_ring(void)
{
    /* the fake DMA ISR only moves a hop and pushes its index (FWSIM-R3); the ring drops (and counts) on overflow */
    fake_reset();
    int32_t hop[128];
    for (int i = 0; i < 128; i++)
        hop[i] = i << 8;
    for (int i = 0; i < 10; i++) {
        hop[0] = i << 8;
        fake_adf_script_hop(hop);
    }
    for (int i = 0; i < 10; i++)
        fake_adf_isr();
    TF_CHECK_EQ(fake_adf_ring()->dropped, 3);        /* capacity FW_RING_CAP - 1 = 7 */
    const int32_t *h = hal_adf_hop_take();
    TF_CHECK(h != NULL && h[0] == 0 && h[5] == (5 << 8));
    hal_adf_hop_release();
    int n = 1;
    while (hal_adf_hop_take() != NULL) {
        hal_adf_hop_release();
        n++;
    }
    TF_CHECK_EQ(n, 7);
    fake_adf_set_flags(HAL_ADF_FLAG_SATF | HAL_ADF_FLAG_CKABF);
    TF_CHECK_EQ(hal_adf_flags(), HAL_ADF_FLAG_SATF | HAL_ADF_FLAG_CKABF);
    TF_CHECK_EQ(hal_adf_flags(), 0);
}
