#!/usr/bin/env python3
"""Detect case-collision damage in a kernel tree copied from Windows.

NTFS is case-insensitive, so a tree that legitimately contains both
xt_DSCP.c and xt_dscp.c ends up with a single file once copied through a
Windows volume. Linux then fails with:

    No rule to make target 'net/netfilter/xt_DSCP.o'

because the Makefile asks for a name that no longer exists.

There is no way to recover the lost content locally -- the two files were
distinct upstream. What this script does is enumerate every Makefile
reference whose lowercase form exists but whose exact form does not, so
the affected set is known and can be fetched precisely.

Usage: find_case_collisions.py <tree-root>
"""
import os
import re
import sys

# obj-$(CONFIG_X) += foo.o bar/ baz.o
OBJ_RE = re.compile(r'^\s*(?:obj|lib|extra|always|hostprogs)[-\w$()\s]*\+?=\s*(.+)$')


def collect_refs(makefile_path):
    refs = []
    try:
        with open(makefile_path, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                line = line.split('#', 1)[0].rstrip()
                m = OBJ_RE.match(line)
                if not m:
                    continue
                for tok in m.group(1).split():
                    if tok.endswith('.o'):
                        refs.append(tok)
    except OSError:
        pass
    return refs


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    missing = []

    for dirpath, _dirs, files in os.walk(root):
        if 'Makefile' not in files:
            continue
        makefile = os.path.join(dirpath, 'Makefile')
        refs = collect_refs(makefile)
        if not refs:
            continue

        # 目录下现有的 .c/.S 文件名(小写索引)，用于判断"大小写不同但同一文件"
        try:
            present = {name.lower(): name for name in os.listdir(dirpath)
                       if name.endswith(('.c', '.S', '.s'))}
        except OSError:
            continue

        for ref in refs:
            obj = ref[:-2] if ref.endswith('.o') else ref
            if '/' in obj:
                continue
            candidates = (obj + '.c', obj + '.S', obj + '.s')
            if any(os.path.exists(os.path.join(dirpath, c)) for c in candidates):
                continue
            # 精确名不存在；检查是否只有大小写不同的版本
            for c in candidates:
                actual = present.get(c.lower())
                if actual:
                    missing.append((dirpath, obj + c[2:], actual))
                    break

    print(f'case-collision candidates: {len(missing)}')
    for d, want, have in missing:
        rel = os.path.relpath(os.path.join(d, want), root)
        print(f'  WANT {rel}   HAVE {have}')


if __name__ == '__main__':
    main()
