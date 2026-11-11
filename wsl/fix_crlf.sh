#!/bin/bash
# 把 WSL 里的源码树从 CRLF 转为 LF。
#
# 从 /mnt/c 复制 Windows 上的内核源码时，原样带入了 \r\n 换行。
# Kconfig 解析器遇到 \r 会报 "ignoring unsupported character" 和
# "missing end statement"，make 的变量与规则同样无法解析，
# 结果就是 gki_defconfig 阶段直接失败。
#
# 只处理文本文件(Kconfig/Makefile/*.c/*.h/*.S/*.pl/*.sh/*.py)，
# 用 sed 原地去掉行尾 \r。二进制文件不动。
set -uo pipefail

ROOT="${1:-/home/misaka/zram}"
cd "$ROOT" || exit 1

convert_tree() {
  local dir="$1"
  echo ">>> 处理 $dir"
  find "$dir" -type f \
    \( -name 'Kconfig*' -o -name 'Makefile*' -o -name '*.mk' \
       -o -name '*.c' -o -name '*.h' -o -name '*.S' -o -name '*.s' \
       -o -name '*.pl' -o -name '*.sh' -o -name '*.py' -o -name '*.dts' \
       -o -name '*.dtsi' -o -name '*.bzl' -o -name 'BUILD*' -o -name '*.mk' \) \
    -print0 2>/dev/null | \
  xargs -0 -r -P "$(nproc)" -n 200 sed -i 's/\r$//' 2>/dev/null
  echo "    done"
}

for d in common modules; do
  [ -d "$d" ] && convert_tree "$d"
done

echo "=== 验证 ==="
for f in common/arch/arm64/Kconfig common/Makefile common/kernel/oplus_cpu/Kconfig; do
  [ -f "$f" ] || continue
  if grep -qI $'\r' "$f" 2>/dev/null; then
    echo "  STILL CRLF: $f"
  else
    echo "  OK (LF): $f"
  fi
done
