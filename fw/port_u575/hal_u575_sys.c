/* fw/port_u575/hal_u575_sys.c: register layer part 3 (RM0456 Rev 7): clock plans with voltage range, EPOD booster and flash latency
 * (FWSIM-R25), the Stop 2 entry with its wake sources and the RTC wake-up timer (FWSIM-R23), ADF1 microphone input (D1 chain: CIC5 /5 +
 * RSFLT /4, A3-u575-plan.md s1.2) and the USB OTG_FS power/pin lifecycle (FWSIM-R28). Tested in fw/test/port (recorded-register fake). */
#include "board_config.h"
#include "hal.h"
#include "reg.h"

#define POLL_MAX 20000u

static hal_status_t wait_bits(uint32_t addr, uint32_t mask, uint32_t want)
{
    for (uint32_t i = 0; i < POLL_MAX; i++)
        if ((REG_R(addr) & mask) == want)
            return HAL_OK;
    return HAL_TIMEOUT;
}

/* ---------------------------------------------------------------------------------------------- clock plans */
typedef struct { uint32_t hz; uint8_t vos, boost, pll, n, r, latency; } plan_t;
/* vos: 3 = Range 1 ... 0 = Range 4 (PWR_VOSR encoding); pll 0 = MSIS 48 MHz direct; PLL input = MSIS 48.005 / 3 = 16.0017 MHz;
 * latency from RM0456 Table 54 (Range 1: <=96 MHz 2 WS, <=128 3, <=160 4; Range 2: <=90 2, <=110 3; Range 3: <=48 1, <=55 2) */
static const plan_t plans[HAL_CLK_PLAN_COUNT] = {
    [HAL_CLK_P80] = {80009000u, 2u, 1u, 1u, 20u, 4u, 2u},
    [HAL_CLK_P160] = {160018000u, 3u, 1u, 1u, 20u, 2u, 4u},
    [HAL_CLK_P64] = {64007000u, 2u, 1u, 1u, 24u, 6u, 2u},
    [HAL_CLK_P48] = {48005000u, 1u, 0u, 0u, 0u, 0u, 2u},      /* 48.005 MHz > 48: 2 WS in Range 3 */
    [HAL_CLK_P112] = {112012000u, 3u, 1u, 1u, 28u, 4u, 3u},   /* above Range 2's 110 MHz: Range 1 */
    [HAL_CLK_P104] = {104011000u, 2u, 1u, 1u, 26u, 4u, 3u},
    [HAL_CLK_P72] = {72008000u, 2u, 1u, 1u, 18u, 4u, 2u},
    [HAL_CLK_P52] = {52006000u, 1u, 0u, 1u, 13u, 4u, 2u},     /* Range 3 (<= 55 MHz): no booster */
};
static uint32_t cur_hz = 4000000u, cur_vos;   /* MSIS 4 MHz, Range 4 after reset */

uint32_t hal_clock_hclk_hz(void) { return cur_hz; }

static hal_status_t set_vos(uint32_t vos, uint32_t boost)
{
    REG_SET(RCC_AHB3ENR, 1u << 2);                               /* PWREN */
    REG_MOD(PWR_VOSR, (3u << 16) | (1u << 18), vos << 16);
    if (wait_bits(PWR_VOSR, 1u << 15, 1u << 15) != HAL_OK)       /* VOSRDY */
        return HAL_TIMEOUT;
    if (boost) {                                                 /* RM: BOOSTEN in Range 1/2 before SYSCLK > 55 MHz */
        REG_SET(PWR_VOSR, 1u << 18);
        if (wait_bits(PWR_VOSR, 1u << 14, 1u << 14) != HAL_OK)   /* BOOSTRDY */
            return HAL_TIMEOUT;
    }
    cur_vos = vos;
    return HAL_OK;
}

hal_status_t hal_clock_set_plan(hal_clock_plan_t plan)
{
    if ((uint32_t)plan >= (uint32_t)HAL_CLK_PLAN_COUNT)
        return HAL_EINVAL;
    if ((REG_R(TIM1_BASE + TIM_CR1) & 1u) || (REG_R(ADF1_BASE + ADF_DFLT0CR) & 1u))
        return HAL_BUSY;                                         /* FWSIM-R25: only with TIM1 and ADF1 stopped */
    const plan_t *p = &plans[plan];
    REG_SET(PWR_CR3, 1u << 1);                                   /* REGSEL = SMPS, never the LDO (FWSIM-R23) */
    /* MSIS range 0 (48 MHz), locked to the LSE when the LSE runs (PLL mode, A3 s2) */
    REG_MOD(RCC_ICSCR1, 0xFu << 28, (0u << 28) | (1u << 23));
    if (REG_R(RCC_BDCR) & (1u << 1))
        REG_SET(RCC_CR, (1u << CR_MSIPLLSEL) | (1u << CR_MSIPLLEN));
    REG_SET(RCC_CR, 1u << CR_MSISON);
    if (wait_bits(RCC_CR, 1u << CR_MSISRDY, 1u << CR_MSISRDY) != HAL_OK)
        return HAL_TIMEOUT;
    /* up: range (and booster) and flash latency BEFORE the clock rises */
    if (p->vos > cur_vos || p->boost) {
        if (set_vos(p->vos > cur_vos ? p->vos : cur_vos, p->boost) != HAL_OK)
            return HAL_TIMEOUT;
    }
    if ((REG_R(FLASH_ACR) & 0xFu) < p->latency)
        REG_MOD(FLASH_ACR, 0xFu, (uint32_t)p->latency | (1u << 8));
    /* SYSCLK to MSIS while PLL1 is reprogrammed */
    REG_MOD(RCC_CFGR1, 3u, 0u);
    if (wait_bits(RCC_CFGR1, 3u << 2, 0u) != HAL_OK)
        return HAL_TIMEOUT;
    REG_CLR(RCC_CR, 1u << CR_PLL1ON);
    if (wait_bits(RCC_CR, 1u << CR_PLL1RDY, 0u) != HAL_OK)
        return HAL_TIMEOUT;
    if (p->pll) {
        REG_W(RCC_PLL1CFGR, 1u | (3u << 2) | (2u << 8) | (2u << 12) | (1u << 18));   /* MSIS, 8-16 MHz, M = 3, MBOOST /4 (48 -> 12 MHz), REN */
        REG_W(RCC_PLL1DIVR, ((uint32_t)p->n - 1u) | (((uint32_t)p->r - 1u) << 24));
        REG_SET(RCC_CR, 1u << CR_PLL1ON);
        if (wait_bits(RCC_CR, 1u << CR_PLL1RDY, 1u << CR_PLL1RDY) != HAL_OK)
            return HAL_TIMEOUT;
        REG_MOD(RCC_CFGR1, 3u, 3u);
        if (wait_bits(RCC_CFGR1, 3u << 2, 3u << 2) != HAL_OK)
            return HAL_TIMEOUT;
    }
    /* down: latency and range AFTER the clock fell */
    if ((REG_R(FLASH_ACR) & 0xFu) > p->latency)
        REG_MOD(FLASH_ACR, 0xFu, p->latency);
    if (p->vos < cur_vos || !p->boost) {
        if (!p->boost)
            REG_CLR(PWR_VOSR, 1u << 18);
        if (p->vos < cur_vos)
            (void)set_vos(p->vos, 0u);
    }
    cur_hz = p->hz;
    return HAL_OK;
}

hal_status_t hal_clock_stop_prep(void)
{
    REG_CLR(RCC_CR, (1u << CR_PLL2ON) | (1u << CR_PLL3ON) | (1u << CR_HSI48ON) | (1u << CR_SHSION));
    return wait_bits(RCC_CR, (1u << CR_PLL2RDY) | (1u << CR_PLL3RDY) | (1u << CR_HSI48RDY) | (1u << CR_SHSIRDY), 0u);
}

/* ---------------------------------------------------------------------------------------------- RTC wake-up timer, Stop 2 */
hal_status_t hal_power_rtc_wakeup_s(uint32_t seconds)
{
    if (seconds > 65536u)
        return HAL_EINVAL;
    REG_SET(RCC_AHB3ENR, 1u << 2);
    REG_SET(PWR_DBPR, 1u);                                       /* backup domain writable */
    if (!(REG_R(RCC_BDCR) & (1u << 15))) {                       /* RTC clock: LSE if fitted (HAS_LSE), else LSI */
#if defined(FW_HAS_LSE) && FW_HAS_LSE == 0
        REG_SET(RCC_BDCR, 1u << 26);
        if (wait_bits(RCC_BDCR, 1u << 27, 1u << 27) != HAL_OK)
            return HAL_TIMEOUT;
        REG_MOD(RCC_BDCR, 3u << 8, 2u << 8);
#else
        REG_SET(RCC_BDCR, 1u);
        if (wait_bits(RCC_BDCR, 1u << 1, 1u << 1) != HAL_OK)
            return HAL_TIMEOUT;
        REG_MOD(RCC_BDCR, 3u << 8, 1u << 8);
#endif
        REG_SET(RCC_BDCR, 1u << 15);
    }
    REG_SET(RCC_APB3ENR, 1u << 21);                              /* RTCAPBEN */
    REG_W(RTC_WPR, 0xCAu);
    REG_W(RTC_WPR, 0x53u);
    REG_CLR(RTC_CR, (1u << 10) | (1u << 14));                    /* WUTE = 0 before WUTR */
    hal_status_t e = HAL_OK;
    if (seconds) {
        if (wait_bits(RTC_ICSR, 1u << 2, 1u << 2) != HAL_OK)     /* WUTWF */
            e = HAL_TIMEOUT;
        else {
            REG_W(RTC_WUTR, seconds - 1u);                       /* ck_spre 1 Hz: period = WUT + 1 s */
            REG_MOD(RTC_CR, 7u, 4u);                             /* WUCKSEL = 100 */
            REG_SET(RTC_CR, (1u << 10) | (1u << 14));            /* WUTE, WUTIE */
        }
    }
    REG_W(RTC_WPR, 0xFFu);                                       /* re-lock */
    return e;
}

#if defined(FW_REG_RECORD)
void u575_wfi(void);                                             /* the host test decides which wake flags the "hardware" raises */
#else
static void u575_wfi(void) { __asm volatile("dsb\n wfi\n isb"); }
#endif

hal_wake_t hal_power_stop2(void)
{
    /* wake sources: WKUP1 = PA0 (button, high level), EXTI15 = PA15 CHG_INT (falling), EXTI1 = PA1 VBUS_SENSE (rising), RTC wake-up */
    REG_SET(PWR_WUCR1, 1u);
    REG_MOD(EXTI_EXTICR1, 0xFFu << 8, 0u);                       /* line 1 <- port A */
    REG_MOD(EXTI_EXTICR4, 0xFFu << 24, 0u);                      /* line 15 <- port A */
    REG_SET(EXTI_RTSR1, 1u << 1);
    REG_SET(EXTI_FTSR1, 1u << 15);
    REG_SET(EXTI_IMR1, (1u << 1) | (1u << 15));
    REG_SET(PWR_CR3, 1u << 1);                                   /* SMPS in Stop 2 */
    REG_MOD(PWR_CR1, 7u, 2u);                                    /* LPMS = 010 Stop 2 */
    REG_SET(SCB_SCR, 1u << 2);                                   /* SLEEPDEEP */
    u575_wfi();
    REG_CLR(SCB_SCR, 1u << 2);
    cur_hz = 48005000u;                                          /* Stop exit runs on MSIS: the caller restores its clock plan */
    cur_vos = (REG_R(PWR_VOSR) >> 16) & 3u;
    hal_wake_t w = HAL_WAKE_OTHER;
    if (REG_R(PWR_WUSR) & 1u) {
        REG_W(PWR_WUSCR, 1u);
        w = HAL_WAKE_BUTTON;
    } else if (REG_R(EXTI_FPR1) & (1u << 15)) {
        REG_W(EXTI_FPR1, 1u << 15);
        w = HAL_WAKE_CHG_INT;
    } else if (REG_R(EXTI_RPR1) & (1u << 1)) {
        REG_W(EXTI_RPR1, 1u << 1);
        w = HAL_WAKE_VBUS;
    } else if (REG_R(RTC_SR) & (1u << 2)) {
        REG_W(RTC_SCR, 1u << 2);
        w = HAL_WAKE_RTC;
    }
    return w;
}

/* ---------------------------------------------------------------------------------------------- ADF1 microphone (D1) */
/* Hop ring: 3 hops of 128 words, filled back to back by a 3-node GPDMA linked list (each node reloads DAR + BR1, links to the next hop;
 * the last links to the first). The transfer-complete ISR counts filled hops. The consumer takes the oldest complete hop and releases it.
 * When the DMA is about to overwrite a hop the consumer has not taken, that hop is dropped (oldest first), counted, and the hal_adf_flags
 * report a DOVRF-style overflow (FWSIM-R46: input ring >= 3 hops). */
#define ADF_HOPS 3u
#define ADF_HOP_N 128u
typedef struct { uint32_t dar, br1, llr; } adf_lli_t;
static int32_t adf_buf[ADF_HOPS][ADF_HOP_N];
static adf_lli_t adf_lli[ADF_HOPS];
static volatile uint32_t adf_filled, adf_taken, adf_held, adf_drops, adf_sw_flags;
static uint32_t adf_running;

void u575_adf_dma_tc_isr(void)
{
    REG_W(GPDMA1_BASE + 0x80u * DMA_ADF_CH + DMA_CFCR, 1u << 8);
    adf_filled++;
    if (adf_filled - adf_taken > ADF_HOPS - 1u) {                /* the DMA now writes the oldest unconsumed hop */
        adf_drops++;
        adf_sw_flags |= HAL_ADF_FLAG_DOVRF;
        adf_taken = adf_filled - (ADF_HOPS - 1u);
        adf_held = 0u;                                           /* a hop held across this point is invalid: release is a no-op */
    }
}

const int32_t *hal_adf_hop_take(void)
{
    if (!adf_running || adf_held || adf_filled == adf_taken)
        return NULL;
    adf_held = 1u;
    return adf_buf[adf_taken % ADF_HOPS];
}

void hal_adf_hop_release(void)
{
    if (adf_held) {
        adf_held = 0u;
        adf_taken++;
    }
}

uint32_t hal_adf_flags(void)
{
    uint32_t isr = REG_R(ADF1_BASE + ADF_DFLT0ISR), f = adf_sw_flags;
    adf_sw_flags = 0u;
    if (isr & (1u << 9)) f |= HAL_ADF_FLAG_SATF;
    if (isr & (1u << 10)) f |= HAL_ADF_FLAG_CKABF;
    if (isr & (1u << 1)) f |= HAL_ADF_FLAG_DOVRF;
    if (isr & (1u << 11)) f |= HAL_ADF_FLAG_RFOVRF;
    REG_W(ADF1_BASE + ADF_DFLT0ISR, isr & ((1u << 1) | (1u << 9) | (1u << 10) | (1u << 11)));   /* rc_w1 */
    return f;
}

uint32_t u575_adf_drops(void) { return adf_drops; }

hal_status_t hal_adf_start(uint32_t cck_hz)
{
    uint32_t hz = hal_clock_hclk_hz();
    /* proc_ck = HCLK / (PROCDIV+1) >= 19.2 MHz (D1); CCK = proc_ck / (CCKDIV+1), CCKDIV+1 even (duty, A3 s1.1) */
    uint32_t procdiv = hz > 60000000u ? 2u : 1u;
    uint32_t ccdiv = (hz / procdiv + cck_hz / 2u) / (cck_hz ? cck_hz : 1u);
    if (cck_hz == 0u || ccdiv < 2u || ccdiv > 16u)
        return HAL_EINVAL;
    REG_SET(RCC_AHB3ENR, 1u << 10);                              /* ADF1EN (kernel clock = HCLK by default [T: CCIPR3 ADF1SEL]) */
    (void)hal_gpio_mode(BOARD_PIN_MIC_CLK, HAL_GPIO_AF);
    (void)hal_gpio_mode(BOARD_PIN_MIC_DATA, HAL_GPIO_AF);
    REG_W(ADF1_BASE + ADF_CKGCR, ((procdiv - 1u) << 24) | ((ccdiv - 1u) << 16) | (1u << 5) | (1u << 1) | 1u);   /* CCK0 output, enabled, dividers on */
    REG_W(ADF1_BASE + ADF_SITF0CR, (4u << 8) | (1u << 4) | 1u);  /* STH 4 (clock-absence timeout), normal SPI, CCK0, SITFEN */
    REG_W(ADF1_BASE + ADF_BSMX0CR, 0u);                          /* bs0_r (rising edge) */
    REG_W(ADF1_BASE + ADF_DFLT0CICR, (5u << 4) | (4u << 8));     /* Sinc5, /5 (MCICD 4); SCALE 0 until the bench sets it (knob adf_scale) */
    REG_W(ADF1_BASE + ADF_DFLT0RSFR, (3u << 8));                 /* RSFLT on, /4; HPF on, HPFC 3 (1.9 kHz) */
    /* GPDMA: peripheral -> memory, word, one block per hop, endless 3-node linked list (LLR: UB1 | UDA | ULL) */
    uint32_t ch = GPDMA1_BASE + 0x80u * DMA_ADF_CH;
    for (uint32_t k = 0; k < ADF_HOPS; k++) {
        adf_lli[k].dar = (uint32_t)(uintptr_t)adf_buf[k];
        adf_lli[k].br1 = ADF_HOP_N * 4u;
        adf_lli[k].llr = ((uint32_t)(uintptr_t)&adf_lli[(k + 1u) % ADF_HOPS] & 0xFFFCu) | (1u << 29) | (1u << 27) | (1u << 16);
    }
    REG_SET(RCC_AHB1ENR, 1u);
    REG_W(ch + DMA_CFCR, (1u << 8) | (1u << 9));
    REG_W(ch + 0x50u, (uint32_t)(uintptr_t)adf_lli & 0xFFFF0000u);   /* CLBAR */
    REG_W(ch + DMA_CTR1, 2u | (2u << 16) | (1u << 19));          /* word -> word, destination increment */
    REG_W(ch + DMA_CTR2, 98u);                                   /* REQSEL adf1_flt0_dma */
    REG_W(ch + DMA_CBR1, ADF_HOP_N * 4u);
    REG_W(ch + DMA_CSAR, ADF1_BASE + ADF_DFLT0DR);
    REG_W(ch + DMA_CDAR, adf_lli[0].dar);
    REG_W(ch + 0xCCu, adf_lli[0].llr);                           /* CLLR: then hop 1 */
    REG_W(ch + DMA_CCR, 1u | (1u << 8));                         /* EN, TCIE */
    adf_filled = adf_taken = adf_held = adf_drops = adf_sw_flags = 0u;
    REG_W(ADF1_BASE + ADF_DFLT0CR, (1u << 1) | 1u);              /* DMAEN, DFLTEN (async continuous) last */
    adf_running = 1u;
    return HAL_OK;
}

void hal_adf_stop(void)
{
    REG_CLR(ADF1_BASE + ADF_DFLT0CR, 3u);
    REG_CLR(ADF1_BASE + ADF_SITF0CR, 1u);
    REG_CLR(ADF1_BASE + ADF_CKGCR, (1u << 1) | 1u);              /* mic clock off */
    REG_CLR(GPDMA1_BASE + 0x80u * DMA_ADF_CH + DMA_CCR, 1u);
    adf_running = 0u;
}

/* ---------------------------------------------------------------------------------------------- USB OTG_FS lifecycle (FWSIM-R28) */
void u575_usb_core_start(void);                                  /* usb/hal_u575_usb.c (TinyUSB); the register test supplies its own */
void u575_usb_core_stop(void);
bool hal_usb_vbus(void)
{
    return hal_gpio_read(BOARD_PIN_VBUS_SENSE);                  /* PA1 divider (VBUS/2 ~ 2.5 V >= VIH) as a digital input */
}

hal_status_t hal_usb_enable(bool on)
{
    if (on) {
        if (!hal_usb_vbus())
            return HAL_EINVAL;                                   /* clock and pins only while VBUS is present (R28) */
        REG_SET(RCC_CR, 1u << CR_HSI48ON);
        if (wait_bits(RCC_CR, 1u << CR_HSI48RDY, 1u << CR_HSI48RDY) != HAL_OK)
            return HAL_TIMEOUT;
        REG_MOD(RCC_CCIPR1, 3u << 26, 0u);                       /* ICLKSEL = HSI48 */
        REG_SET(RCC_AHB3ENR, 1u << 2);
        REG_SET(PWR_SVMCR, 1u << 28);                            /* USV: VDDUSB valid */
        REG_SET(RCC_AHB2ENR1, 1u << 14);                         /* OTGEN */
        (void)hal_gpio_mode(BOARD_PIN_USB_DM, HAL_GPIO_AF);
        (void)hal_gpio_mode(BOARD_PIN_USB_DP, HAL_GPIO_AF);
        u575_usb_core_start();                                   /* TinyUSB: core reset, FDMOD, PWRDWN = 1, SDIS = 0 (usb/hal_u575_usb.c) */
    } else {
        u575_usb_core_stop();                                    /* soft disconnect (SDIS = 1) first, stack down */
        REG_CLR(OTG_BASE + OTG_GCCFG, 1u << 16);                 /* transceiver off */
        REG_CLR(RCC_AHB2ENR1, 1u << 14);
        (void)hal_gpio_mode(BOARD_PIN_USB_DM, HAL_GPIO_ANALOG);  /* PA11/PA12 analog, no pull (R28) */
        (void)hal_gpio_mode(BOARD_PIN_USB_DP, HAL_GPIO_ANALOG);
        REG_CLR(PWR_SVMCR, 1u << 28);
        REG_CLR(RCC_CR, 1u << CR_HSI48ON);
    }
    return HAL_OK;
}

/* ---------------------------------------------------------------------------------------------- DFU handoff (FWSIM-R21) */
#if defined(FW_REG_RECORD)
void u575_system_reset(void);                                    /* the test records it */
#else
static void u575_system_reset(void)
{
    __asm volatile("dsb" ::: "memory");
    REG_W(SCB_AIRCR, (0x05FAu << 16) | (1u << 2));               /* SYSRESETREQ */
    for (;;) {
    }
}
#endif

/* flag in TAMP backup register 0, then a system reset: Reset_Handler (startup.c) sees the flag before any clock or peripheral is touched,
 * clears it and jumps to the ROM loader, which enumerates USB DFU (AN2606). A clean reset keeps the loader's assumptions (MSIS, no IRQs). */
void hal_usb_dfu_request(void)
{
    REG_SET(RCC_AHB3ENR, 1u << 2);
    REG_SET(PWR_DBPR, 1u);
    REG_SET(RCC_APB3ENR, 1u << 21);                              /* RTCAPBEN: TAMP register clock */
    REG_W(TAMP_BKP0R, FW_DFU_MAGIC);
    u575_system_reset();
}
