SKIPUNZIP=0
ui_print " "
ui_print "*** ZRAM Compressor Algorithms ***"
ui_print " "
ui_print "- reboot to load all algorithms automatically"
ui_print "- switch compressor with Scene or sysfs:"
ui_print "    echo lz4k_oplus > /sys/block/zram0/comp_algorithm"
ui_print "- load log: /data/local/tmp/zram_algos.log"
ui_print " "
