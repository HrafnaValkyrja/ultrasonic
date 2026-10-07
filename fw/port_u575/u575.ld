/* fw/port_u575/u575.ld: STM32U575CIU6Q (2 MB flash, SRAM1 192 KB / SRAM2 64 KB / SRAM3 512 KB; RM0456 Rev 7 memory map).
 * Flash: page 0 (8 KB) = boot stub (FWSIM-R21, write-protected, separate image); application from 0x08002000;
 * last two 8 KB pages = knob store (hal_flash, FWSIM-R6). TrustZone off (TZEN = 0): non-secure aliases. */
MEMORY
{
    FLASH (rx)  : ORIGIN = 0x08002000, LENGTH = 2048K - 8K - 16K
    KNOBS (r)   : ORIGIN = 0x081FC000, LENGTH = 16K
    SRAM1 (rwx) : ORIGIN = 0x20000000, LENGTH = 192K
    SRAM3 (rwx) : ORIGIN = 0x20040000, LENGTH = 512K
}

_stack_size = 8K;   /* FWSIM-R11: worst-case stack <= 50 % of this */
_estack = ORIGIN(SRAM1) + LENGTH(SRAM1);
_knob_store = ORIGIN(KNOBS);
ENTRY(Reset_Handler)

SECTIONS
{
    .isr_vector : { KEEP(*(.isr_vector)) ASSERT(. - ADDR(.isr_vector) <= 0x300, "vector table overlaps the image header"); . = 0x300; KEEP(*(.app_header)) } > FLASH
    .text : { *(.text*) *(.rodata*) . = ALIGN(4); } > FLASH
    .ARM.exidx : { *(.ARM.exidx*) } > FLASH
    _sidata = LOADADDR(.data);
    .data : { _sdata = .; *(.data*) . = ALIGN(4); _edata = .; } > SRAM1 AT > FLASH
    _app_size = LOADADDR(.data) + SIZEOF(.data) - ORIGIN(FLASH);
    .bss (NOLOAD) : { _sbss = .; *(.bss*) *(COMMON) . = ALIGN(4); _ebss = .; } > SRAM1
    .noinit (NOLOAD) : { *(.noinit*) } > SRAM1
    .stack (NOLOAD) : { . = ALIGN(8); _sstack = .; . = . + _stack_size; } > SRAM1
    ASSERT(_sstack + _stack_size <= _estack, "SRAM1 overflow: data + bss + stack do not fit")
    /DISCARD/ : { *(.ARM.attributes) }
}
