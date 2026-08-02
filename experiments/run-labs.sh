#!/usr/bin/env bash
# Run every lab, collect one diffable artifact, exit nonzero if any
# claim failed.
#
#   ./run-labs.sh                     measure the current directory
#   PERFBOOK_DIR=/mnt/nvme ./run-labs.sh
#
# Produces results.json. Send that file, not a screenshot: it carries
# the environment, the claims, and which ones held.

set -uo pipefail

DIR="${PERFBOOK_DIR:-$(pwd)}"
OUT="${PERFBOOK_RESULTS:-results.json}"
LABS=(02_ladder_survival 03_fsync_cost 05_group_commit 06_crc_zero_seed 01_write_latency)

command -v cc >/dev/null || { echo "no C compiler on PATH"; exit 127; }
make all >/dev/null || { echo "build failed"; exit 1; }

: > "$OUT"

# Record exactly which source produced these numbers. Without this the
# results are not attributable to a version of the code.
{
  echo "{"
  echo "  \"lab\": \"manifest\","
  echo "  \"generated\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
  echo "  \"target_dir\": \"$DIR\","
  echo "  \"compiler\": \"$(cc --version | head -1)\","
  if command -v git >/dev/null && git rev-parse --git-dir >/dev/null 2>&1; then
    echo "  \"git_commit\": \"$(git rev-parse HEAD)\","
    echo "  \"git_dirty\": $(git diff --quiet && echo false || echo true),"
  fi
  echo "  \"source_sha256\": {"
  first=1
  for f in common.h lab.h "${LABS[@]/%/.c}"; do
    [ -f "$f" ] || continue
    h=$(sha256sum "$f" | cut -c1-16)
    [ $first -eq 1 ] || echo ","
    printf '    "%s": "%s"' "$f" "$h"
    first=0
  done
  echo ""
  echo "  }"
  echo "}"
} >> "$OUT"

fail=0
for lab in "${LABS[@]}"; do
  PERFBOOK_DIR="$DIR" PERFBOOK_RESULTS="$OUT" "./$lab" || fail=$((fail+1))
done

echo "============================================================"
if [ "$fail" -eq 0 ]; then
  echo "all labs upheld their claims"
else
  echo "$fail lab(s) had a failing claim"
  echo
  echo "Before assuming the book is wrong, check the mount line in each"
  echo "environment block. tmpfs, overlayfs and a hypervisor in the path"
  echo "each break a different one of these claims, and all three are"
  echo "more likely than the arithmetic being wrong."
fi
echo "wrote $OUT"
exit "$fail"
