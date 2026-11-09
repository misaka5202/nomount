#!/usr/bin/env python3
"""Stamp device-real modversions CRCs into a built .ko.

The OPPO open-source tree is 6.1.134 while the shipped kernel is
6.1.157. Stable backports between those releases changed struct module,
so genksyms derives a different module_layout CRC than the running
kernel has. check_modstruct_version() then fails and returns -ENOEXEC
without printing anything, which surfaces to userspace only as
"Exec format error" -- impossible to diagnose from dmesg.

Reading the real CRCs off the device is possible because vendor modules
in /vendor{,_dlkm}/lib/modules carry their own __versions tables; those
tables record the CRCs of the symbols they import, as computed against
the running kernel.

This script rewrites matching entries in the module's __versions
section. Only symbols already present are touched, and only when a
device CRC is known.

Usage:
    patch_crc.py <built.ko> <device_crcs.txt> [<out.ko>]
device_crcs.txt is Module.symvers-shaped:
    0x<CRC>\t<symbol>\t<module>\tEXPORT_SYMBOL
"""
import sys
import struct
import os

MODULE_NAME_LEN = 56
ENTRY = 8 + MODULE_NAME_LEN

# Symbols that matter for silent -ENOEXEC, plus ones nomount needs that
# vendor modules happen to export. Everything else keeps the compiler's
# value: a wrong CRC there produces a loud "disagrees about version of
# symbol" message rather than a mystery ENOEXEC.
PATCH_ALWAYS = ('module_layout',)


def get_versions_off(data):
    is64 = data[4] == 2
    e = '<' if data[5] == 1 else '>'
    if is64:
        shoff, = struct.unpack_from(e + 'Q', data, 0x28)
        shentsize, shnum = struct.unpack_from(e + 'HH', data, 0x3A)
        shstrndx, = struct.unpack_from(e + 'H', data, 0x3E)
    else:
        shoff, = struct.unpack_from(e + 'I', data, 0x20)
        shentsize, shnum = struct.unpack_from(e + 'HH', data, 0x2E)
        shstrndx, = struct.unpack_from(e + 'H', data, 0x32)
    secs = []
    for i in range(shnum):
        off = shoff + i * shentsize
        if is64:
            nm, st, fl, ad, of, sz = struct.unpack_from(e + 'IIQQQQ', data, off)
        else:
            nm, st, fl, ad, of, sz = struct.unpack_from(e + 'IIIIII', data, off)
        secs.append((nm, of, sz))
    _, stroff, strsz = secs[shstrndx]
    st = data[stroff:stroff + strsz]

    def sname(n):
        end = st.find(b'\0', n)
        return st[n:end].decode('utf-8', 'replace')

    for (nm, of, sz) in secs:
        if sname(nm) == '__versions':
            return of, sz
    return None, None


def load_device_crcs(path):
    crcs = {}
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            parts = line.rstrip('\n').split('\t')
            if len(parts) < 2:
                continue
            try:
                crc = int(parts[0], 16)
            except ValueError:
                continue
            crcs[parts[1]] = crc
    return crcs


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    src = sys.argv[1]
    crcfile = sys.argv[2]
    dst = sys.argv[3] if len(sys.argv) > 3 else src

    dev = load_device_crcs(crcfile)
    data = bytearray(open(src, 'rb').read())

    off, size = get_versions_off(bytes(data))
    if off is None:
        raise SystemExit(f'{src}: no __versions section; is CONFIG_MODVERSIONS on?')

    patched = []
    missing = []
    for i in range(off, off + size - ENTRY + 1, ENTRY):
        cur, = struct.unpack_from('<Q', data, i)
        raw = bytes(data[i + 8:i + ENTRY])
        end = raw.find(b'\0')
        if end <= 0:
            continue
        name = raw[:end].decode('utf-8', 'replace')
        want = dev.get(name)
        if want is None or want == cur:
            continue
        struct.pack_into('<Q', data, i, want)
        patched.append((name, cur, want))

    for name in PATCH_ALWAYS:
        if name not in dev:
            missing.append(name)

    print(f'[patch_crc] {os.path.basename(src)}: __versions {size} bytes')
    for name, cur, want in patched:
        print(f'  {name}: 0x{cur:08x} -> 0x{want:08x}')
    print(f'  patched {len(patched)} symbol(s)')

    if missing:
        raise SystemExit(f'[patch_crc] device CRC table lacks required: {missing}')
    if not any(n == 'module_layout' for n, _a, _b in patched) and 'module_layout' in dev:
        # already equal -> also fine
        pass

    open(dst, 'wb').write(bytes(data))
    print(f'  wrote {dst}')


if __name__ == '__main__':
    main()
