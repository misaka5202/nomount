#!/system/bin/sh
# Uninstall hook.
#
# Do not rmmod here: zram may be actively using one of these compressors,
# and unloading it underneath zram would crash the kernel. Modules stay
# resident until the next reboot, which is fine.

rm -f /data/local/tmp/zram_algos.log
