# Avoid BitBake's full Git mirror for this pinned Jetson upstream revision.
SRC_URI:remove = "git://github.com/NVIDIA/libnvidia-container.git;protocol=https;name=libnvidia;branch=jetson"
SRC_URI:append = " https://codeload.github.com/NVIDIA/libnvidia-container/tar.gz/${SRCREV_libnvidia};name=libnvidia;downloadfilename=libnvidia-container-${SRCREV_libnvidia}.tar.gz;subdir=git;striplevel=1"
SRC_URI[libnvidia.sha256sum] = "ac6c0fc9a9c4edeeca0627be0c983e6fed7c4b185cab2ba6f5bfcdc29443299a"
WARN_QA:remove = "src-uri-bad"
