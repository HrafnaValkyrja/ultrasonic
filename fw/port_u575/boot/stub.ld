/* fw/port_u575/boot/stub.ld: boot stub in flash page 0 (8 KB, write-protected via FLASH_WRP1AR at production), stack in SRAM1. */
MEMORY
{
    STUB (rx)   : ORIGIN = 0x08000000, LENGTH = 8K
    SRAM1 (rwx) : ORIGIN = 0x20000000, LENGTH = 192K
}
_stub_estack = ORIGIN(SRAM1) + LENGTH(SRAM1);
ENTRY(stub_reset)
SECTIONS
{
    .stub_vectors : { KEEP(*(.stub_vectors)) } > STUB
    .text : { *(.text*) *(.rodata*) . = ALIGN(4); } > STUB
    .data : { *(.data*) } > SRAM1
    .bss (NOLOAD) : { *(.bss*) *(COMMON) } > SRAM1
    /DISCARD/ : { *(.ARM.attributes) }
}
ASSERT(SIZEOF(.data) == 0 && SIZEOF(.bss) == 0, "stub: no RAM data (there is no copy / zero loop)")
