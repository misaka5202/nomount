#!/bin/bash
# 打包成 KernelSU 模块。
set -uo pipefail

ROOT=/home/misaka/zram
SRC="$ROOT/kos"
STAGE="$ROOT/ksu_module"
TMPL=/mnt/c/nomount/zram_ko/ksu_module
DEVICE_KREL="6.1.157-android14-11-o-ga8ed1c96e9fd"

rm -rf "$STAGE"
mkdir -p "$STAGE/system/lib/modules"

echo "=== 复制 ko ==="
for f in "$SRC"/*.ko; do
  [ -f "$f" ] || continue
  cp -f "$f" "$STAGE/system/lib/modules/"
  echo "  $(basename "$f")"
done

echo
echo "=== 复制模块脚本 ==="
cp -f "$TMPL/post-fs-data.sh" "$STAGE/post-fs-data.sh"
cp -f "$TMPL/customize.sh"   "$STAGE/customize.sh"
cp -f "$TMPL/uninstall.sh"   "$STAGE/uninstall.sh"
chmod 755 "$STAGE/post-fs-data.sh" "$STAGE/uninstall.sh"

# 这些脚本来自 Windows，需去掉 CR，否则 Android 的 sh 会报错
python3 /mnt/c/nomount/wsl/strip_cr.py "$STAGE" > /dev/null 2>&1 || true
chmod 755 "$STAGE/post-fs-data.sh" "$STAGE/uninstall.sh"

VER=$(date +%Y%m%d)
{
  printf 'id=zram_algos\n'
  printf 'name=ZRAM Compressor Algorithms\n'
  printf 'version=%s\n' "$VER"
  printf 'versionCode=%s\n' "$VER"
  printf 'author=ABK/SukiSU_patch port\n'
  printf 'description=Extra zram compressors (lz4k, lz4kd, lz4k_oplus, zstdp) as loadable kernel modules. Built for %s. Switch compressor with Scene or sysfs.\n' "$DEVICE_KREL"
} > "$STAGE/module.prop"

echo
echo "=== module.prop ==="
cat "$STAGE/module.prop"

echo
echo "=== 打包 ==="
cd "$STAGE" || exit 1
ZIP="$ROOT/zram_algos-$VER.zip"
rm -f "$ZIP"
zip -qr9 "$ZIP" . -x '*.DS_Store'
cd "$ROOT" || exit 1

echo "  $ZIP ($(du -h "$ZIP" | cut -f1))"
echo
echo "=== 包内容 ==="
unzip -l "$ZIP"

echo
echo "=== 脚本换行检查 ==="
file "$STAGE/post-fs-data.sh"
