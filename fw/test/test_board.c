/* FWSIM-R5: the generated board_config.h is self-consistent (values come from pin-contract.yaml via fw/tools/gen.py). */
#include <string.h>

#include "board_config.h"
#include "tf.h"
#include "tests.h"

static const board_pin_info_t pins[BOARD_PIN_COUNT] = BOARD_PIN_TABLE_INIT;

void test_board_config(void)
{
    TF_CHECK(BOARD_PIN_COUNT >= 25);
    for (uint32_t i = 0; i < (uint32_t)BOARD_PIN_COUNT; i++) {
        TF_CHECK(pins[i].net != NULL && pins[i].signal != NULL);
        for (uint32_t j = i + 1u; j < (uint32_t)BOARD_PIN_COUNT; j++)
            TF_CHECK(pins[i].pkg_pin != pins[j].pkg_pin);       /* one job per package pin */
        if (pins[i].port != '\0')
            TF_CHECK(pins[i].num <= 15u);
    }
    /* bridge legs: complementary pairs of one TIM1 channel on AF1 (Rev F: leg B on CH3, ECR-0003) */
    TF_CHECK(strcmp(pins[BOARD_PIN_GA_P].signal, "TIM1_CH1") == 0 && strcmp(pins[BOARD_PIN_GA_N].signal, "TIM1_CH1N") == 0);
    TF_CHECK(strcmp(pins[BOARD_PIN_GB_P].signal, "TIM1_CH3") == 0 && strcmp(pins[BOARD_PIN_GB_N].signal, "TIM1_CH3N") == 0);
    TF_CHECK_EQ(BOARD_GA_P_AF, 1);
    TF_CHECK_EQ(BOARD_GB_N_AF, 1);
    TF_CHECK_EQ(BOARD_VBAT_SENSE_ADC, 4);                       /* ADC4: runs in Stop 2 (pin-contract) */
    TF_CHECK_EQ(pins[BOARD_PIN_GB_N].hazard, 1);                /* PB15 UCPD dead battery (ECR-0013) */
}
