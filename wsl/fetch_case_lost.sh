#!/bin/bash
# 取回全部四个被 Windows 大小写合并丢失的 netfilter TARGET 源文件。
#
# 虽然设备 config 里 TARGET_HL / TARGET_RATEEST 是 not set，但补全它们
# 可以避免将来切换配置时再次踩到同一个坑，且这些文件与 MATCH 版本
# 内容完全不同，不能互相替代。
set -uo pipefail

DEST=/home/misaka/zram/common/net/netfilter
BASE="https://raw.githubusercontent.com/torvalds/linux/v6.1"
cd "$DEST" || exit 1

for name in xt_DSCP.c xt_HL.c xt_RATEEST.c xt_TCPMSS.c; do
  if [ -f "$name" ]; then
    echo "已存在 $name ($(wc -c < "$name") bytes)"
    continue
  fi
  if curl -fsSL --retry 5 --retry-delay 3 --connect-timeout 20 \
       -o "$name" "$BASE/net/netfilter/$name"; then
    echo "OK   $name ($(wc -c < "$name") bytes)"
  else
    echo "FAIL $name"
  fi
done

echo
echo "=== 最终确认(每个 TARGET 与其 MATCH 版本应同时存在且大小不同) ==="
for pair in "xt_DSCP.c xt_dscp.c" "xt_HL.c xt_hl.c" \
            "xt_RATEEST.c xt_rateest.c" "xt_TCPMSS.c xt_tcpmss.c"; do
  set -- $pair
  up="$1"; low="$2"
  us="?"; ls_="?"
  [ -f "$up" ] && us=$(wc -c < "$up")
  [ -f "$low" ] && ls_=$(wc -c < "$low")
  printf '  %-14s %6s   |  %-14s %6s\n' "$up" "$us" "$low" "$ls_"
done
