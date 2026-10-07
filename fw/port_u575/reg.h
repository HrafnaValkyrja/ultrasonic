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
#endif
