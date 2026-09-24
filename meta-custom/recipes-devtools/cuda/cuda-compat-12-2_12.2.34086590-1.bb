SUMMARY = "CUDA 12.2 forward-compatibility libraries for Jetson"
DESCRIPTION = "CUDA driver libraries that let JetPack 5 Xavier run CUDA 12.2 applications"
HOMEPAGE = "https://developer.nvidia.com/cuda-toolkit"
LICENSE = "CLOSED"

DEPENDS:tegra = "tegra-libraries-core"

# CUDA 12.2 is the newest CUDA release supported by the Xavier JetPack 5 BSP.
CUDA_VERSION = "12.2"
S = "${WORKDIR}/${BP}"
B = "${S}"

SRC_URI = "https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/arm64/cuda-compat-12-2_${PV}_arm64.deb;name=main;subdir=${BP}"
SRC_URI[main.sha256sum] = "3b74c3775bcc4999f89c5a73213cdbb34e8692e56b50d3d430186caec8efe0ef"

do_compile() {
    :
}

do_install() {
    install -d ${D}${prefix}/local/cuda-${CUDA_VERSION}
    cp -R --preserve=mode,links,timestamps \
        ${S}/usr/local/cuda-${CUDA_VERSION}/compat \
        ${D}${prefix}/local/cuda-${CUDA_VERSION}/
}

sysroot_stage_dirs:append() {
    sysroot_stage_dir $from${prefix}/local/cuda-${CUDA_VERSION} $to${prefix}/local/cuda-${CUDA_VERSION}
}

FILES:${PN} = "${prefix}/local/cuda-${CUDA_VERSION}/compat"

FILES_SOLIBSDEV = ""
SOLIBS = ".so*"
# NVIDIA ships these prebuilt driver libraries in CUDA's private compat directory.
INSANE_SKIP:${PN} += "ldflags file-rdeps libdir"
INSANE_SKIP:${PN} += "dev-so"
COMPATIBLE_MACHINE:class-target = "(tegra)"
PACKAGE_ARCH:class-target = "${TEGRA_PKGARCH}"
