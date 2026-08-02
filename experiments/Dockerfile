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

# PIN THIS BEFORE YOU RELY ON IT.
#
# A tag can be repointed at a new image; a digest cannot. Until you
# append a digest, two people building this Dockerfile a month apart
# can get different compilers, which is exactly the thing a container
# is supposed to prevent.
#
#   docker buildx imagetools inspect debian:bookworm-slim
#
# then change the line below to:
#   FROM debian:bookworm-slim@sha256:<the digest you just saw>
#
# It is deliberately not pinned here: a digest I cannot verify is
# worse than none, because it fails to pull for reasons that look
# like your mistake rather than mine.
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libc6-dev \
        make \
        util-linux \
        systemd \
    && rm -rf /var/lib/apt/lists/* \
    && cc --version | head -1

WORKDIR /experiments
COPY common.h lab.h Makefile run-labs.sh *.c ./
RUN chmod +x run-labs.sh
RUN make all

# Default to /scratch so the common case is a bind-mounted host path.
ENV PERFBOOK_DIR=/scratch
VOLUME /scratch

CMD ["./run-labs.sh"]
