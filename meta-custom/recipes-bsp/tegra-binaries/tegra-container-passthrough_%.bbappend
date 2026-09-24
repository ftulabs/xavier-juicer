DEPENDS:append = " cuda-compat-12-2"
RDEPENDS:${PN}:append = " cuda-compat-12-2"
# This package deliberately stages NVIDIA libraries below the container mount root.
INSANE_SKIP:${PN} += "libdir"

do_install:append() {
    install -d ${D}${PASSTHRU_ROOT}/usr/local/cuda-12.2
    cp -R --preserve=mode,links,timestamps \
        ${RECIPE_SYSROOT}/usr/local/cuda-12.2/compat \
        ${D}${PASSTHRU_ROOT}/usr/local/cuda-12.2/
}
