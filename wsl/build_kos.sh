#!/bin/bash
# 编译四个 zram 压缩算法 ko。
set -uo pipefail

ROOT=/home/misaka/zram
cd "$ROOT/common" || exit 1
export PATH="$ROOT/clang20/bin:$PATH"

FLAGS="LLVM=1 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
  CC=clang LD=ld.lld HOSTCC=clang HOSTLD=ld.lld O=out
  KCFLAGS+=-O2 KCFLAGS+=-Wno-error HOSTCFLAGS+=-Wno-error WERROR=0"

OUT="$ROOT/kos"
mkdir -p "$OUT"

# 先把符号表放到内核树根(外部模块 modpost 会读它)
cp -f out/vmlinux.symvers Module.symvers
export KBUILD_EXTRA_SYMBOLS="$PWD/out/vmlinux.symvers"

# 1) 生成四个算法模块目录
echo "=============================================="
echo " 生成模块目录"
echo "=============================================="
python3 /mnt/c/nomount/zram_ko/stage_zram_modules.py \
  "$ROOT/algos/sukisu" "$ROOT/algos/abk" "$ROOT/zram_work"

# 2) zstdp 需要 vendored zstd
echo
echo "=============================================="
echo " 准备 zstdp 的 vendored zstd"
echo "=============================================="
python3 /mnt/c/nomount/zram_ko/vendor_zstdp.py \
  "$PWD" "$ROOT/algos/abk/zram/zstdp" "$ROOT/zram_work/zstdp"

# 3) 逐个编译
FAIL=0
for m in lz4k lz4kd lz4k_oplus zstdp; do
  echo
  echo "=============================================="
  echo " 编译 $m"
  echo "=============================================="
  MODDIR="$ROOT/zram_work/$m"
  [ -d "$MODDIR" ] || { echo "  目录缺失: $MODDIR"; FAIL=1; continue; }
  cp -f out/vmlinux.symvers "$MODDIR/Module.symvers" 2>/dev/null || true

  if make -j"$(nproc)" $FLAGS M="$MODDIR" modules > "/tmp/$m.log" 2>&1; then
    if [ -f "$MODDIR/$m.ko" ]; then
      cp -f "$MODDIR/$m.ko" "$OUT/"
      echo "  OK   $(ls -lh "$OUT/$m.ko" | awk '{print $5}')"
    else
      echo "  FAIL make 成功但未生成 $m.ko"
      grep -nE 'error:|Error [0-9]' "/tmp/$m.log" | head -5
      FAIL=1
    fi
  else
    echo "  FAIL make 失败"
    grep -nE 'error:|Error [0-9]' "/tmp/$m.log" | head -10
    FAIL=1
  fi
done

echo
echo "=============================================="
echo " 产物"
echo "=============================================="
ls -lh "$OUT" 2>/dev/null
exit $FAIL
