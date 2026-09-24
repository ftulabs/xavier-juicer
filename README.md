# Jetson AGX Xavier Yocto Image

This project builds a Yocto Linux image for the NVIDIA Jetson AGX Xavier Developer Kit.

The image uses L4T r35.6.4 and the Yocto Scarthgap release. It uses RPM packages and systemd.

## Image Content

The image includes these items:

- CUDA 11.4, cuDNN, and TensorRT from the Jetson BSP.
- CUDA 12.2 compatibility libraries.
- Docker, Docker Compose, and NVIDIA container tools.
- Rust, Cargo, CMake, Git, Python, and common debug tools.
- OpenSSH and Tailscale.
- zsh as the root login shell when the image has `/etc/passwd`.

The Xavier GPU uses CUDA architecture 7.2.

## Host Requirements

Use a supported Linux host. Ubuntu 22.04 LTS or Ubuntu 24.04 LTS is suitable.

Install these host packages:

```sh
sudo apt-get update
sudo apt-get install gawk wget git diffstat unzip texinfo gcc build-essential \
  chrpath socat cpio python3 python3-pexpect xz-utils debianutils \
  iputils-ping file
```

Provide at least 300 GB of free disk space. Provide 32 GB of RAM when possible.

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

## Device Access

The image enables the OpenSSH server. The tracked project does not contain SSH keys or Tailscale auth keys.

To add one SSH public key after setup, add these lines to the local `build/conf/local.conf` file before the build:

```bitbake
CORE_IMAGE_EXTRA_INSTALL:append = " ssh-keys"
SSH_AUTHORIZED_KEY = "ssh-ed25519 AAAA... user@host"
```

Do not commit that local configuration file.

To join Tailscale, start the device and run `tailscale up`. Complete the login step that Tailscale shows.

## Reproducibility

The setup script pins these external layers:

| Layer | Revision |
| --- | --- |
| meta-openembedded | `b5874ea07d69919d9b40d59f2c2f0bbd24bc3259` |
| meta-virtualization | `e066aa71b00d8ef5121fcab3a7ac813058cda09c` |
| meta-tegra | `0c507bfe8d64a0e113beeff8f45e7fe0dfb5bc80` |
| meta-tailscale | `c70a30954839eef1923627e3a2f056692611f789` |

The custom recipes in `meta-custom/` are part of this project. The source archives for the NVIDIA container library use fixed commit IDs and SHA-256 checksums.

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
