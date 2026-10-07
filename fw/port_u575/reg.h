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
