#!/usr/bin/env bash
# Commit to a number, then measure it.
#
# The book's Design Note in chapter 1 argues that instrumentation
# without a prediction has no failure condition: every result looks
# interesting, nothing is surprising, and you learn very little because
# nothing you believed was ever at risk.
#
# So this asks first. It writes your guesses into results.json next to
# what actually happened, which means the artifact records not just
# what your machine did but what you expected it to do.
#
#   ./predict.sh

set -uo pipefail

DIR="${PERFBOOK_DIR:-$(pwd)}"
OUT="${PERFBOOK_RESULTS:-results.json}"
PRED=$(mktemp)
trap 'rm -f "$PRED"' EXIT

ask() {           # ask <key> <prompt> <hint>
  local key="$1" prompt="$2" hint="$3" answer=""
  echo
  echo "$prompt"
  echo "   ($hint)"
  # Prefer the terminal so this still prompts when output is piped,
  # but fall back to stdin so it can be driven non-interactively.
  if [ -r /dev/tty ] && [ -t 1 ]; then
    read -r -p "   your answer: " answer </dev/tty || answer=""
  else
    printf '   your answer: '
    read -r answer || answer=""
    echo "$answer"
  fi
  [ -z "$answer" ] && answer="(no prediction)"
  printf '%s\t%s\n' "$key" "$answer" >> "$PRED"
}

cat <<'INTRO'
============================================================
 Predict, then measure.

 Four questions. Write down a number for each before anything
 runs. Being wrong by 10x is the normal outcome and it is the
 entire point: a prediction you cannot fail teaches nothing.

 Press enter to skip any of them.
============================================================
INTRO

ask fsync_8b \
  "1. On YOUR device, how long does write()+fsync() of 8 bytes take?" \
  "the book's axiom for NVMe is ~100 us; consumer drives are often slower"

ask cost_ratio \
  "2. Going from an 8 B payload to 8 MB is 1,048,576x more data. How many times more expensive is the fsync?" \
  "answer as a multiplier, e.g. 3 means 3x slower"

ask sigkill_bytes \
  "3. A process fwrite()s 65536 bytes, then is SIGKILLed before any fflush. How many bytes are in the file?" \
  "a number between 0 and 65536"

ask groupcommit \
  "4. At a low arrival rate, how much worse is a fixed 64-record batch than adaptive batching, on ack latency?" \
  "answer as a multiplier"

echo
echo "Locked in. Running the labs now."
echo

PERFBOOK_DIR="$DIR" PERFBOOK_RESULTS="$OUT" ./run-labs.sh
rc=$?

python3 - "$OUT" "$PRED" <<'PY'
import json, re, sys

results_path, pred_path = sys.argv[1], sys.argv[2]

# results.json is one JSON object per record, pretty-printed.
raw = open(results_path).read()
objs, depth, start = [], 0, None
for i, ch in enumerate(raw):
    if ch == '{':
        if depth == 0: start = i
        depth += 1
    elif ch == '}':
        depth -= 1
        if depth == 0 and start is not None:
            try: objs.append(json.loads(raw[start:i+1]))
            except Exception: pass
            start = None

observed = {}
for o in objs:
    for c in o.get("checks", []):
        observed[c["id"]] = c["observed"]

def num(s):
    m = re.search(r'-?\d+(?:\.\d+)?', s or '')
    return float(m.group()) if m else None

MAP = {
    "fsync_8b":      ("measuring-real-storage",           "8 B fsync"),
    "cost_ratio":    ("cost-is-not-bandwidth-bound",      "cost multiplier for 1,048,576x data"),
    "sigkill_bytes": ("userspace-buffer-dies",            "bytes surviving SIGKILL"),
    "groupcommit":   ("fixed-count-collapses-at-low-load","fixed vs adaptive at low load"),
}

preds = {}
for line in open(pred_path):
    k, _, v = line.rstrip("\n").partition("\t")
    preds[k] = v

print()
print("=" * 60)
print(" prediction vs measurement")
print("=" * 60)
for key, (cid, label) in MAP.items():
    p = preds.get(key, "(no prediction)")
    o = observed.get(cid)
    if o is None:
        print(f"\n {label}\n   predicted {p}\n   measured  (lab did not run)")
        continue
    print(f"\n {label}")
    print(f"   predicted {p}")
    print(f"   measured  {o}")
    pn, on = num(p), num(o)
    if pn is not None and on is not None and pn > 0 and on > 0:
        f = max(pn, on) / min(pn, on)
        verdict = "within 2x" if f < 2 else ("off by %.0fx" % f)
        print(f"   {verdict}")
    elif pn is not None and on is not None and pn == on:
        print("   exact")

print()
print(" A prediction you got wrong by 10x is worth more than three")
print(" you got right. Write down why before you move on.")
print()
PY

exit $rc
