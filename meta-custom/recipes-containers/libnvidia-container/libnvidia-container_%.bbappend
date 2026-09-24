# Avoid BitBake's full Git mirror for this pinned upstream revision.
SRC_URI:remove = "git://github.com/NVIDIA/libnvidia-container.git;protocol=https;name=libnvidia;branch=main"
SRC_URI:append = " https://codeload.github.com/NVIDIA/libnvidia-container/tar.gz/${SRCREV_libnvidia};name=libnvidia;downloadfilename=libnvidia-container-${SRCREV_libnvidia}.tar.gz;subdir=git;striplevel=1"
SRC_URI[libnvidia.sha256sum] = "9d93566bfa1444ab74870cd504be633aa17bd2f322e4702a7d5f3944541fcf1e"
WARN_QA:remove = "src-uri-bad"
