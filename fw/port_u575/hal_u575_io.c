/* fw/port_u575/hal_u575_io.c: register layer part 2 (RM0456 Rev 7, values in reg.h): I2C2 controller (charger), ADC1 single conversions,
 * the MDF1/ADC1 side of the always-on break (FWSIM-R65), and the GPDMA burst path that feeds TIM1 (hal_pwm_submit, FWSIM-R46).
 * Host-tested against the recorded-register fake (fw/test/port, FW_REG_RECORD), whose device models drive the status flags. */
#include "board_config.h"
#include "hal.h"
#include "reg.h"

#define POLL_MAX 20000u                     /* bounded busy-waits: a stuck flag returns HAL_TIMEOUT, never hangs */

void u575_tim1_brk_enable(uint32_t on);
uint16_t u575_pwm_arr(void);

static hal_status_t wait_set(uint32_t addr, uint32_t mask)
{
    for (uint32_t i = 0; i < POLL_MAX; i++)
        if (REG_R(addr) & mask)
            return HAL_OK;
    return HAL_TIMEOUT;
}

static hal_status_t wait_clear(uint32_t addr, uint32_t mask)
{
    for (uint32_t i = 0; i < POLL_MAX; i++)
        if (!(REG_R(addr) & mask))
            return HAL_OK;
    return HAL_TIMEOUT;
}

/* ---------------------------------------------------------------------------------------------- I2C2 (BQ25180, 100 kHz) */
#define I(o) (I2C2_BASE + (o))
#define I2C_TIMING_100K_HSI16 0x30420F13u   /* RM0456 Table 664: PRESC 3, SCLDEL 4, SDADEL 2, SCLH 0x0F, SCLL 0x13 */
static uint32_t i2c_up;

static hal_status_t i2c_init(void)
{
    REG_SET(RCC_CR, 1u << 8);                                    /* HSION: I2C2 kernel clock HSI16 (also works in Stop 0/1) */
    if (wait_set(RCC_CR, 1u << 10) != HAL_OK)                    /* HSIRDY */
        return HAL_TIMEOUT;
    REG_MOD(RCC_CCIPR1, 3u << 12, 2u << 12);                     /* I2C2SEL = 10 HSI16 */
    REG_SET(RCC_APB1ENR1, 1u << 22);                             /* I2C2EN */
    (void)hal_gpio_mode(BOARD_PIN_I2C_SCL, HAL_GPIO_AF);
    (void)hal_gpio_mode(BOARD_PIN_I2C_SDA, HAL_GPIO_AF);
    REG_SET(GPIO_BASE(BOARD_I2C_SCL_PORT - 'A') + GPIO_OTYPER, 1u << BOARD_I2C_SCL_PIN);   /* open drain (R15/R16 pull-ups) */
    REG_SET(GPIO_BASE(BOARD_I2C_SDA_PORT - 'A') + GPIO_OTYPER, 1u << BOARD_I2C_SDA_PIN);
    REG_W(I(I2C_CR1), 0u);                                       /* PE = 0 while timing is written */
    REG_W(I(I2C_TIMINGR), I2C_TIMING_100K_HSI16);
    REG_W(I(I2C_CR1), 1u);                                       /* PE */
    i2c_up = 1u;
    return HAL_OK;
}

static hal_status_t i2c_wait(uint32_t mask)
{
    for (uint32_t i = 0; i < POLL_MAX; i++) {
        uint32_t isr = REG_R(I(I2C_ISR));
        if (isr & (1u << 4)) {                                   /* NACKF: AUTOEND / hardware sends STOP */
            (void)wait_set(I(I2C_ISR), 1u << 5);
            REG_W(I(I2C_ICR), (1u << 4) | (1u << 5));
            return HAL_NACK;
        }
        if (isr & mask)
            return HAL_OK;
    }
    return HAL_TIMEOUT;
}

static uint32_t cr2(uint8_t addr7, uint32_t nbytes, uint32_t rd, uint32_t autoend)
{
    return ((uint32_t)addr7 << 1) | (rd << 10) | (nbytes << 16) | (autoend << 25) | (1u << 13);
}

hal_status_t hal_i2c_write(uint8_t addr7, uint8_t reg, const uint8_t *buf, size_t len)
{
    if ((buf == NULL && len) || len > 254u)
        return HAL_EINVAL;
    if (!i2c_up && i2c_init() != HAL_OK)
        return HAL_TIMEOUT;
    REG_W(I(I2C_CR2), cr2(addr7, 1u + (uint32_t)len, 0u, 1u));
    hal_status_t e = i2c_wait(1u << 1);                          /* TXIS */
    if (e != HAL_OK)
        return e;
    REG_W(I(I2C_TXDR), reg);
    for (size_t i = 0; i < len; i++) {
        if ((e = i2c_wait(1u << 1)) != HAL_OK)
            return e;
        REG_W(I(I2C_TXDR), buf[i]);
    }
    if ((e = i2c_wait(1u << 5)) != HAL_OK)                       /* STOPF */
        return e;
    REG_W(I(I2C_ICR), 1u << 5);
    return HAL_OK;
}

hal_status_t hal_i2c_read(uint8_t addr7, uint8_t reg, uint8_t *buf, size_t len)
{
    if (buf == NULL || len == 0u || len > 255u)
        return HAL_EINVAL;
    if (!i2c_up && i2c_init() != HAL_OK)
        return HAL_TIMEOUT;
    REG_W(I(I2C_CR2), cr2(addr7, 1u, 0u, 0u));                   /* write the register pointer, no STOP */
    hal_status_t e = i2c_wait(1u << 1);
    if (e != HAL_OK)
        return e;
    REG_W(I(I2C_TXDR), reg);
    if ((e = i2c_wait(1u << 6)) != HAL_OK)                       /* TC */
        return e;
    REG_W(I(I2C_CR2), cr2(addr7, (uint32_t)len, 1u, 1u));        /* repeated START, read len, AUTOEND */
    for (size_t i = 0; i < len; i++) {
        if ((e = i2c_wait(1u << 2)) != HAL_OK)                   /* RXNE */
            return e;
        buf[i] = (uint8_t)REG_R(I(I2C_RXDR));
    }
    if ((e = i2c_wait(1u << 5)) != HAL_OK)
        return e;
    REG_W(I(I2C_ICR), 1u << 5);
    return HAL_OK;
}

hal_status_t hal_i2c_recover(void)
{
    REG_W(I(I2C_CR1), 0u);                                       /* PE = 0 resets the I2C state machine and flags */
    i2c_up = 0u;
    return i2c_init();                                           /* [T] 9-clock bus clear via GPIO when SDA is held low (bring-up) */
}

/* ---------------------------------------------------------------------------------------------- ADC1 */
#define A(o) (ADC1_BASE + (o))
static uint32_t adc_up, brk_armed;

static hal_status_t adc_init(void)
{
    REG_SET(RCC_AHB2ENR1, AHB2EN_ADC12);
    REG_CLR(A(ADC_CR), 1u << 29);                                /* DEEPPWD = 0 (reset 1) */
    REG_SET(A(ADC_CR), 1u << 28);                                /* ADVREGEN */
    if (wait_set(A(ADC_ISR), 1u << 12) != HAL_OK)                /* LDORDY */
        return HAL_TIMEOUT;
    REG_SET(A(ADC_CR), 1u << 31);                                /* ADCAL (offset) */
    if (wait_clear(A(ADC_CR), 1u << 31) != HAL_OK)
        return HAL_TIMEOUT;
    REG_W(A(ADC_ISR), 1u);                                       /* clear ADRDY (rc_w1) */
    REG_SET(A(ADC_CR), 1u);                                      /* ADEN */
    if (wait_set(A(ADC_ISR), 1u) != HAL_OK)                      /* ADRDY */
        return HAL_TIMEOUT;
    adc_up = 1u;
    return HAL_OK;
}

static void adc_channel(uint32_t ch, uint32_t smp)
{
    REG_W(A(ADC_PCSEL), 1u << ch);
    if (ch < 10u)
        REG_MOD(A(ADC_SMPR1), 7u << (3u * ch), smp << (3u * ch));
    else
        REG_MOD(A(ADC_SMPR2), 7u << (3u * (ch - 10u)), smp << (3u * (ch - 10u)));
    REG_W(A(ADC_SQR1), ch << 6);                                 /* L = 0 (one conversion), SQ1 = ch */
}

hal_status_t hal_adc_read_mv(hal_adc_ch_t ch, uint16_t *mv)
{
    static const int8_t adc1_ch[HAL_ADC_CH_COUNT] = {11, -1, 6, 7, 0};   /* I_SENSE IN11, VBAT on ADC4 (not here), VBUS IN6, TS IN7, VREFINT IN0 */
    if (mv == NULL || (uint32_t)ch >= (uint32_t)HAL_ADC_CH_COUNT)
        return HAL_EINVAL;
    *mv = 0u;
    if (adc1_ch[ch] < 0)
        return HAL_ENOTIMPL;                                     /* ADC4 (VBAT_SENSE PA4, ADC4_IN9): next layer */
    if (brk_armed)
        return HAL_BUSY;                                         /* FWSIM-R65: ADC1 streams I_SENSE to MDF1 while the break is armed */
    if (!adc_up && adc_init() != HAL_OK)
        return HAL_TIMEOUT;
    REG_W(A(ADC_CFGR1), 0u);                                     /* DR only, 14 bit, single */
    adc_channel((uint32_t)adc1_ch[ch], 7u);                      /* longest sampling time: high-impedance dividers */
    REG_SET(A(ADC_CR), 1u << 2);                                 /* ADSTART */
    if (wait_set(A(ADC_ISR), 1u << 2) != HAL_OK)                 /* EOC */
        return HAL_TIMEOUT;
    uint32_t code = REG_R(A(ADC_DR)) & 0x3FFFu;
    *mv = (uint16_t)((code * 3000u + 8191u) / 16383u);           /* VREF+ = VDDA = 3.0 V [A: VREFINT correction later] */
    return HAL_OK;
}

/* ---------------------------------------------------------------------------------------------- break: ADC1 -> MDF1 OLD -> TIM1 */
#define M(o) (MDF1_BASE + (o))
#define ISENSE_UV_PER_MA 100u               /* R21 0.1 ohm shunt, no amplifier (sub-output.md): 0.1 mV per mA */

hal_status_t hal_brk_arm(uint32_t threshold_ma)
{
    if (!adc_up && adc_init() != HAL_OK)
        return HAL_TIMEOUT;
    /* threshold in 14-bit ADC codes at VREF+ 3.0 V; the OLD sees the ADC data through ACIC FastSinc, decimation 1 (gain 1) */
    uint32_t code = (threshold_ma * ISENSE_UV_PER_MA * 16383u + 1500000u) / 3000000u;
    REG_W(A(ADC_CFGR1), 2u | (1u << 13));                       /* DMNGT = 10 (MDF), CONT = 1, 14 bit */
    adc_channel(11u, 2u);                                        /* I_SENSE IN11, short sample: fast over-current response */
    REG_SET(RCC_AHB1ENR, 1u << 3);                               /* MDF1EN */
    REG_SET(M(MDF_CKGCR), 1u);                                   /* CKGDEN */
    REG_CLR(M(MDF_OLD0CR), 1u);                                  /* OLDEN = 0, then wait OLDACTIVE = 0 (RM0456 OLD activation sequence) */
    if (wait_clear(M(MDF_OLD0CR), 1u << 31) != HAL_OK)
        return HAL_TIMEOUT;
    REG_W(M(MDF_DFLT0CICR), 2u);                                 /* DATSRC = 10: ADCITF1 (ADC1); CICMOD 000 (split: ACIC used by the OLD) */
    REG_W(M(MDF_OLD0THLR), (0u - code) & 0x03FFFFFFu);           /* window +-code (both signs), 26-bit two's complement */
    REG_W(M(MDF_OLD0THHR), code);
    REG_W(M(MDF_OLD0CR), (1u << 4));                             /* BKOLD = 0001 (mdf_break0), ACICN 00 FastSinc, ACICD 0, THINB 0 */
    REG_SET(M(MDF_OLD0CR), 1u);                                  /* OLDEN */
    REG_SET(A(ADC_CR), 1u << 2);                                 /* ADSTART: continuous I_SENSE stream */
    u575_tim1_brk_enable(1u);
    brk_armed = 1u;
    return HAL_OK;
}

void hal_brk_disarm(void)
{
    u575_tim1_brk_enable(0u);
    REG_CLR(M(MDF_OLD0CR), 1u);
    REG_SET(A(ADC_CR), 1u << 4);                                 /* ADSTP */
    (void)wait_clear(A(ADC_CR), 1u << 2);
    REG_W(A(ADC_CFGR1), 0u);
    brk_armed = 0u;
}

/* ---------------------------------------------------------------------------------------------- GPDMA -> TIM1 DMAR bursts */
/* Each TIM1 update request moves 3 words to DMAR: CCR1, CCR2 (unused, 0), CCR3 = ARR - CCR1 (leg B complement), DCR DBA = CCR1, DBL = 2
 * (FWSIM design_binding Rev F). Ring of 2 hops; the channel runs one block per submit (ping-pong by buffer index). */
static uint32_t burst[2][FW_BURST_WORDS];
static uint32_t next_buf, underruns, dma_up;

hal_status_t hal_pwm_submit(const uint16_t *ccr, size_t n)
{
    uint16_t arr = u575_pwm_arr();
    if (ccr == NULL || n == 0u || n * 3u > FW_BURST_WORDS || arr == 0u)
        return HAL_EINVAL;
    uint32_t *b = burst[next_buf];
    for (size_t i = 0; i < n; i++) {
        uint32_t c = ccr[i] > arr ? arr : ccr[i];
        b[3u * i] = c;
        b[3u * i + 1u] = 0u;
        b[3u * i + 2u] = (uint32_t)arr - c;
    }
    uint32_t ccr_reg = REG_R(DMA_REG(DMA_CCR));
    if ((ccr_reg & 1u) && !(REG_R(DMA_REG(DMA_CSR)) & 1u))
        return HAL_BUSY;                                         /* previous block still running (not IDLE): the port retries next hop */
    if (!dma_up) {
        dma_up = 1u;
        REG_SET(RCC_AHB1ENR, 1u);                                /* GPDMA1EN (first use) */
        REG_W(TIM1_BASE + TIM_DCR, (TIM_CCR1 / 4u) | (2u << 8)); /* DBA = 13 (CCR1), DBL = 2: 3 transfers per update */
        REG_SET(TIM1_BASE + TIM_DIER, 1u << 8);                  /* UDE */
    }
    REG_W(DMA_REG(DMA_CFCR), (1u << 8) | (1u << 9));             /* clear TCF, HTF */
    REG_W(DMA_REG(DMA_CTR1), 2u | (1u << 3) | (2u << 4) | (2u << 16) | (2u << 20));   /* word src, SINC, burst 3; word dst, no DINC, burst 3 */
    REG_W(DMA_REG(DMA_CTR2), 46u);                               /* REQSEL = tim1_upd_dma (RM0456 Table 137) */
    REG_W(DMA_REG(DMA_CBR1), (uint32_t)n * 12u);                 /* bytes */
    REG_W(DMA_REG(DMA_CSAR), (uint32_t)(uintptr_t)b);
    REG_W(DMA_REG(DMA_CDAR), TIM1_BASE + TIM_DMAR);
    REG_W(DMA_REG(DMA_CCR), 1u);                                 /* EN */
    next_buf ^= 1u;
    return HAL_OK;
}

uint32_t hal_pwm_underruns(void) { return underruns; }

#if defined(FW_REG_RECORD)
const uint32_t *u575_burst_buf(uint32_t i) { return burst[i & 1u]; }   /* host test: the 64-bit source address cannot go through CSAR */
#endif
