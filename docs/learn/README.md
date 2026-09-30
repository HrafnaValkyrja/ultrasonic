# Learning the device

**Level-set (owner, 2026-09-30):** RF, analogue, digital packets/data, CAD and device physics are all known ground. The gaps are the black boxes: what's inside a modern MCU, how to read one, and why a 4-layer board. Lessons are pitched there.

- `02-inside-the-chip.png`: the STM32U575 as a small network (bus masters, DMA, memory-mapped peripherals, clock tree), with one audio sample's path
- `03-four-layer-board.png`: the pod board's stack-up, vias, return paths, and why 4 layers

## Original plan (lesson 1 pitched too low; kept for reference)

Each lesson has one picture and one idea. Every later lesson builds on lesson 1.

1. **The big picture:** the journey of one bat chirp; the "two pianos" idea (`01-big-picture.png`)
2. **Hearing ultrasound:** how a 3.5 mm mic hears 40 kHz, and why it speaks in 1-bit pulses
3. **Counting:** turning pulses into numbers; why 200,000 numbers a second is enough for 85 kHz
4. **Sorting and re-singing:** splitting sound into 28 "keys" (the FFT), the log squeeze, and why whines vanish
5. **Switching:** making sound from on/off pulses (PWM), the H-bridge, and dead time
6. **Bone conduction:** why the tragus, and how vibration reaches the cochlea
7. **Power:** battery, regulators, and why current decides runtime; the idle mode
8. **The board:** every part on the render, matched to the blocks above
9. **Mechanics:** the pod, the NiTi arm, and balance on your nose and ears

Each lesson ends with a hands-on "try it" for when the parts arrive.
