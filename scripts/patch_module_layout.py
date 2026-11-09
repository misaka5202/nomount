#!/usr/bin/env python3
"""Make struct module match the device's layout for CONFIG_MITIGATION_ITS.

Context
-------
The OPPO open-source tree is 6.1.134; the device runs 6.1.157. Comparing
include/linux/module.h against the device's own kheaders, with comments
stripped, the only substantive difference inside struct module is:

    #ifdef CONFIG_MITIGATION_ITS
            int its_num_pages;
            void **its_page_array;
    #endif

The block sits mid-struct, so it shifts every following field. That
changes module_layout's CRC (device 0xea759d7f vs tree 0xa26bedb1).
check_modstruct_version() then fails and returns -ENOEXEC without any
printk, which is the opaque "Exec format error" on device. Forcing the
CRC instead corrupts the kernel's view of __this_module and panics in
mod_sysfs_setup().

Approach
--------
Kconfig in this tree has no MITIGATION_ITS symbol, so syncconfig would
drop any CONFIG_MITIGATION_ITS we write. Rather than teach Kconfig a new
symbol, emit the two fields unconditionally: the device has them, so
struct module must contain them regardless of how the config is spelled.

Note the option only gates these two pointers inside struct module; it
is not referenced by the fields that follow, so making it unconditional
reproduces the device layout exactly.

Usage: patch_module_layout.py <kernel-tree-root>
"""
import os
import sys

ANCHOR = '#ifdef CONFIG_CONSTRUCTORS'

BLOCK = """\t/* Layout parity with the shipped 6.1.157 kernel: these fields exist
\t * there under CONFIG_MITIGATION_ITS. Emitted unconditionally because
\t * this tree (6.1.134) has no Kconfig symbol for it and syncconfig would
\t * otherwise drop it, leaving struct module shorter than the kernel's.
\t */
\tint its_num_pages;
\tvoid **its_page_array;
"""


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    path = os.path.join(root, 'include', 'linux', 'module.h')
    if not os.path.isfile(path):
        sys.exit(f'[layout] not found: {path}')

    src = open(path, encoding='utf-8', errors='replace').read()

    if 'its_num_pages' in src:
        print('[layout] its_num_pages already present, skipping')
        return

    if ANCHOR not in src:
        sys.exit(f'[layout] anchor not found: {ANCHOR}')

    src = src.replace(ANCHOR, BLOCK + ANCHOR, 1)
    open(path, 'w', encoding='utf-8').write(src)
    print('[layout] injected its_num_pages / its_page_array into struct module')


if __name__ == '__main__':
    main()
