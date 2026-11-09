#!/usr/bin/env python3
"""Reproduce the device's struct module exactly, including the ifdef wrapper.

Diffing our include/linux/module.h against the device's own kheaders with
comments stripped shows struct module differs by exactly one construct:

    #ifdef CONFIG_MITIGATION_ITS
            int its_num_pages;
            void **its_page_array;
    #endif

An earlier attempt emitted only the two fields, unconditionally. That
did move module_layout (0xa26bedb1 -> 0xed15e86a), proving the fields
matter, but it still did not match the device's 0xea759d7f: genksyms
hashes the token stream it is fed, and dropping the #ifdef/#endif changes
that stream.

So reproduce the block verbatim, and make the symbol resolvable. Because
this 6.1.134 tree has no Kconfig entry for MITIGATION_ITS (it arrived in
a later stable), syncconfig would drop any value written to .config. Add
a Kconfig entry alongside the field patch so `#ifdef` actually holds and
the preprocessed token stream matches the device's.

Usage: patch_module_layout.py <kernel-tree-root>
"""
import os
import sys

ANCHOR = '#ifdef CONFIG_CONSTRUCTORS'

BLOCK = """#ifdef CONFIG_MITIGATION_ITS
\tint its_num_pages;
\tvoid **its_page_array;
#endif

"""

KCONFIG_SNIPPET = """
config MITIGATION_ITS
\tbool "Mitigate ITS (Indirect Target Selection) attacks"
\tdepends on ARM64
\tdefault y
\thelp
\t  Layout parity with the shipped 6.1.157 kernel for this device.

\t  The option gates two fields inside struct module. The open-source
\t  tree here is 6.1.134 and predates the mitigation, so struct module
\t  comes out shorter than the running kernel's, which changes
\t  module_layout's CRC. check_modstruct_version() then rejects any
\t  module built against this tree with -ENOEXEC and no printk at all.
\t  Providing the symbol lets the fields compile in and keeps the
\t  layout identical.
"""


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.'

    mh = os.path.join(root, 'include', 'linux', 'module.h')
    if not os.path.isfile(mh):
        sys.exit(f'[layout] not found: {mh}')

    src = open(mh, encoding='utf-8', errors='replace').read()

    if 'CONFIG_MITIGATION_ITS' in src:
        print('[layout] wrapper already present, skipping module.h')
    else:
        if ANCHOR not in src:
            sys.exit(f'[layout] anchor not found: {ANCHOR}')
        src = src.replace(ANCHOR, BLOCK + ANCHOR, 1)
        open(mh, 'w', encoding='utf-8').write(src)
        print('[layout] inserted the device\'s CONFIG_MITIGATION_ITS block verbatim')

    # Register the symbol so Kconfig keeps it instead of silently dropping it.
    kc = os.path.join(root, 'arch', 'arm64', 'Kconfig')
    if not os.path.isfile(kc):
        sys.exit(f'[layout] not found: {kc}')

    ks = open(kc, encoding='utf-8', errors='replace').read()
    if 'config MITIGATION_ITS' in ks:
        print('[layout] Kconfig entry already present')
    else:
        ks = ks.rstrip('\n') + '\n' + KCONFIG_SNIPPET
        open(kc, 'w', encoding='utf-8').write(ks)
        print('[layout] added arch/arm64/Kconfig entry for MITIGATION_ITS')


if __name__ == '__main__':
    main()
