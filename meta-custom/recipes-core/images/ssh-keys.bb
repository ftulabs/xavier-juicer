SUMMARY = "Preload authorized SSH keys for root"
LICENSE = "CLOSED"

SSH_AUTHORIZED_KEY ?= ""

do_install() {
    if [ -z "${SSH_AUTHORIZED_KEY}" ]; then
        bbfatal "Set SSH_AUTHORIZED_KEY before you install ssh-keys"
    fi
    install -d ${D}${ROOT_HOME}/.ssh
    printf '%s\n' "${SSH_AUTHORIZED_KEY}" > ${D}${ROOT_HOME}/.ssh/authorized_keys
    chmod 0600 ${D}${ROOT_HOME}/.ssh/authorized_keys
}

FILES:${PN} += "${ROOT_HOME}/.ssh/authorized_keys"
