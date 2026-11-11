#!/bin/bash
cd /home/misaka/zram/common/net/netfilter || exit 1

echo "=== 现有文件 ==="
ls -la xt_dscp.c xt_hl.c xt_rateest.c xt_tcpmss.c 2>&1

echo
echo "=== 各文件前 5 行 (判断是哪个大小写版本) ==="
for f in xt_dscp.c xt_hl.c xt_rateest.c xt_tcpmss.c; do
  echo "--- $f ---"
  head -5 "$f" 2>&1
  echo
done

echo "=== Makefile 中对这四对的大小写引用 ==="
grep -inE 'xt_(DSCP|dscp|HL|hl|RATEEST|rateest|TCPMSS|tcpmss)\.o' Makefile
