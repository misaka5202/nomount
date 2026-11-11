#!/bin/bash
# 取回被 Windows 大小写合并丢失的 netfilter 头文件。
#
# 与 .c 文件同样的问题: include/uapi/linux/netfilter/ 下同时存在
#   xt_DSCP.h (TARGET 用) 与 xt_dscp.h (MATCH 用)
# 复制到 NTFS 时被合并，只剩小写版本。构建 xt_DSCP.c 时会报
#   fatal error: 'linux/netfilter/xt_DSCP.h' file not found
set -uo pipefail

UAPI=/home/misaka/zram/common/include/uapi/linux/netfilter
BASE="https://raw.githubusercontent.com/torvalds/linux/v6.1"

cd "$UAPI" || exit 1

for name in xt_DSCP.h xt_HL.h xt_RATEEST.h xt_TCPMSS.h; do
  if [ -f "$name" ]; then
    echo "已存在 $name ($(wc -c < "$name") bytes)"
    continue
  fi
  if curl -fsSL --retry 5 --retry-delay 3 --connect-timeout 20 \
       -o "$name" "$BASE/include/uapi/linux/netfilter/$name"; then
    echo "OK   $name ($(wc -c < "$name") bytes)"
  else
    echo "FAIL $name"
  fi
done

echo
echo "=== 确认大小写配对 ==="
for pair in "xt_DSCP.h xt_dscp.h" "xt_HL.h xt_hl.h" \
            "xt_RATEEST.h xt_rateest.h" "xt_TCPMSS.h xt_tcpmss.h"; do
  set -- $pair
  a="$1"; b="$2"
  as="?"; bs="?"
  [ -f "$a" ] && as=$(wc -c < "$a")
  [ -f "$b" ] && bs=$(wc -c < "$b")
  printf '  %-16s %6s   |  %-16s %6s\n' "$a" "$as" "$b" "$bs"
done
