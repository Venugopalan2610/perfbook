# A pinned toolchain, so the *code* builds identically everywhere.
#
# Read this before you trust a number that came out of it:
#
# A container pins the compiler. It does not pin the storage stack.
# Chapters 1 to 3 measure the kernel's page cache and a device's flush
# behaviour, and a container changes both:
#
#   - Writes to the container's own filesystem go through overlayfs,
#     which adds a layer the host does not have.
#   - On Docker Desktop (macOS, Windows) every container runs inside a
#     Linux VM. fsync there measures the VM's virtual disk, and often
#     its host cache, not your SSD.
#
# So: build here for a consistent toolchain, but bind-mount a real
# directory on the filesystem you actually care about and point
# PERFBOOK_DIR at it.
#
#   docker build -t perfbook-experiments .
#   docker run --rm -v /mnt/nvme/scratch:/scratch \
#              -e PERFBOOK_DIR=/scratch perfbook-experiments
#
# Every experiment prints its environment, including whether it
# detected virtualization. Check that block before comparing numbers
# with anyone.

FROM debian:bookworm-20250203-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc=4:12.2.0-3 \
        libc6-dev \
        make \
        util-linux \
        systemd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /experiments
COPY common.h Makefile *.c ./
RUN make all

# Default to /scratch so the common case is a bind-mounted host path.
ENV PERFBOOK_DIR=/scratch
VOLUME /scratch

CMD ["make", "run"]
