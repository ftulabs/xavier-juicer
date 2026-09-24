set_root_shell_to_zsh () {
    if [ -f "${IMAGE_ROOTFS}${sysconfdir}/passwd" ]; then
        sed -i -e 's|^root:\(.*\):/bin/\(sh\|bash\)$|root:\1:/bin/zsh|' "${IMAGE_ROOTFS}${sysconfdir}/passwd"
    fi
}
