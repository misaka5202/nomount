#!/bin/bash
# 校验四个 ko: vermagic 必须等于设备值, module_layout 必须等于设备 CRC。
set -uo pipefail

ROOT=/home/misaka/zram
OUT="$ROOT/kos"
EXPORT="$ROOT/kos_export"
export PATH="$ROOT/clang20/bin:$PATH"

DEVICE_KREL="6.1.157-android14-11-o-ga8ed1c96e9fd"
EXPECT_VERMAGIC="$DEVICE_KREL SMP preempt mod_unload modversions aarch64"
DEV_ML=$(awk -F'\t' '$2=="module_layout"{print $1; exit}' /mnt/c/nomount/device_symvers.txt)

echo "设备 module_layout : $DEV_ML"
echo "期望 vermagic      : $EXPECT_VERMAGIC"
echo

mkdir -p "$EXPORT"
FAIL=0

for f in "$OUT"/*.ko; do
  [ -f "$f" ] || continue
  name=$(basename "$f")
  echo "=== $name ==="

  vm=$(modinfo -F vermagic "$f" 2>/dev/null || strings "$f" | grep -m1 'vermagic=' | sed 's/vermagic=//')
  echo "  vermagic: $vm"
  if [ "$vm" = "$EXPECT_VERMAGIC" ]; then
    echo "  OK   vermagic 匹配"
  else
    echo "  FAIL vermagic 不匹配"
    FAIL=1
  fi

  ml=$(python3 /mnt/c/nomount/scripts/get_crc.py "$f" module_layout 2>/dev/null || echo 'absent')
  echo "  module_layout: $ml"
  if [ "$ml" = "$DEV_ML" ]; then
    echo "  OK   module_layout 匹配"
  else
    echo "  FAIL module_layout 不匹配"
    FAIL=1
  fi

  # __versions 段大小
  vs=$(llvm-objdump -h "$f" 2>/dev/null | awk '/__versions/{print $3; exit}')
  if [ -n "$vs" ]; then
    dec=$((16#$vs))
    echo "  __versions: $dec 字节"
    [ "$dec" -gt 0 ] || { echo "  FAIL __versions 为空"; FAIL=1; }
  else
    echo "  FAIL 无 __versions 段"
    FAIL=1
  fi

  # 注册的算法名
  reg=$(strings "$f" | grep -m1 -E '^(lz4k|lz4kd|lz4k_oplus|zstdp)$' || echo '?')
  echo "  注册名: $reg"

  # 依赖的关键符号
  echo "  依赖符号数: $(llvm-nm -u "$f" 2>/dev/null | wc -l)"

  cp -f "$f" "$EXPORT/"
  echo
done

echo "=============================================="
if [ "$FAIL" -eq 0 ]; then
  echo " 全部 ko 校验通过"
else
  echo " 存在校验失败项"
fi
echo "=============================================="
exit $FAIL
