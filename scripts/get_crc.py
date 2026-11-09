#!/usr/bin/env python3
"""Print the CRC a .ko records for a given symbol, or 'absent'.

Usage: get_crc.py <mod.ko> <symbol>
Reads the module's __versions section, which modpost populates with
( symbol, crc ) pairs used by the running kernel's version_check().
"""
import sys
import struct

MODULE_NAME_LEN = 56
ENTRY = 8 + MODULE_NAME_LEN


def main():
    path, want = sys.argv[1], sys.argv[2]
    data = open(path, 'rb').read()
    if data[:4] != b'\x7fELF':
        raise SystemExit('not an ELF')
    e = '<' if data[5] == 1 else '>'
    is64 = data[4] == 2
    if is64:
        shoff, = struct.unpack_from(e + 'Q', data, 0x28)
        shentsize, shnum = struct.unpack_from(e + 'HH', data, 0x3A)
        shstrndx, = struct.unpack_from(e + 'H', data, 0x3E)
        fmt = e + 'IIQQQQ'
    else:
        shoff, = struct.unpack_from(e + 'I', data, 0x20)
        shentsize, shnum = struct.unpack_from(e + 'HH', data, 0x2E)
        shstrndx, = struct.unpack_from(e + 'H', data, 0x32)
        fmt = e + 'IIIIII'

    raw_secs = [struct.unpack_from(fmt, data, shoff + i * shentsize) for i in range(shnum)]
    stroff, strsz = raw_secs[shstrndx][4], raw_secs[shstrndx][5]
    st = data[stroff:stroff + strsz]

    def nm(n):
        end = st.find(b'\0', n)
        return st[n:end].decode('utf-8', 'replace')

    off = size = None
    for s in raw_secs:
        if nm(s[0]) == '__versions':
            off, size = s[4], s[5]
            break
    if off is None:
        print('absent')
        return

    for i in range(off, off + size - ENTRY + 1, ENTRY):
        crc, = struct.unpack_from('<Q', data, i)
        raw = data[i + 8:i + ENTRY]
        end = raw.find(b'\0')
        if end > 0 and raw[:end].decode('utf-8', 'replace') == want:
            print(f'0x{crc:08x}')
            return
    print('absent')


if __name__ == '__main__':
    main()
