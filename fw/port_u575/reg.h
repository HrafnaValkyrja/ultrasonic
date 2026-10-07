/* fw/port_u575/reg.h: register access for the U575 port. On target a plain volatile access; in the host register test
 * (FW_REG_RECORD, fw/test/port) every access goes to a recorded-register fake so write sequences can be checked against RM0456 values.
 * Addresses and bitfields: STM32U5 reference manual RM0456 Rev 7 (March 2026), local text read 2026-10-07 (line refs in comments). */
#ifndef FW_PORT_U575_REG_H
#define FW_PORT_U575_REG_H
#include <stdint.h>

#if defined(FW_REG_RECORD)
void reg_write(uint32_t addr, uint32_t v);
uint32_t reg_read(uint32_t addr);
#define REG_W(a, v) reg_write((uint32_t)(a), (uint32_t)(v))
#define REG_R(a) reg_read((uint32_t)(a))
#else
#define REG_W(a, v) (*(volatile uint32_t *)(uintptr_t)(a) = (uint32_t)(v))
#define REG_R(a) (*(volatile uint32_t *)(uintptr_t)(a))
#endif
#define REG_SET(a, m) REG_W((a), REG_R(a) | (uint32_t)(m))
#define REG_CLR(a, m) REG_W((a), REG_R(a) & ~(uint32_t)(m))
#define REG_MOD(a, clr, set) REG_W((a), (REG_R(a) & ~(uint32_t)(clr)) | (uint32_t)(set))

/* memory map (RM0456 Rev 7 Table 'memory map', non-secure aliases) */
#define RCC_BASE   0x46020C00u              /* RCC 0x4602 0C00 */
#define RCC_AHB2ENR1 (RCC_BASE + 0x08Cu)    /* GPIOxEN bit = port index (A = 0) */
#define RCC_APB2ENR  (RCC_BASE + 0x0A4u)    /* bit 11 TIM1EN */
#define GPIO_BASE(port_idx) (0x42020000u + 0x400u * (uint32_t)(port_idx))   /* GPIOA 0x4202 0000 ... GPIOH 0x4202 1C00 */
#define GPIO_MODER   0x00u                  /* 00 input, 01 output, 10 AF, 11 analog; reset A 0xABFFFFFF, B 0xFFFFFEBF, else 0xFFFFFFFF */
#define GPIO_OTYPER  0x04u
#define GPIO_PUPDR   0x0Cu                  /* 00 none, 01 pull-up, 10 pull-down */
#define GPIO_IDR     0x10u
#define GPIO_BSRR    0x18u
#define GPIO_AFRL    0x20u
#define GPIO_AFRH    0x24u
#define TIM1_BASE  0x40012C00u              /* TIM1 0x4001 2C00 */
#define TIM_CR1    0x000u                   /* bit 0 CEN, bits 6:5 CMS, bit 7 ARPE */
#define TIM_CR2    0x004u                   /* bit 8 OIS1, 9 OIS1N, 12 OIS3, 13 OIS3N */
#define TIM_SR     0x010u                   /* bit 7 BIF (rc_w0) */
#define TIM_EGR    0x014u                   /* bit 0 UG */
#define TIM_CCMR1  0x018u                   /* OC1M bits 16, 6:4 (0110 PWM mode 1), OC1PE bit 3 */
#define TIM_CCMR2  0x01Cu                   /* OC3M bits 16, 6:4, OC3PE bit 3 */
#define TIM_CCER   0x020u                   /* CC1E 0, CC1NE 2, CC3E 8, CC3NE 10 */
#define TIM_PSC    0x028u
#define TIM_ARR    0x02Cu
#define TIM_RCR    0x030u
#define TIM_CCR1   0x034u
#define TIM_CCR3   0x03Cu
#define TIM_BDTR   0x044u                   /* DTG 7:0, OSSI 10, OSSR 11, BKE 12, BKP 13, MOE 15 */
#define TIM_DTR2   0x054u                   /* DTGF 7:0, DTAE 16 */
#define TIM_AF1    0x060u                   /* bit 7 BKCMP7E (tim_brk_cmp7 = mdf1_break0, RM0456 Table 541) */
#define TIM_DIER   0x00Cu                   /* bit 8 UDE */
#define TIM_DCR    0x3DCu                   /* DBA 4:0 (word offset from CR1), DBL 12:8 (transfers - 1) */
#define TIM_DMAR   0x3E0u

#define RCC_CR       (RCC_BASE + 0x000u)    /* bit 8 HSION, bit 10 HSIRDY */
#define RCC_AHB1ENR  (RCC_BASE + 0x088u)    /* bit 0 GPDMA1EN, bit 3 MDF1EN */
#define RCC_APB1ENR1 (RCC_BASE + 0x09Cu)    /* bit 22 I2C2EN */
#define RCC_CCIPR1   (RCC_BASE + 0x0E0u)    /* bits 13:12 I2C2SEL: 10 = HSI16 */
#define AHB2EN_ADC12 (1u << 10)

#define I2C2_BASE  0x40005800u              /* I2C2 0x4000 5800 */
#define I2C_CR1    0x00u                    /* bit 0 PE */
#define I2C_CR2    0x04u                    /* SADD 9:0, RD_WRN 10, START 13, STOP 14, NBYTES 23:16, AUTOEND 25 */
#define I2C_TIMINGR 0x10u                   /* Table 664 (fI2CCLK 16 MHz, Sm 100 kHz): PRESC 3, SCLDEL 4, SDADEL 2, SCLH 0x0F, SCLL 0x13 */
#define I2C_ISR    0x18u                    /* TXE 0, TXIS 1, RXNE 2, NACKF 4, STOPF 5, TC 6, BUSY 15 */
#define I2C_ICR    0x1Cu                    /* NACKCF 4, STOPCF 5 */
#define I2C_RXDR   0x24u
#define I2C_TXDR   0x28u

#define ADC1_BASE  0x42028000u              /* ADC12 0x4202 8000 (ADC1 at +0) */
#define ADC_ISR    0x00u                    /* ADRDY 0, EOC 2, OVR 4, LDORDY 12 */
#define ADC_CR     0x08u                    /* ADEN 0, ADDIS 1, ADSTART 2, ADSTP 4, ADVREGEN 28, DEEPPWD 29 (reset 1), ADCAL 31 */
#define ADC_CFGR1  0x0Cu                    /* DMNGT 1:0 (10 = MDF), RES 3:2 (00 = 14 bit), CONT 13 */
#define ADC_SMPR1  0x14u
#define ADC_SMPR2  0x18u
#define ADC_PCSEL  0x1Cu
#define ADC_SQR1   0x30u                    /* L 3:0, SQ1 10:6 */
#define ADC_DR     0x40u

#define MDF1_BASE  0x40025000u              /* MDF1 0x4002 5000; filter x block at 0x80 + 0x80 x */
#define MDF_CKGCR  0x004u                   /* bit 0 CKGDEN */
#define MDF_DFLT0CICR 0x08Cu                /* DATSRC 1:0 (10 = ADCITF1), CICMOD 6:4 */
#define MDF_OLD0CR 0x098u                   /* OLDEN 0, THINB 1, BKOLD 7:4, ACICN 13:12, ACICD 21:17, OLDACTIVE 31 */
#define MDF_OLD0THLR 0x09Cu
#define MDF_OLD0THHR 0x0A0u

#define GPDMA1_BASE 0x40020000u             /* GPDMA1 0x4002 0000; channel x registers at + 0x80 x */
#define DMA_CH     7u                       /* channel used for TIM1 bursts (0-11: no 2D needed) */
#define DMA_CFCR   0x5Cu                    /* flag clear (TCF 8, HTF 9) */
#define DMA_CSR    0x60u                    /* IDLEF 0, TCF 8, HTF 9 */
#define DMA_CCR    0x64u                    /* EN 0, RESET 1 */
#define DMA_CTR1   0x90u                    /* SDW_LOG2 1:0, SINC 3, SBL_1 9:4, DDW_LOG2 17:16, DINC 19, DBL_1 25:20 */
#define DMA_CTR2   0x94u                    /* REQSEL 6:0 (46 = tim1_upd_dma, Table 137) */
#define DMA_CBR1   0x98u                    /* BNDT 15:0 bytes */
#define DMA_CSAR   0x9Cu
#define DMA_CDAR   0xA0u
#define DMA_REG(off) (GPDMA1_BASE + 0x80u * DMA_CH + (off))
#define FW_BURST_WORDS (512u * 3u)          /* 800 kHz case: 512 periods x 3 words (FWSIM-R61) */
#endif

/* ---- round 9: clocks, power, RTC, EXTI, ADC4, ADF1, OTG_FS (RM0456 Rev 7) */
#ifndef FW_PORT_U575_REG9_H
#define FW_PORT_U575_REG9_H
#define RCC_ICSCR1   (RCC_BASE + 0x008u)    /* MSISRANGE 31:28 (0000 = 48 MHz range 0), MSIRGSEL 23 */
#define RCC_CFGR1    (RCC_BASE + 0x01Cu)    /* SW 1:0, SWS 3:2 (11 = PLL1) */
#define RCC_PLL1CFGR (RCC_BASE + 0x028u)    /* PLL1SRC 1:0 (01 MSIS), PLL1RGE 3:2 (11 = 8-16 MHz), PLL1M 11:8 (M-1), PLL1MBOOST 15:12, PLL1REN 18 */
#define RCC_PLL1DIVR (RCC_BASE + 0x034u)    /* PLL1N 8:0 (N-1), PLL1R 30:24 (R-1) */
#define RCC_AHB3ENR  (RCC_BASE + 0x094u)    /* bit 2 PWREN, bit 5 ADC4EN, bit 10 ADF1EN */
#define RCC_APB3ENR  (RCC_BASE + 0x0A8u)    /* bit 21 RTCAPBEN */
#define RCC_BDCR     (RCC_BASE + 0x0F0u)    /* LSEON 0, LSERDY 1, RTCSEL 9:8 (01 LSE, 10 LSI), RTCEN 15, LSION 26, LSIRDY 27 */
#define CR_MSISON 0u
#define CR_MSISRDY 2u
#define CR_MSIPLLEN 3u
#define CR_MSIPLLSEL 6u
#define CR_HSI48ON 12u
#define CR_HSI48RDY 13u
#define CR_SHSION 14u
#define CR_SHSIRDY 15u
#define CR_PLL1ON 24u
#define CR_PLL1RDY 25u
#define CR_PLL2ON 26u
#define CR_PLL2RDY 27u
#define CR_PLL3ON 28u
#define CR_PLL3RDY 29u

#define PWR_BASE   0x46020800u              /* PWR 0x4602 0800 */
#define PWR_CR1    (PWR_BASE + 0x00u)       /* LPMS 2:0 (010 = Stop 2) */
#define PWR_CR3    (PWR_BASE + 0x08u)       /* bit 1 REGSEL (1 = SMPS) */
#define PWR_VOSR   (PWR_BASE + 0x0Cu)       /* BOOSTEN 18, VOS 17:16 (00 R4, 01 R3, 10 R2, 11 R1), VOSRDY 15, BOOSTRDY 14; reset 0x8000 */
#define PWR_SVMCR  (PWR_BASE + 0x10u)       /* bit 28 USV */
#define PWR_WUCR1  (PWR_BASE + 0x14u)       /* bit 0 WUPEN1 */
#define PWR_DBPR   (PWR_BASE + 0x28u)       /* bit 0 DBP */
#define PWR_WUSR   (PWR_BASE + 0x44u)       /* bit 0 WUF1 */
#define PWR_WUSCR  (PWR_BASE + 0x48u)       /* bit 0 CWUF1 */
#define FLASH_ACR  0x40022000u              /* FLASH 0x4002 2000: LATENCY 3:0 (Table 54), PRFTEN 8 */
#define SCB_SCR    0xE000ED10u              /* bit 2 SLEEPDEEP (Armv8-M) */

#define RTC_BASE   0x46007800u              /* RTC 0x4600 7800 */
#define RTC_ICSR   (RTC_BASE + 0x0Cu)       /* bit 2 WUTWF */
#define RTC_WUTR   (RTC_BASE + 0x14u)       /* WUT 15:0 */
#define RTC_CR     (RTC_BASE + 0x18u)       /* WUCKSEL 2:0 (100 = ck_spre 1 Hz), WUTE 10, WUTIE 14 */
#define RTC_WPR    (RTC_BASE + 0x24u)       /* key 0xCA, 0x53 */
#define RTC_SR     (RTC_BASE + 0x50u)       /* bit 2 WUTF */
#define RTC_SCR    (RTC_BASE + 0x5Cu)       /* bit 2 CWUTF */

#define EXTI_BASE  0x46022000u              /* EXTI 0x4602 2000 */
#define EXTI_RTSR1 (EXTI_BASE + 0x000u)
#define EXTI_FTSR1 (EXTI_BASE + 0x004u)
#define EXTI_RPR1  (EXTI_BASE + 0x00Cu)
#define EXTI_FPR1  (EXTI_BASE + 0x010u)
#define EXTI_EXTICR1 (EXTI_BASE + 0x060u)   /* line 1 port select bits 15:8 [M: standard U5 layout] */
#define EXTI_EXTICR4 (EXTI_BASE + 0x06Cu)   /* line 15 port select bits 31:24 [M] */
#define EXTI_IMR1  (EXTI_BASE + 0x080u)

#define ADC4_BASE  0x46021000u              /* ADC4 0x4602 1000: ISR 0x00, CR 0x08 (ADEN 0, ADSTART 2, ADVREGEN 28, ADCAL 31), CFGR1 0x0C (RES 3:2 00 = 12 bit) */
#define ADC4_SMPR  0x14u
#define ADC4_CHSELR 0x28u                   /* CHSELRMOD 0: one bit per channel */

#define ADF1_BASE  0x46024000u              /* ADF1 0x4602 4000 */
#define ADF_CKGCR  0x004u                   /* CKGDEN 0, CCK0EN 1, CCK0DIR 5, CCKDIV 19:16, PROCDIV 30:24 */
#define ADF_SITF0CR 0x080u                  /* SITFEN 0, SCKSRC 2:1 (00 CCK0), SITFMOD 5:4 (01 normal SPI), STH 12:8 */
#define ADF_BSMX0CR 0x084u                  /* BSSEL 4:0 (00000 bs0_r) */
#define ADF_DFLT0CR 0x088u                  /* DFLTEN 0, DMAEN 1, ACQMOD 6:4 (000 async continuous), DFLTACTIVE 31 */
#define ADF_DFLT0CICR 0x08Cu                /* CICMOD 6:4 (101 Sinc5), MCICD 16:8 (4 = /5), SCALE 25:20 */
#define ADF_DFLT0RSFR 0x090u                /* RSFLTBYP 0, RSFLTD 4 (0 = /4), HPFBYP 7, HPFC 9:8 */
#define ADF_DFLT0DR 0x0F0u                  /* DR 31:8 */
#define DMA_ADF_CH 6u                       /* GPDMA1 channel for ADF1 FLT0 (REQSEL 98, Table 137) */

#define OTG_BASE   0x42040000u              /* OTG_FS 0x4204 0000 */
#define OTG_GUSBCFG 0x00Cu                  /* bit 30 FDMOD */
#define OTG_GCCFG  0x038u                   /* bit 16 PWRDWN (1 = transceiver on), bit 21 VBDEN */
#define OTG_DCTL   0x804u                   /* bit 1 SDIS */
#endif
