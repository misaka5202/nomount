#!/usr/bin/env python3
"""Patch bundled libbpf so resolve_btfids compiles under Clang 20.

tools/bpf/resolve_btfids vendors a copy of libbpf. Around line 10746 it
does:

    next_path = strchr(s, ':');

where s is 'const char *' but next_path is 'char *'. Clang 20 promotes
-Wincompatible-pointer-types-discards-qualifiers to a hard error in this
configuration, so `make vmlinux` dies while building the host tool:

    libbpf.c:10746:14: error: assigning to 'char *' from 'const char *'
    discards qualifiers

This matters because CONFIG_DEBUG_INFO_BTF_MODULES=y must stay enabled:
it gates two fields inside struct module, and disabling it changes
struct module's size (device's __this_module is 1088 bytes, ours came
out 1024), which in turn breaks module_layout's CRC.

Resolve it in the tooling rather than in the kernel config: switch the
offending assignment to a cast. The tool only parses paths, so the
qualifier change is behaviourally irrelevant.

Usage: patch_resolve_btfids.py <kernel-tree-root>
"""
import glob
import os
import sys


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.'

    cands = glob.glob(os.path.join(root, 'tools', 'bpf', 'resolve_btfids', 'libbpf', 'src', 'libbpf.c'))
    cands += glob.glob(os.path.join(root, 'tools', 'lib', 'bpf', 'libbpf.c'))
    if not cands:
        print('[btfids] no bundled libbpf.c found, nothing to patch')
        return

    patched = 0
    for path in cands:
        src = open(path, encoding='utf-8', errors='replace').read()
        if "next_path = strchr(s, ':');" not in src:
            print(f'[btfids] pattern absent in {path}')
            continue
        src = src.replace(
            "next_path = strchr(s, ':');",
            "next_path = (char *)strchr(s, ':');",
        )
        open(path, 'w', encoding='utf-8').write(src)
        print(f'[btfids] patched qualifier cast in {path}')
        patched += 1

    if not patched:
        print('[btfids] nothing patched')


if __name__ == '__main__':
    main()
