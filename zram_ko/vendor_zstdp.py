#!/usr/bin/env python3
"""Vendor the kernel tree's zstd into a zstdp module directory.

ABK ships zstdp as a kernel-tree integration: setup_zstdp.sh copies
lib/zstd and the zstd headers into the tree, rewrites a couple of
includes, and patches crypto/ plus drivers/block/zram/. That is wrong for
our purpose -- we want a standalone .ko against the stock device kernel.

What zstdp actually needs is just its wrapper plus a private copy of zstd,
compiled with every exported zstd symbol renamed to abk_zstdp_*. The
prefix matters: the device kernel has CONFIG_CRYPTO_ZSTD=y, so plain
ZSTD_* symbols already exist there, and a module that referenced them
would bind to the kernel's version instead of its own.

Layout produced:
    <dest>/zstdp_wrapper.c
    <dest>/zstdp_namespace.h
    <dest>/vendor/include/linux/{zstd.h,zstd_lib.h,zstd_errors.h,unaligned.h}
    <dest>/vendor/lib/zstd/**

Usage: vendor_zstdp.py <kernel-tree-common> <abk-zram-zstdp> <dest>
"""
import os
import shutil
import sys


def copy_tree(src, dst):
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def copy_file(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    common, abk_zstdp, dest = sys.argv[1:4]

    vendor = os.path.join(dest, 'vendor')
    os.makedirs(vendor, exist_ok=True)

    # 1. zstd sources + headers from the kernel tree
    src_zstd = os.path.join(common, 'lib', 'zstd')
    if not os.path.isdir(src_zstd):
        raise SystemExit(f'[zstdp] missing {src_zstd}')
    copy_tree(src_zstd, os.path.join(vendor, 'lib', 'zstd'))

    inc = os.path.join(vendor, 'include', 'linux')
    os.makedirs(inc, exist_ok=True)
    for h in ('zstd.h', 'zstd_lib.h', 'zstd_errors.h'):
        src = os.path.join(common, 'include', 'linux', h)
        if os.path.isfile(src):
            copy_file(src, os.path.join(inc, h))
        else:
            print(f'[zstdp] WARNING: missing {src}')

    # unaligned.h: newer trees have include/linux/unaligned.h, older ones
    # only asm-generic. ABK ships a vendored shim for the latter case.
    unl = os.path.join(common, 'include', 'linux', 'unaligned.h')
    if os.path.isfile(unl):
        copy_file(unl, os.path.join(inc, 'unaligned.h'))
    else:
        shim = os.path.join(abk_zstdp, 'vendor_include_linux_unaligned.h')
        if os.path.isfile(shim):
            copy_file(shim, os.path.join(inc, 'unaligned.h'))
            print('[zstdp] used vendored unaligned.h shim')

    # 2. wrapper sources
    for f in ('zstdp_wrapper.c', 'zstdp_namespace.h', 'Makefile'):
        src = os.path.join(abk_zstdp, f)
        if os.path.isfile(src):
            copy_file(src, os.path.join(dest, f))
        else:
            print(f'[zstdp] WARNING: missing {src}')

    # 3. point error_private.h at the vendored zstd_errors.h
    #
    #    In-tree it does "#include <linux/zstd_errors.h>", which would
    #    resolve to the kernel's copy. Use the vendored one so the enum
    #    layout matches the zstd build we are linking.
    err_h = os.path.join(vendor, 'lib', 'zstd', 'common', 'error_private.h')
    if os.path.isfile(err_h):
        with open(err_h, encoding='utf-8', errors='replace') as fh:
            text = fh.read()
        old = '#include <linux/zstd_errors.h>'
        new = '#include "vendor/include/linux/zstd_errors.h"'
        if old in text and new not in text:
            with open(err_h, 'w', encoding='utf-8') as fh:
                fh.write(text.replace(old, new, 1))
            print('[zstdp] error_private.h -> vendored zstd_errors.h')

    print(f'[zstdp] staged into {dest}')


if __name__ == '__main__':
    main()
