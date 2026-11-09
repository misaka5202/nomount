#!/usr/bin/env python3
"""Overlay a device's /proc/config.gz values onto a tree-generated .config.

Why this exists
---------------
Two naive approaches both fail when building a vendor module against an
upstream/AOSP kernel tree:

  * `make <name>_defconfig` with the device config: the device carries
    hundreds of vendor-only symbols that the tree has no Kconfig entry
    for. Kconfig reconciles the whole file, and the cascade turns off
    general options such as CONFIG_MODULES / CONFIG_MODVERSIONS /
    CONFIG_MODULE_UNLOAD, after which vmlinux refuses to build at all.

  * Putting the device config in verbatim and running syncconfig: the
    tree now has symbols the device config never mentioned. Kconfig asks
    about each as "(NEW)"; with no stdin it takes defaults, which resets
    those same critical options.

The workable combination is: let the tree generate a self-consistent
.config from its own defconfig (so every symbol the tree knows about is
present and coherent), then force every value the device config states
on top of it. What the device says wins; anything only the tree knows
keeps its tree default.

Usage:
    overlay_config.py <tree.config> <device.config> <out.config>
"""
import sys


def parse(path):
    """Return {symbol: full_line} preserving 'is not set' entries."""
    m = {}
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            line = line.rstrip('\n')
            if line.startswith('CONFIG_') and '=' in line:
                m[line.split('=', 1)[0]] = line
            elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
                m[line[2:].split(' is not set')[0].strip()] = line
    return m


def symbol_of(line):
    if line.startswith('CONFIG_') and '=' in line:
        return line.split('=', 1)[0]
    if line.startswith('# CONFIG_') and line.endswith(' is not set'):
        return line[2:].split(' is not set')[0].strip()
    return None


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    tree_path, dev_path, out_path = sys.argv[1:4]

    dev = parse(dev_path)
    out = []
    seen = set()
    overridden = 0

    with open(tree_path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            line = line.rstrip('\n')
            sym = symbol_of(line)
            if sym is None:
                out.append(line)
                continue
            if sym in dev:
                if dev[sym] != line:
                    overridden += 1
                out.append(dev[sym])
            else:
                out.append(line)
            seen.add(sym)

    # Symbols the tree never emitted but the device has. Kconfig will drop
    # them if unknown, which is harmless, but keeping them means a tree that
    # does know them gets the right value.
    extra = [v for k, v in dev.items() if k not in seen]
    out.extend(extra)

    with open(out_path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out) + '\n')

    print(f'[overlay] device symbols: {len(dev)}')
    print(f'[overlay] values overridden from device: {overridden}')
    print(f'[overlay] device-only symbols appended: {len(extra)}')
    print(f'[overlay] wrote {out_path}')


if __name__ == '__main__':
    main()
