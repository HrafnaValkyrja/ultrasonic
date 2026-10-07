/* fw/port_u575/usb/stm32u5xx.h: the few CMSIS device names TinyUSB's dwc2_stm32.h uses, so no ST header is vendored.
 * Values: OTG_FS base 0x4204 0000 (RM0456 Rev 7 memory map), OTG_FS IRQ 73 (RM0456 Rev 7 NVIC table, vector 0x164),
 * NVIC_ISER/ICER at 0xE000E100 / 0xE000E180 (Armv8-M ARM). */
#ifndef FW_STM32U5XX_SHIM_H
#define FW_STM32U5XX_SHIM_H
#include <stdint.h>
#define USB_OTG_FS 1
#define USB_OTG_FS_BASE 0x42040000u
typedef enum { OTG_FS_IRQn = 73 } IRQn_Type;
extern uint32_t SystemCoreClock;                          /* kept equal to hal_clock_hclk_hz() by hal_u575_usb.c */
static inline void NVIC_EnableIRQ(IRQn_Type n) { ((volatile uint32_t *)0xE000E100u)[(uint32_t)n >> 5] = 1u << ((uint32_t)n & 31u); }
static inline void NVIC_DisableIRQ(IRQn_Type n)
{
    ((volatile uint32_t *)0xE000E180u)[(uint32_t)n >> 5] = 1u << ((uint32_t)n & 31u);
    __asm volatile("dsb\n isb" ::: "memory");
}
#define __NOP() __asm volatile("nop")
#endif
