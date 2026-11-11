#!/usr/bin/env python3
"""Materialise the four zram compressor algorithms as out-of-tree modules.

The algos ship as kernel-tree patches (SukiSU_patch / ABK) that expect to
live inside crypto/ and lib/. We want them as standalone .ko files that
KernelSU can insmod against the stock device kernel, so instead of
patching the tree we lay the sources out in a self-contained module
directory and build with M=<dir> modules.

Layout produced under <dest>:

    lz4k/        crypto wrapper + lib/lz4k/*.c
    lz4kd/       crypto wrapper + lib/lz4kd/*.c
    lz4k_oplus/  self-contained (already has compress/decompress)
    zstdp/       crypto wrapper + vendored zstd (fetched separately)

Each directory gets a Makefile that names the module after the algorithm,
and a Kbuild-compatible obj-m target.

Usage: stage_zram_modules.py <sukisu_patch_root> <abk_root> <dest>
"""
import os
import shutil
import sys

WRAPPER_TMPL = """# SPDX-License-Identifier: GPL-2.0-only
# Standalone build of the {name} crypto compressor for zram.

ccflags-y += -I$(src)/include

obj-m += {obj}.o
{obj}-y := {objs}
"""


def read(path):
    with open(path, encoding='utf-8', errors='replace') as fh:
        return fh.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def modulefy(path, drop_exports=True):
    """Rewrite a crypto wrapper/library for out-of-tree module use.

    Two things break when these files are lifted out of the kernel tree:

    1. `subsys_initcall(x)` in a module still works, but the symbol lands in
       the module's init section with initcall ordering meant for built-ins.
       `module_init(x)` is the correct form for a loadable module.

    2. EXPORT_SYMBOL() on a module's own helpers is unnecessary and, worse,
       lz4kd exports lz4kd_encode_state_bytes_min from two different files,
       which is a duplicate symbol at link time. Drop them: nothing outside
       the module calls these.
    """
    text = read(path)
    orig = text

    text = text.replace('subsys_initcall(', 'module_init(')

    if drop_exports:
        lines = []
        for line in text.split('\n'):
            stripped = line.strip()
            if stripped.startswith('EXPORT_SYMBOL'):
                # keep line numbering sane without emitting the macro
                continue
            lines.append(line)
        text = '\n'.join(lines)

    if text != orig:
        write(path, text)
        return True
    return False


def stage_lz4k(sp_root, dest):
    """LZ4K: crypto/lz4k.c + lib/lz4k/{lz4k_encode,lz4k_decode}.c"""
    base = os.path.join(sp_root, 'other', 'zram', 'lz4k')
    out = os.path.join(dest, 'lz4k')
    os.makedirs(out, exist_ok=True)

    copy(os.path.join(base, 'crypto', 'lz4k.c'), os.path.join(out, 'lz4k_crypto.c'))

    lib = os.path.join(base, 'lib', 'lz4k')
    for f in ('lz4k_encode.c', 'lz4k_decode.c', 'lz4k_encode_private.h', 'lz4k_private.h'):
        copy(os.path.join(lib, f), os.path.join(out, f))

    copy(os.path.join(base, 'include', 'linux', 'lz4k.h'),
         os.path.join(out, 'include', 'linux', 'lz4k.h'))

    for f in ('lz4k_crypto.c', 'lz4k_encode.c', 'lz4k_decode.c'):
        modulefy(os.path.join(out, f))

    write(os.path.join(out, 'Makefile'), WRAPPER_TMPL.format(
        name='LZ4K', obj='lz4k',
        objs='lz4k_crypto.o lz4k_encode.o lz4k_decode.o'))
    print(f'[stage] lz4k -> {out}')


def stage_lz4kd(sp_root, dest):
    """LZ4KD: crypto/lz4kd.c + lib/lz4kd/*.c (delta variants included)"""
    base = os.path.join(sp_root, 'other', 'zram', 'lz4k')
    out = os.path.join(dest, 'lz4kd')
    os.makedirs(out, exist_ok=True)

    copy(os.path.join(base, 'crypto', 'lz4kd.c'), os.path.join(out, 'lz4kd_crypto.c'))

    lib = os.path.join(base, 'lib', 'lz4kd')
    for f in ('lz4kd_encode.c', 'lz4kd_decode.c',
              'lz4kd_encode_delta.c', 'lz4kd_decode_delta.c',
              'lz4kd_encode_private.h', 'lz4kd_private.h'):
        copy(os.path.join(lib, f), os.path.join(out, f))

    copy(os.path.join(base, 'include', 'linux', 'lz4kd.h'),
         os.path.join(out, 'include', 'linux', 'lz4kd.h'))

    for f in ('lz4kd_crypto.c', 'lz4kd_encode.c', 'lz4kd_decode.c',
              'lz4kd_encode_delta.c', 'lz4kd_decode_delta.c'):
        modulefy(os.path.join(out, f))

    # -DLZ4K_DELTA matches the upstream lib/lz4kd/Makefile
    text = WRAPPER_TMPL.format(
        name='LZ4KD', obj='lz4kd',
        objs='lz4kd_crypto.o lz4kd_encode.o lz4kd_decode.o '
             'lz4kd_encode_delta.o lz4kd_decode_delta.o')
    text = text.replace('ccflags-y += -I$(src)/include',
                        'ccflags-y += -I$(src)/include -DLZ4K_DELTA -O3')
    write(os.path.join(out, 'Makefile'), text)
    print(f'[stage] lz4kd -> {out}')


def stage_lz4k_oplus(sp_root, dest):
    """LZ4K_OPLUS: self-contained under lib/lz4k_oplus/"""
    base = os.path.join(sp_root, 'other', 'zram', 'lz4k_oplus')
    out = os.path.join(dest, 'lz4k_oplus')
    os.makedirs(out, exist_ok=True)

    rename = {'lz4k.c': 'lz4k_oplus_crypto.c'}
    for f in os.listdir(base):
        if not f.endswith(('.c', '.h')):
            continue
        target = rename.get(f, f)
        copy(os.path.join(base, f), os.path.join(out, target))

    # lz4k_oplus already uses module_init, but its compress/decompress
    # helpers carry EXPORT_SYMBOL; harmless in-tree, pointless in a module.
    for f in ('lz4k_oplus_crypto.c', 'lz4k_compress.c', 'lz4k_decompress.c'):
        modulefy(os.path.join(out, f))

    write(os.path.join(out, 'Makefile'), WRAPPER_TMPL.format(
        name='LZ4K_OPLUS', obj='lz4k_oplus',
        objs='lz4k_oplus_crypto.o lz4k_compress.o lz4k_decompress.o'))
    print(f'[stage] lz4k_oplus -> {out}')


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    sp_root, abk_root, dest = sys.argv[1:4]

    os.makedirs(dest, exist_ok=True)

    if os.path.isdir(os.path.join(sp_root, 'other', 'zram')):
        stage_lz4k(sp_root, dest)
        stage_lz4kd(sp_root, dest)
        stage_lz4k_oplus(sp_root, dest)
    else:
        print(f'[stage] WARNING: no zram dir under {sp_root}')

    # zstdp is staged by abk's own setup_zstdp.sh (it needs to vendor zstd
    # from the kernel tree); just note where its sources live.
    zstdp = os.path.join(abk_root, 'zram', 'zstdp')
    if os.path.isdir(zstdp):
        print(f'[stage] zstdp sources at {zstdp} (vendored zstd handled separately)')
    else:
        print(f'[stage] WARNING: no zstdp dir under {abk_root}')


if __name__ == '__main__':
    main()
