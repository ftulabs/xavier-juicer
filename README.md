# Jetson AGX Xavier Yocto Image

This project builds a Yocto Linux image for the NVIDIA Jetson AGX Xavier Developer Kit.

The image uses L4T r35.6.4 and the Yocto Scarthgap release. It uses RPM packages and systemd.

## Image Content

The image includes these items:

- CUDA 11.4, cuDNN, and TensorRT from the Jetson BSP.
- CUDA 12.2 compatibility libraries.
- Docker, Docker Compose, Podman, and NVIDIA container tools.
- Rust, Cargo, CMake, Git, Python, Node and common debug tools.
- OpenSSH and Tailscale.
- Bash and zsh. The image build sets the root login shell to `/bin/bash`.

The Xavier GPU uses CUDA architecture 7.2.

## Host Requirements

Use a supported Linux host. The build is tested against Ubuntu 24.04 LTS, but 22.04 or other distros may work too.

Install these host packages:

```sh
sudo apt-get update
sudo apt-get install gawk wget git diffstat unzip texinfo gcc build-essential \
  chrpath socat cpio python3 python3-pexpect xz-utils debianutils \
  iputils-ping file usbutils
```

Provide at least 300 GB of free disk space. Provide 32 GB of RAM when possible.

## Per-user Distrobox

The Xavier image provides Docker and NVIDIA's Docker runtime. Install
Distrobox under your home directory, then create a container from NVIDIA's
L4T JetPack image. Choose an image tag compatible with the Xavier's L4T
release from the [NGC L4T JetPack catalog](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/l4t-jetpack):

This project uses L4T 35.6.4. NGC currently lists `r35.4.1` as its newest R35
JetPack image, so that tag is older and is not an exact match.

```sh
curl -fsSL https://raw.githubusercontent.com/89luca89/distrobox/main/install \
  | sh -s -- --prefix "$HOME/.local"
export PATH="$HOME/.local/bin:$PATH"
export CONTAINER_MANAGER=docker
# Replace with the tag you intend to use; r35.4.1 is only an older example.
L4T_IMAGE=nvcr.io/nvidia/l4t-jetpack:r35.4.1
distrobox create --name l4t-dev \
  --image "$L4T_IMAGE" \
  --additional-flags "--runtime=nvidia --network=host"
distrobox enter l4t-dev
```

Add both `export` lines to `~/.profile`. Docker must be running, and your user
must be allowed to access its daemon. Docker daemon access is effectively
root access. The L4T JetPack image includes CUDA, cuDNN, TensorRT, VPI, and
Jetson multimedia libraries. Install any additional packages inside the
container; they stay in its storage:

```sh
sudo apt-get update
sudo apt-get install -y build-essential
```

The NVIDIA runtime uses the image's CSV mounts (not CDI) to pass the Xavier's
GPU devices and driver libraries. To display an app on your computer, connect
to the Xavier with `ssh -X`, enter the Distrobox, and start the app. The image
includes `xauth` and enables SSH X11 forwarding; no screen or display server
is needed on the Xavier. `--network=host` lets the container reach SSH's
forwarding proxy on the Xavier. Your computer must have a working X11 display
(Xorg or XWayland).

## Create a Build Directory

Clone this project from its GitHub repository. Change to the project directory.

Run the setup script:

```sh
./scripts/setup-jetson-xavier-build
```

Before you run the script, you can create local access configuration:

```sh
cp config/local.private.conf.example config/local.private.conf
```

Set the SSH public key in `config/local.private.conf`. Git ignores this file. The setup script adds it to the build configuration.

The script does these actions:

1. Clones the required external layers with shallow Git clones.
2. Checks the exact revision of each external layer.
3. Creates `build/conf/local.conf`.
4. Creates `build/conf/bblayers.conf` with paths for this machine.

The script stops if the build directory already has a configuration. Use a new build directory to make another configuration:

```sh
./scripts/setup-jetson-xavier-build /work/jetson-build
```

## Build the Image

Start the build environment:

```sh
. oe-init-build-env build
```

Build the image:

```sh
bitbake core-image-minimal
```

BitBake writes images to this directory:

```text
build/tmp/deploy/images/jetson-agx-xavier-devkit/
```

The first build downloads source files and creates build output. Do not add `build/`, download files, sstate files, or external layers to Git.

## Flash the Xavier

The build creates a Tegra flash bundle. Flashing erases the Xavier internal eMMC. Use a supported Linux host, a direct USB cable, and stable power for the host and Xavier.

1. Build the image.
2. Set the Xavier to Force Recovery Mode. Power off the Xavier. Connect the baseboard Type-C port `J512` to the build host. Hold the `FORCE RECOVERY` button, press and release `POWER`, then release `FORCE RECOVERY`.
3. Confirm that the host detects the Xavier:

```sh
lsusb | grep '0955:7019'
```

4. Extract the `*.tegraflash.tar.gz` file for the image. Replace `<timestamp>` with the name that BitBake created:

```sh
deploy_dir=build/tmp/deploy/images/jetson-agx-xavier-devkit
flash_dir=/tmp/xavier-flash
mkdir -p "$flash_dir"
tar -xzf "$deploy_dir/core-image-minimal-jetson-agx-xavier-devkit.rootfs-<timestamp>.tegraflash.tar.gz" -C "$flash_dir"
```

5. Run the flash script from the extracted directory:

```sh
cd "$flash_dir"
sudo ./doflash.sh
```

The script programs the boot firmware and the image to the Xavier internal eMMC. Do not disconnect the USB cable or power during this process. The Xavier restarts when the flash process completes.

This procedure is for an unfused development kit. A device with Secure Boot fuses needs its signing keys and the matching `doflash.sh` signing options.

## Redundant Boot (A/B)

The image uses the redundant flash layout (`USE_REDUNDANT_FLASH_LAYOUT_DEFAULT = "1"`):

- Bootloader A/B slots, updated through UEFI capsules (`tegra-uefi-capsules` builds
  `jetson-agx-xavier-devkit-tegra-bl.cap`).
- Root filesystem slots `APP` and `APP_b`, 14 GiB each. The UEFI boot chain retries a slot that
  does not boot and falls back to the other one. `nv_update_verifier.service` marks a boot as
  successful.
- `nvbootctrl` (package `tegra-redundant-boot`) shows and selects slots:
  `nvbootctrl dump-slots-info`, `nvbootctrl -t rootfs dump-slots-info`.

Rootfs update without physical access (`momonga-ota`, package `momonga-recovery`). A flash
package from `scripts/momonga-flash-package` contains `<name>.rootfs.ext4.zst` and its manifest
`<name>.ota`:

1. `sudo momonga-ota install <name>.ota <name>.rootfs.ext4.zst` (local paths or http(s) URLs,
   such as presigned R2 links). It writes the image into the inactive slot (`APP_b` when slot A
   runs, `APP` otherwise), reads it back against the manifest's digest, copies the SSH host keys
   and the Tailscale state into it, and selects it for the next boot.
2. Reboot. The new slot boots on trial: `nv_update_verifier` skips it, and
   `momonga-boot-trial` runs `nvbootctrl verify` once sshd answers, a default route exists, and
   Tailscale is running. Its log: `journalctl -b -u momonga-boot-trial`.
3. If the board is not reachable 10 minutes after a trial boot, it reboots. After
   `RootfsRetryCountMax` (3) unverified boots, the boot chain returns to the previous slot.
4. To go back by hand: `sudo nvbootctrl -t rootfs set-active-boot-slot <slot>`, then reboot.
   `momonga-ota status` shows the slots.

Switching the rootfs slot also switches the bootloader chain to the same slot (`nvbootctrl
dump-slots-info`); both chains hold the bootloader from the last flash or capsule update.

State on the rootfs that `momonga-ota` does not copy (anything installed with dnf, edits under
`/etc`) stays with the old slot; `/home` and the Docker data root are on the SD card and shared.

Bootloader update: copy the capsule to `/boot/efi/EFI/UpdateCapsule/TEGRA_BL.Cap` on the ESP,
set the UEFI `OsIndications` capsule bit, and reboot (see the meta-tegra documentation for
`tegra-uefi-capsules`).

## Package Management (dnf)

The image includes `dnf` and the RPM database (`package-management` image feature). Packages
come from an RPM feed built from the same build directory:

1. Publish: `scripts/momonga-publish-feed build <rclone-remote:path>` runs
   `bitbake package-index` and mirrors `build/tmp/deploy/rpm`.
2. Point the image at the feed's public base URL in `config/local.private.conf`:
   `PACKAGE_FEED_URIS = "https://<feed-host>/<path>"`. The image then contains repository
   files for each package architecture.
3. On the device: `dnf makecache && dnf install <package>`.

`PRSERV_HOST = "localhost:0"` keeps package revisions increasing across rebuilds. Keep the
build directory's `cache/prserv.sqlite3` with the sstate cache so revisions stay monotonic.

## Host Integration

- Kernel: `vsock`, `vhost_vsock`, and `vhost_net` modules for KVM guests
  (`meta-custom/recipes-kernel/linux/files/virt-host.cfg`).
- Device tree: SD card slot polled instead of using its card-detect GPIO, matching the board's
  previous L4T installation.
- Recovery (`momonga-recovery`): reboot 10 s after a kernel panic (`panic=10` on the kernel
  command line), a 30 s systemd hardware watchdog, and a reboot instead of a shell when the
  initramfs cannot mount the rootfs or systemd enters emergency mode (after a 5 minute window
  for a console login). Unverified boots use up the slot's retries, then the boot chain falls
  back to the other slot.
- Power: MAXN by default (`NVPMODEL_CONFIG_DEFAULT = "0"`).
- GPU: Vulkan, EGL/GLES, and the GBM backend stay installed without a display server, so the
  NVIDIA container runtime can pass the Tegra GPU userspace into containers. `tegra-udrm` provides
  `/dev/dri`.
- Site: SD card (label `xavier-sd`) at `/mnt/sdcard` and read-only NFS model share, the
  Momonga extra package feed for dnf, and the CUDA 11.4 toolkit on `PATH`
  (`xavier-site-config`); Docker data root on the SD card, NVIDIA default runtime, and local
  registry in `/etc/docker/daemon.json` (`nvidia-docker` bbappend).
- SSH: key-only for every user (`PasswordAuthentication no`, `openssh` bbappend).

## Device Access

The image enables the OpenSSH server. The tracked project does not contain SSH keys or Tailscale auth keys.

`config/issue.net` is shown before SSH authentication. After an interactive SSH login,
the image reports load, memory, root filesystem usage, and Tegra CPU/GPU/thermal data
when the corresponding kernel interfaces are available.

To add SSH public keys for root after setup, add these lines to the local `build/conf/local.conf` file before the build. Separate several keys with a literal `\n`:

```bitbake
CORE_IMAGE_EXTRA_INSTALL:append = " ssh-keys"
SSH_AUTHORIZED_KEY = "ssh-ed25519 AAAA... user@host\nssh-ed25519 AAAA... other@host"
```

Root can log in over SSH with these keys only (`PermitRootLogin prohibit-password`); password
logins over SSH are refused.

Do not commit that local configuration file.

To join Tailscale, start the device and run `tailscale up`. Complete the login step that Tailscale shows.

## Time

The image uses the `Asia/Ho_Chi_Minh` timezone. It starts `systemd-timesyncd` at boot and synchronizes time after the Ethernet network is available. The configured NTP servers are `time.cloudflare.com` and `time.google.com`.

## First Boot Users

`/etc/passwd` is present in the final image. The image sets the root login shell to `/bin/bash`.

The image creates the login users listed in `MOMONGA_USERS` in `config/local.conf` (`name:uid:shell`). They belong to `wheel`, which has passwordless `sudo`, and to `docker`, `kvm`, `video` and `render`. Set each user's SSH key as `MOMONGA_USER_KEY_<name>` in `config/local.private.conf`; the image installs it at `/etc/ssh/authorized_keys/<name>`, which `sshd` reads in addition to `~/.ssh/authorized_keys`. These users have no password. `/home` is a bind mount of `/mnt/sdcard/home`, so home directories survive a reflash.

You can also create and manage users after flashing. Sign in as root on the local console or through SSH with the key that you configured. Then create a user and set its password:

```sh
useradd --create-home --shell /bin/bash xavier
passwd xavier
```

Use `usermod` to change groups. Add an administrator to `wheel` and, when needed, to the Docker group:

```sh
usermod --append --groups wheel,docker xavier
```

The image installs `sudo`. Members of `wheel` can run administrative commands with `sudo`, for example `sudo -i`. Use `su -` when you need a root login shell. The image uses SSH key authentication for root. Configure a key in `config/local.private.conf` before you build. The key installs at `/root/.ssh/authorized_keys`. Root has no password unless you set `MOMONGA_ROOT_PASSWORD_HASH` (from `openssl passwd -6`) in `config/local.private.conf`; that password works on the local console only, because SSH accepts keys only.

## Reproducibility

The setup script pins these external layers:

| Layer | Revision |
| --- | --- |
| meta-openembedded | `0f00f8b9a21950640da8c5707343e5540133f86e` |
| meta-virtualization | `e066aa71b00d8ef5121fcab3a7ac813058cda09c` |
| meta-tegra | `0c507bfe8d64a0e113beeff8f45e7fe0dfb5bc80` |
| meta-tailscale | `c70a30954839eef1923627e3a2f056692611f789` |

The custom recipes in `meta-custom/` are part of this project. The source archives for the NVIDIA container library use fixed commit IDs and SHA-256 checksums.

## Extra ARM64 Packages

The extra RPM feed includes Neovim, `bat`, `fzf`, Node.js with npm, Neofetch, Fastfetch, C.UTF-8 (`momonga-locale`), ONNX, ONNX GraphSurgeon, Polygraphy, TensorRT Python bindings, `tegrastats`, and `jtop` (from `python3-jetson-stats`). Neofetch and Fastfetch include the MomongaOS logo. Custom-layer RPMs depend on `momonga-locale`, so C.UTF-8 is installed with them. The Neovim, `bat`, `fzf`, and Node.js recipes package official upstream Linux ARM64 release binaries, so they do not compile Neovim, Rust, or V8. The Zsh recipe enables dynamic modules for plugins such as Powerlevel10k and fzf-tab. Build the optional RPMs with:

```sh
bitbake bash bat diffutils fzf gdbm glibc-locale nano ncurses neovim nodejs24 \
  neofetch fastfetch momonga-locale ptest-runner python3 python3-distro \
  python3-jetson-stats python3-numpy python3-nvidia-ml-py python3-onnx \
  python3-onnx-graphsurgeon python3-polygraphy python3-smbus2 python3-tensorrt \
  tegra-tools tensorrt-trtexec-prebuilt zsh
```

The Node.js and Neovim binaries require glibc 2.28 and 2.34 or newer, respectively. Confirm those requirements against the target image before installing. The target's RPM dependency solver may not detect every required glibc symbol version. The `nodejs24` RPM provides both Node.js 24 and npm.

ARM64 RPMs are stored once in the append-only GitHub Release asset pool `momonga-rpm-packages`; each `momonga-rpm-feed-*` release publishes signed repository metadata only. A GitHub Actions workflow deploys that metadata to GitHub Pages at `/rpm/momonga/aarch64/` and generates browsable indexes with direct GitHub Releases download links. The RPMs and repository metadata use the Momonga signing key; the workflow publishes its public key beside the metadata. Use this DNF configuration:

The image ships it as `/etc/yum.repos.d/momonga-extra.repo` (`xavier-site-config`). Packages installed from the feed live on the rootfs slot, so install them again after a `momonga-ota` update:

```ini
[momonga-extra]
name=Momonga Extra Packages
baseurl=https://kani.ftds.online/rpm/momonga/aarch64/
enabled=1
gpgcheck=1
gpgkey=https://kani.ftds.online/rpm/momonga/aarch64/RPM-GPG-KEY-momonga
repo_gpgcheck=1
```

The build result can change when an upstream download is removed or changed. Keep a copy of `build/downloads/` if you must make the same build without network access.

## Clean Data

These paths are local build data. Git ignores them:

- `build/`
- `downloads/`
- `sstate-cache/`
- `meta-openembedded/`
- `meta-virtualization/`
- `meta-tegra/`
- `meta-tailscale/`

To remove one build configuration, remove its build directory. Do not remove a directory until you no longer need its images, logs, downloads, or sstate cache.
