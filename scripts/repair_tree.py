#!/usr/bin/env python3
"""Repair a kernel tree that was copied through a case-insensitive filesystem.

Two independent kinds of damage occur when a Linux kernel tree passes
through NTFS:

1. CRLF line endings. Kconfig chokes on the CR byte
   ("ignoring unsupported character", "missing end statement"), and the
   shebang of extensionless helper scripts becomes "#!/bin/sh\\r", which
   the kernel reports as "No such file or directory" when make execs it.

2. Case-collapsed files. Trees legitimately contain pairs like
   net/netfilter/xt_DSCP.c (TARGET) and xt_dscp.c (MATCH). NTFS keeps
   only one, so the Makefile later fails with
   "No rule to make target 'net/netfilter/xt_DSCP.o'".

This script fixes (1) in place and reports (2) so the missing files can be
refetched. It is only needed when the source came from a Windows volume;
trees downloaded as a zip inside Linux already have LF endings and correct
case.

Usage: repair_tree.py <tree-root> [--fix-cr] [--report-case]
"""
import os
import re
import sys

TEXT_EXT = {
    '.c', '.h', '.S', '.s', '.mk', '.pl', '.sh', '.py', '.dts', '.dtsi',
    '.bzl', '.rs', '.lds', '.txt', '.md', '.json', '.xml', '.yaml', '.yml',
    '.awk', '.in', '.ld', '.cfg', '.conf', '.spec',
}
TEXT_NAMES = {'Kconfig', 'Makefile', 'Kbuild', 'BUILD', 'BUILD.bazel'}
OBJ_RE = re.compile(r'^\s*(?:obj|lib|extra|always|hostprogs)[-\w$()\s]*\+?=\s*(.+)$')


def looks_textual(data):
    """No NUL in the first 8 KiB is a good enough text test."""
    return b'\0' not in data[:8192]


def is_text(name, data):
    if name in TEXT_NAMES or name.startswith(('Kconfig', 'Makefile')):
        return True
    if os.path.splitext(name)[1] in TEXT_EXT:
        return True
    return looks_textual(data)


def fix_crlf(root):
    scanned = fixed = 0
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            path = os.path.join(dirpath, name)
            if os.path.islink(path):
                continue
            try:
                with open(path, 'rb') as fh:
                    data = fh.read()
            except OSError:
                continue
            scanned += 1
            if b'\r' not in data or not is_text(name, data):
                continue
            try:
                with open(path, 'wb') as fh:
                    fh.write(data.replace(b'\r\n', b'\n').replace(b'\r', b'\n'))
                fixed += 1
            except OSError:
                pass
    print(f'[crlf] scanned={scanned} converted={fixed}')


def report_case(root):
    missing = []
    for dirpath, _dirs, files in os.walk(root):
        if 'Makefile' not in files:
            continue
        refs = []
        try:
            with open(os.path.join(dirpath, 'Makefile'),
                      encoding='utf-8', errors='replace') as fh:
                for line in fh:
                    line = line.split('#', 1)[0].rstrip()
                    m = OBJ_RE.match(line)
                    if not m:
                        continue
                    refs += [t for t in m.group(1).split() if t.endswith('.o')]
        except OSError:
            continue
        if not refs:
            continue

        try:
            present = {n.lower(): n for n in os.listdir(dirpath)
                       if n.endswith(('.c', '.S', '.s'))}
        except OSError:
            continue

        for ref in refs:
            stem = ref[:-2]
            if '/' in stem:
                continue
            exts = ('.c', '.S', '.s')
            if any(os.path.exists(os.path.join(dirpath, stem + e)) for e in exts):
                continue
            for e in exts:
                actual = present.get((stem + e).lower())
                if actual:
                    missing.append((os.path.relpath(os.path.join(dirpath, stem + e), root),
                                    actual))
                    break

    print(f'[case] collapsed files: {len(missing)}')
    for want, have in missing:
        print(f'  MISSING {want}   (only {have} exists)')
    return missing


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = {a for a in sys.argv[1:] if a.startswith('--')}
    root = args[0] if args else '.'

    do_cr = ('--fix-cr' in flags) or not flags
    do_case = ('--report-case' in flags) or not flags

    if do_cr:
        fix_crlf(root)
    if do_case:
        report_case(root)


if __name__ == '__main__':
    main()
