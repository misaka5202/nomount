#!/usr/bin/env python3
"""Strip CR from text files so Kconfig/make can parse Windows-sourced trees.

The kernel source was copied from a Windows filesystem, so nearly every
file carries CRLF line endings. Kconfig chokes on the CR
("ignoring unsupported character", "missing end statement"), and make
misparses rules for the same reason.

sed with 's/\\r$//' is unreliable through the shell quoting layers, so do
it in Python where the byte is unambiguous.

Usage: strip_cr.py <dir> [<dir> ...]
"""
import os
import sys

TEXT_EXT = {
    '.c', '.h', '.S', '.s', '.mk', '.pl', '.sh', '.py', '.dts', '.dtsi',
    '.bzl', '.rs', '.lds', '.txt', '.md', '.json', '.xml', '.yaml', '.yml',
    '.awk', '.sed', '.in', '.ld', '.lds', '.cfg', '.conf', '.spec',
}
TEXT_NAMES = {'Kconfig', 'Makefile', 'Kbuild', 'BUILD', 'BUILD.bazel'}


def looks_textual(data):
    """Heuristic: no NUL bytes in the first 8 KiB means text.

    Extension whitelists miss extensionless scripts such as
    scripts/remove-stale-files. Those carry a CRLF shebang "#!/bin/sh\\r",
    which the kernel reports as "No such file or directory" when make tries
    to exec it -- the kernel is looking for an interpreter literally named
    "/bin/sh\\r". Sniffing the content catches every such case.
    """
    head = data[:8192]
    return b'\0' not in head


def is_text(name, data=None):
    if name in TEXT_NAMES or name.startswith('Kconfig') or name.startswith('Makefile'):
        return True
    if os.path.splitext(name)[1] in TEXT_EXT:
        return True
    # 无扩展名的脚本(Kconfig 引用的 helper、scripts/ 下的工具)按内容判断
    if data is not None:
        return looks_textual(data)
    return False


def main():
    dirs = sys.argv[1:] or ['.']
    total = 0
    fixed = 0

    for root_dir in dirs:
        if not os.path.isdir(root_dir):
            print(f'skip (not a dir): {root_dir}')
            continue
        for root, _dirs, files in os.walk(root_dir):
            for name in files:
                path = os.path.join(root, name)
                # 符号链接单独处理时容易写坏目标，这里一律跳过
                if os.path.islink(path):
                    continue
                try:
                    with open(path, 'rb') as fh:
                        data = fh.read()
                except OSError:
                    continue
                total += 1
                if b'\r' not in data:
                    continue
                if not is_text(name, data):
                    continue
                try:
                    with open(path, 'wb') as fh:
                        fh.write(data.replace(b'\r\n', b'\n').replace(b'\r', b'\n'))
                    fixed += 1
                except OSError:
                    pass

    print(f'scanned={total} fixed={fixed}')

    # 抽样验证几个关键文件
    for probe in ('common/arch/arm64/Kconfig', 'common/Makefile',
                  'vendor/oplus/kernel/cpu/Kconfig',
                  'common/scripts/remove-stale-files'):
        if not os.path.isfile(probe):
            continue
        with open(probe, 'rb') as fh:
            has_cr = b'\r' in fh.read()
        print(f'  {"STILL CRLF" if has_cr else "OK (LF)"}: {probe}')


if __name__ == '__main__':
    main()
