#!/bin/bash
cd /home/misaka/zram
export PATH="$PWD/clang20/bin:$PATH"
echo "=== clang ==="
clang --version | head -2
echo "=== lld ==="
ld.lld --version
echo "=== 目录 ==="
ls -d clang20 common modules 2>&1
