# Experiments for "Deriving Systems".
#
#   make            build everything
#   make run        build and run every experiment in order
#   make 01         build and run just one
#
# Choose which filesystem gets measured. This matters more than
# anything else in here: measuring /tmp on tmpfs tells you about RAM.
#
#   PERFBOOK_DIR=/mnt/nvme make run

CC     ?= cc
CFLAGS ?= -O2 -g -Wall -Wextra -std=c11

BINS = 01_write_latency 02_ladder_survival 03_fsync_cost 06_crc_zero_seed

.PHONY: all run clean

all: $(BINS)

%: %.c common.h lab.h
	$(CC) $(CFLAGS) -o $@ $<

# The lab runner: every claim checked, one diffable artifact out.
run: all
	@./run-labs.sh

01: 01_write_latency    ; @./01_write_latency
02: 02_ladder_survival ; @./02_ladder_survival
03: 03_fsync_cost     ; @./03_fsync_cost
06: 06_crc_zero_seed  ; @./06_crc_zero_seed

clean:
	rm -f $(BINS) .perfbook_*.tmp results.json
