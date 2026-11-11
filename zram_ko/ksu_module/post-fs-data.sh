#!/system/bin/sh
# KernelSU module post-fs-data: load every zram compressor ko.
#
# Deliberately contains no zram reconfiguration. Switching the active
# compressor is left to Scene (or manual sysfs writes) so that loading the
# modules and activating an algorithm stay separate concerns.

MODDIR=${0%/*}
LOG="/data/local/tmp/zram_algos.log"

: > "$LOG"
echo "=== zram_algos $(date) ===" >> "$LOG"
echo "kernel: $(uname -r)" >> "$LOG"

for ko in "$MODDIR"/system/lib/modules/*.ko; do
    [ -f "$ko" ] || continue
    name=$(basename "$ko")
    if out=$(insmod "$ko" 2>&1); then
        echo "[OK]   $name" >> "$LOG"
    else
        echo "[FAIL] $name: $out" >> "$LOG"
    fi
done

echo "--- loaded ---" >> "$LOG"
lsmod | grep -E 'lz4k|lz4kd|zstdp' >> "$LOG" 2>/dev/null

echo "--- zram0 available algorithms ---" >> "$LOG"
cat /sys/block/zram0/comp_algorithm >> "$LOG" 2>/dev/null
