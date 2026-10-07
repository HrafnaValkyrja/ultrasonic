# fw/bench/Makefile - V4 cycle-budget kernels (docs/research/drastic/V4-cycles.yaml)
#   make          -> out/kernels_*.lst (disassembly), out/cycles.json + out/cycles.txt, out/budget.txt
#   make test     -> host build; 256-pt real FFT checked against numpy.fft.rfft
# Run inside the memory fence (CLAUDE.md):
#   systemd-run --user --scope --quiet -p MemoryMax=3G -p MemorySwapMax=0 make -C fw/bench
CC      = arm-none-eabi-gcc
OBJDUMP = arm-none-eabi-objdump
# -std=c11 => -ffp-contract=off: separate VMUL+VADD (1+1 cycles on the M4 table) instead of VFMA (3)
# -fno-math-errno => sqrtf/floorf become VSQRT/VRINTM; -fno-tree-loop-distribute-patterns => no memset calls
CFLAGS_M33 = -O2 -mcpu=cortex-m33 -mthumb -mfpu=fpv5-sp-d16 -mfloat-abi=hard -std=c11 -Wall -Wextra \
             -fno-math-errno -fno-tree-loop-distribute-patterns
PY     ?= python3
OUT     = out
# variant name : NB (bands) : TPP (interpolator taps per phase)
VARIANTS = base:32:8 slim:16:4 hq:32:12 b28:28:8

.PHONY: all test clean
all: $(OUT)/cycles.txt $(OUT)/budget.txt

$(OUT):
	mkdir -p $(OUT)

$(OUT)/kernels_%.lst: kernels.c kernels_q15.c kernels.h Makefile | $(OUT)
	$(eval V := $(filter $*:%,$(VARIANTS)))
	$(CC) $(CFLAGS_M33) -DNB=$(word 2,$(subst :, ,$(V))) -DTPP=$(word 3,$(subst :, ,$(V))) -c kernels.c -o $(OUT)/kernels_$*.o
	$(CC) $(CFLAGS_M33) -DNB=$(word 2,$(subst :, ,$(V))) -DTPP=$(word 3,$(subst :, ,$(V))) -c kernels_q15.c -o $(OUT)/kernels_q15_$*.o
	$(OBJDUMP) -d --no-show-raw-insn $(OUT)/kernels_$*.o $(OUT)/kernels_q15_$*.o > $@

LSTS = $(foreach v,$(VARIANTS),$(OUT)/kernels_$(word 1,$(subst :, ,$(v))).lst)

$(OUT)/cycles.txt: $(LSTS) cyccount.py
	$(PY) cyccount.py $(foreach v,$(VARIANTS),$(word 1,$(subst :, ,$(v)))=$(OUT)/kernels_$(word 1,$(subst :, ,$(v))).lst:$(word 2,$(subst :, ,$(v))):$(word 3,$(subst :, ,$(v)))) --json=$(OUT)/cycles.json > $@
	cat $@

$(OUT)/budget.txt: $(OUT)/cycles.txt budget.py
	$(PY) budget.py $(OUT)/cycles.json > $@
	cat $@

test: | $(OUT)
	gcc -O2 -std=gnu11 -fno-math-errno -o $(OUT)/host_test host_test.c kernels.c -lm   # float kernels only (q15 needs ACLE)
	$(OUT)/host_test > $(OUT)/host_test.txt
	$(PY) host_test.py $(OUT)/host_test.txt

clean:
	rm -rf $(OUT)
