# STM32_open_pin_data: the files vendored here

Used by `tools/checks/interfaces.py` [pins] and described in `docs/system/pin-contract.yaml`. Data only; nothing here is code we run.

| | |
|---|---|
| Source | https://github.com/STMicroelectronics/STM32_open_pin_data (ST's own repository: "a subset of the STM32CubeMX internal database", updated at each CubeMX release) |
| Commit | `7d1f1514ed5583ec5007ad91236b4e1d377295b1`, committed 2026-06-29T16:27:37Z, message "Subset of official release STM32CubeMX 6.18.0" (head of `master`; repository last pushed 2026-06-30) |
| Retrieved | 2026-10-02T04:42Z (2026-10-02 00:42 EDT), from `raw.githubusercontent.com` at that exact commit |
| Licence | BSD-3-Clause, "Copyright (c) 2020, STMicroelectronics". GitHub's licence detection agrees (`bsd-3-clause`). Redistribution in source form is allowed provided the copyright notice, the conditions and the disclaimer are kept: the unmodified `LICENSE` file is in this directory. The files themselves are unmodified copies; each XML begins with "Copyright (c) 2025 STMicroelectronics. All rights reserved." |

| File | Path in the repository | Bytes | SHA-256 |
|---|---|---|---|
| `STM32U575CIUxQ.xml` | `mcu/STM32U575CIUxQ.xml` | 62121 | `a4860eec3cfcd317a883677a8d9d5953510e82f038461fc4030f65e670071b54` |
| `GPIO-STM32U5x_gpio_v1_0_Modes.xml` | `mcu/IP/GPIO-STM32U5x_gpio_v1_0_Modes.xml` | 318564 | `253229fd2510d58784118e5793eb54b4042cdb16951997b7a0cf8f1b5429ea49` |
| `LICENSE` | `LICENSE` | 1526 | `2e80479026d27db007f8bdd190860e4b0452ca30d622ef4c04084b064418a096` |

- `STM32U575CIUxQ.xml` is the part this pod uses (STM32U575CIU6Q: UFQFPN48, internal-SMPS pinout; `Package="UFQFPN48"`, `HasPowerPad="false"`): pin positions 1-48, each pin's name, type and every signal it can carry.
- `GPIO-STM32U5x_gpio_v1_0_Modes.xml` is the STM32U5 family GPIO file: alternate-function numbers (`GPIO_AF<n>_<peripheral>`) per pin and signal, plus EXTI line numbers. Pins with a second function in their name (PA13 `PA13 (JTMS/SWDIO)`, PB3 `PB3 (JTDO/TRACESWO)`, PC14 `PC14-OSC32_IN (PC14)`, PH3 `PH3-BOOT0`) are keyed by the full name there; the checker matches on the leading port token.
- Not in the data: electrical pin class (FT, 5 V tolerance), drive strength, and the exposed pad (pin 49). Those come from the datasheet (ST DS13737 Rev 8, read 2026-10-02: section 6.1 Table 154 note 3 puts the pad on PCB ground).

## Refresh
Replace both XML files from a newer commit, update the commit, date and hashes above, and re-run `python3 tools/checks/interfaces.py`: every contract entry is re-verified against the new data.
