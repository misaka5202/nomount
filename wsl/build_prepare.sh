#!/bin/bash
# 本地复现 CI 的 zram kmod 构建流程 (WSL 内运行)
set -euo pipefail

ROOT=/home/misaka/zram
export PATH="$ROOT/clang20/bin:$PATH"
DEVICE_KREL="6.1.157-android14-11-o-ga8ed1c96e9fd"

FLAGS="LLVM=1 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
  CC=clang LD=ld.lld HOSTCC=clang HOSTLD=ld.lld O=out \
  KCFLAGS+=-O2 KCFLAGS+=-Wno-error HOSTCFLAGS+=-Wno-error WERROR=0"

echo "=============================================="
echo " 1) 对齐设备内核版本"
echo "=============================================="
cd "$ROOT/common"

KSUB="$(echo "$DEVICE_KREL" | cut -d'.' -f3 | cut -d'-' -f1)"
KSUFFIX="$(echo "$DEVICE_KREL" | cut -d'-' -f2-)"
echo "sublevel=$KSUB suffix=$KSUFFIX"

CUR_SUB="$(sed -n 's/^SUBLEVEL = //p' Makefile | tr -d ' ')"
if [ "$CUR_SUB" != "$KSUB" ]; then
  sed -i "s/^SUBLEVEL = .*/SUBLEVEL = $KSUB/" Makefile
  echo "SUBLEVEL: $CUR_SUB -> $KSUB"
fi

rm -f android/abi_gki_protected_exports_* || true
for f in scripts/setlocalversion; do
  sed -i 's/ -dirty//g' "$f"
  sed -i '$i res=$(echo "$res" | sed '\''s/-dirty//g'\'')' "$f"
  sed -i 's|res="$res${scm:++}"|res="$res"|' "$f"
  sed -i "\$s|echo \"\\\$res\"|echo \"-$KSUFFIX\"|" "$f"
done
echo "vermagic 后缀: -$KSUFFIX"
tail -n 2 scripts/setlocalversion

echo
echo "=============================================="
echo " 2) 生成 .config"
echo "=============================================="
if [ -d out ]; then
  echo "清理旧 out/"
  rm -rf out
fi

make -j"$(nproc)" $FLAGS gki_defconfig > /tmp/cfg.log 2>&1 || {
  echo "gki_defconfig 失败"; tail -20 /tmp/cfg.log; exit 1; }
cp -f out/.config out/.config.tree

python3 /mnt/c/nomount/scripts/overlay_config.py \
  out/.config.tree /mnt/c/nomount/device_full.config out/.config

sed -i -E 's|^CONFIG_MODULE_SIG_KEY=.*|# CONFIG_MODULE_SIG_KEY is not set|' out/.config

echo "=== 关键配置核对 ==="
MISS=0
for k in CONFIG_MODULES CONFIG_MODVERSIONS CONFIG_MODULE_UNLOAD \
         CONFIG_KALLSYMS_ALL CONFIG_SYSFS CONFIG_FTRACE CONFIG_ARM64 \
         CONFIG_DEBUG_INFO_BTF_MODULES CONFIG_ZRAM CONFIG_CRYPTO_ACOMP2; do
  if grep -q "^${k}=" out/.config; then
    echo "  OK   $(grep "^${k}=" out/.config | head -n1)"
  else
    echo "  MISS $k"
    case "$k" in
      CONFIG_MODULES|CONFIG_MODVERSIONS|CONFIG_ARM64) MISS=1 ;;
    esac
  fi
done
[ "$MISS" -eq 0 ] || { echo "关键配置缺失"; exit 1; }

python3 /mnt/c/nomount/scripts/patch_resolve_btfids.py .
make -j"$(nproc)" $FLAGS syncconfig > /tmp/sync.log 2>&1 || {
  echo "syncconfig 失败"; tail -20 /tmp/sync.log; exit 1; }

echo
echo "=============================================="
echo " 3) modules_prepare"
echo "=============================================="
make -j"$(nproc)" $FLAGS modules_prepare > /tmp/prep.log 2>&1 || {
  echo "modules_prepare 失败"; tail -40 /tmp/prep.log; exit 1; }
echo "OK"

echo
echo "=============================================="
echo " 4) 编译 vmlinux 生成符号表"
echo "=============================================="
touch include/linux/module.h
make -j"$(nproc)" $FLAGS vmlinux > /tmp/vmlinux.log 2>&1 || {
  echo "vmlinux 失败"; tail -40 /tmp/vmlinux.log; exit 1; }

[ -s out/vmlinux.symvers ] || { echo "符号表缺失"; exit 1; }
echo "符号表: $(wc -l < out/vmlinux.symvers) 条"
echo "module_layout: $(grep -P '\tmodule_layout\t' out/vmlinux.symvers | cut -f1)"

echo
echo "=============================================="
echo " 完成"
echo "=============================================="
