cd /home/misaka/zram/common
export PATH=/home/misaka/zram/clang20/bin:$PATH
make -j$(nproc) LLVM=1 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- CC=clang LD=ld.lld HOSTCC=clang HOSTLD=ld.lld O=out KCFLAGS+=-O2 KCFLAGS+=-Wno-error WERROR=0 modules_prepare > /tmp/prep3.log 2>&1
echo "exit=$?"
ls -l out/scripts/module.lds 2>&1