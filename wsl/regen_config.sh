#!/bin/bash
# 重新生成 .config，让 PAHOLE_VERSION 检测到实际安装的 pahole。
#
# 之前 pahole 未安装，scripts/pahole-version.sh 返回 0，
# 于是 PAHOLE_HAS_SPLIT_BTF=n，Kconfig 连带把
# CONFIG_DEBUG_INFO_BTF_MODULES 关掉。
# 而该开关正是 struct module 里 btf_data_size/btf_data 两个字段的门闩，
# 少掉它们 struct module 尺寸就比设备小 16 字节，
# module_layout 的 CRC 因此算成 0xa26bedb1 而不是设备的 0xea759d7f。
set -euo pipefail

ROOT=/home/misaka/zram
cd "$ROOT/common" || exit 1
export PATH="$ROOT/clang20/bin:$PATH"

FLAGS="LLVM=1 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
  CC=clang LD=ld.lld HOSTCC=clang HOSTLD=ld.lld O=out
  KCFLAGS+=-O2 KCFLAGS+=-Wno-error HOSTCFLAGS+=-Wno-error WERROR=0"

echo "=== pahole 探测 ==="
bash scripts/pahole-version.sh pahole 2>/dev/null || echo "(探测脚本无输出)"
echo "pahole --version: $(pahole --version)"

echo
echo "=== 重新生成配置 ==="
rm -rf out
make -j"$(nproc)" $FLAGS gki_defconfig > /tmp/cfg2.log 2>&1 || {
  echo "gki_defconfig 失败"; tail -20 /tmp/cfg2.log; exit 1; }
cp -f out/.config out/.config.tree

python3 /mnt/c/nomount/scripts/overlay_config.py \
  out/.config.tree /mnt/c/nomount/device_full.config out/.config

sed -i -E 's|^CONFIG_MODULE_SIG_KEY=.*|# CONFIG_MODULE_SIG_KEY is not set|' out/.config

echo
echo "=== overlay 后(未 syncconfig) ==="
grep -E 'DEBUG_INFO_BTF_MODULES|PAHOLE_VERSION|PAHOLE_HAS_SPLIT' out/.config || echo "(无)"

echo
echo "=== syncconfig ==="
make -j"$(nproc)" $FLAGS syncconfig > /tmp/sync2.log 2>&1 || {
  echo "syncconfig 失败"; tail -20 /tmp/sync2.log; exit 1; }

echo
echo "=== syncconfig 后 ==="
for k in CONFIG_DEBUG_INFO_BTF CONFIG_DEBUG_INFO_BTF_MODULES \
         CONFIG_PAHOLE_VERSION CONFIG_PAHOLE_HAS_SPLIT_BTF CONFIG_MODULES; do
  line=$(grep -E "^${k}=" out/.config 2>/dev/null | head -1 || true)
  [ -n "$line" ] || line="# $k is not set"
  echo "  $line"
done
