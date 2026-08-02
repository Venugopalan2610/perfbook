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

BINS = 01_write_latency 03_fsync_cost 06_crc_zero_seed

.PHONY: all run clean

all: $(BINS)

%: %.c common.h
	$(CC) $(CFLAGS) -o $@ $<

run: all
	@for b in $(BINS); do ./$$b || exit 1; done

01: 01_write_latency  ; @./01_write_latency
03: 03_fsync_cost     ; @./03_fsync_cost
06: 06_crc_zero_seed  ; @./06_crc_zero_seed

clean:
	rm -f $(BINS) .perfbook_*.tmp
