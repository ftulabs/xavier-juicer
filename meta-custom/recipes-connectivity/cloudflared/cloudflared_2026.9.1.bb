SUMMARY = "Cloudflare Tunnel client"
HOMEPAGE = "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/"
LICENSE = "CLOSED"

SRC_URI = "https://github.com/cloudflare/cloudflared/releases/download/${PV}/cloudflared-linux-arm64;name=cloudflared"
SRC_URI[cloudflared.sha256sum] = "3d97437c71848bd8df68041e12436b484a661d95073ea1937f01a845ce88faa3"

S = "${WORKDIR}"

do_compile() {
    :
}

do_install() {
    install -D -m 0755 ${WORKDIR}/cloudflared-linux-arm64 ${D}${bindir}/cloudflared
}

FILES:${PN} = "${bindir}/cloudflared"
COMPATIBLE_HOST = "aarch64.*-linux"
