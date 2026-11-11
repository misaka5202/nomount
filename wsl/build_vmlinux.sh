#!/bin/bash
# 编译 vmlinux 并保留完整日志, 便于定位失败点。
set -uo pipefail

ROOT=/home/misaka/zram
cd "$ROOT/common" || exit 1
export PATH="$ROOT/clang20/bin:$PATH"

echo "clang: $(command -v clang)"
LOG="$ROOT/vmlinux_full.log"

make -j"$(nproc)" \
  LLVM=1 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
  CC=clang LD=ld.lld HOSTCC=clang HOSTLD=ld.lld O=out \
  KCFLAGS+=-O2 KCFLAGS+=-Wno-error HOSTCFLAGS+=-Wno-error WERROR=0 \
  vmlinux > "$LOG" 2>&1

rc=$?
echo "exit=$rc"

echo "=== 错误行 ==="
grep -nE 'error:|Error [0-9]|\*\*\*' "$LOG" 2>/dev/null | head -30

echo "=== 日志行数: $(wc -l < "$LOG") ==="
echo "=== 末尾 20 行 ==="
tail -20 "$LOG"
