# Momonga ARM64 RPM repository: build, update, and publish

This section is the maintainer runbook for the extra-package RPM feed. RPMs are stored once in an append-only GitHub Release asset pool; signed repository metadata is published in immutable feed releases and served by GitHub Pages. It is not published to R2.

## Package scope and paths

- The custom layer is `meta-custom/`.
- Current package targets include Neovim, `bat`, `fzf`, `nodejs24`, Zsh, GDBM, Neofetch, Fastfetch, `momonga-locale`, ONNX, ONNX GraphSurgeon, Polygraphy, TensorRT Python bindings, `tegra-tools` (which outputs `tegra-tools-tegrastats`), and `python3-jetson-stats` (which provides `jtop`). Custom-layer RPMs depend on `momonga-locale`, which installs C.UTF-8 and sets it as the default locale. `nodejs24` packages upstream Node.js 24 ARM64 binaries and npm together. `fzf` packages its upstream ARM64 binary and MIT license; it does not currently package shell bindings or completions.
- The build/repository directory is `build-packages/tmp/deploy/rpm/armv8a_tegra/`. It contains the RPMs and generated `repodata/`.
- Keep `MOMONGA-RPM-FEED-PACKAGES.md` up to date whenever RPMs are built, added, removed, or published. Record the recipe targets and actual RPM package names/EVRs, and clearly distinguish local/unpublished builds from the contents of the latest published release; do not label a recipe as built until its RPM output exists.
- The DNF base URL is `https://kani.ftds.online/rpm/momonga/aarch64/`. The URL's `aarch64` is a public repository path; RPM filenames use Yocto's `armv8a_tegra` package architecture.
- The flash image's package selection is separate. `config/local.conf` contains `CORE_IMAGE_EXTRA_INSTALL`; the resolved installed-package list is in the image `.manifest` under `build/tmp/deploy/images/jetson-agx-xavier-devkit/` after a full image build.

## Build packages

Run from the Poky checkout:

```sh
source ./oe-init-build-env build-packages
bitbake bash bat diffutils fzf gdbm nano ncurses neovim nodejs24 \
  neofetch fastfetch momonga-locale ptest-runner python3 python3-distro glibc-locale \
  python3-jetson-stats python3-numpy python3-nvidia-ml-py python3-onnx \
  python3-onnx-graphsurgeon python3-polygraphy python3-smbus2 python3-tensorrt \
  tegra-tools tensorrt-trtexec-prebuilt zsh
```

For a single package, run `bitbake <recipe>` with its recipe name, for example `bitbake fzf`. BitBake builds that recipe and its task/build dependencies. It does not build a flash image. `bitbake package-index` indexes every RPM in the deploy directory; it does not build recipes. The deploy directory contains many build dependencies that are not part of the public feed, so do not publish its RPM wildcard.

Before updating an upstream package version, update the recipe filename/PV and verify source checksums. If package contents change without a version change, increment the package release (`PR`) so DNF sees a newer EVR. RPMs such as `-dbg`, `-dev`, `-doc`, `-src`, and `-ptest` are optional for normal target use; `nodejs24-dev` is useful when native npm add-ons must be built on Xavier. The fzf shell bindings/completions would need to be added separately if wanted.

The local Poky fork can diverge from `upstream/scarthgap`. Inspect upstream commits before merging:

```sh
git fetch upstream
git rev-list --left-right --count HEAD...upstream/scarthgap
git log --oneline HEAD..upstream/scarthgap
```

The last inspection found 11 commits unique to each side, including core security fixes. Merging upstream is a real merge, not a fast-forward. Preserve local work and coordinate core library/image changes with the full-image maintainer. Publishing the extra-package feed alone does not deliver Poky core security updates to Xavier.

## Sign RPMs and repository metadata

The signing key fingerprint is `BE27 4FDA FE86 B911 E0BA C3DB 5B2A A4FE 9449 ABF1`. Sign new or changed RPMs before building repository metadata. The passphrase is entered through GPG's pinentry; never put it in a command or file.

BitBake's native `rpmsign` can be found and run as follows. Set `RPM_FILES` to the unsigned or changed RPMs in the staged feed. Verify signatures against every staged RPM before publishing:

```sh
KEY=BE274FDAFE86B911E0BAC3DB5B2AA4FE9449ABF1
RPM_SIGN=$(find build-packages/tmp/work/x86_64-linux/rpm-native \
  -type f -path '*/recipe-sysroot-native/usr/bin/rpmsign' -print -quit)
RPM_USR=${RPM_SIGN%/bin/rpmsign}
export LD_LIBRARY_PATH="$RPM_USR/lib:$RPM_USR/lib/rpm${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

for rpm in $RPM_FILES; do
  "$RPM_SIGN" --addsign --define "_gpg_name $KEY" "$rpm"
done
```

After all package creation and RPM signing is complete, set `RPM_STAGE` to an empty staging directory under `/tmp/opencode/` and stage the **complete curated feed**: start with the prior curated RPM set, replace superseded package EVRs with the newly built outputs, and add new package outputs. Use `MOMONGA-RPM-FEED-PACKAGES.md` to verify names and EVRs. Do not include unrelated RPMs from the deploy directory. RPM files are served from the append-only `momonga-rpm-packages` release, so generate metadata with its exact GitHub Releases download base URL:

```sh
CREATEREPO=$(find build-packages/tmp/work/x86_64-linux/createrepo-c-native \
  -type f -path '*/recipe-sysroot-native/usr/bin/createrepo_c' -print -quit)
"$CREATEREPO" --database \
  --baseurl="https://github.com/ftulabs/momonga-os/releases/download/momonga-rpm-packages/" \
  "$RPM_STAGE"
```

Then create a detached ASCII-armored signature for the final `repomd.xml`:

```sh
SRC="$RPM_STAGE"
gpg --armor --detach-sign --local-user "$KEY" \
  --output "$SRC/repodata/repomd.xml.asc" \
  "$SRC/repodata/repomd.xml"
gpg --verify "$SRC/repodata/repomd.xml.asc" "$SRC/repodata/repomd.xml"
```

Do not rerun `bitbake package-index` after signing `repomd.xml`; regenerate and re-sign if metadata changes. The published public key must be `RPM-GPG-KEY-momonga`. Export only the public key; never export or upload the private key.

## Publish RPM assets and a feed release

The `momonga-rpm-packages` release is an append-only RPM asset pool. Upload only RPM filenames that are not already in it; never replace or re-upload an existing EVR. A feed release contains the public key and a metadata archive only. Use a new unique tag such as `momonga-rpm-feed-2026.10.08-3`; do not reuse or edit an older feed release. Commit and push approved recipe/workflow changes before tagging, so the release uses the intended workflow version.

The metadata asset must be named exactly `feed-repodata.tar.gz`, and it must contain the `repodata/` directory including `repomd.xml.asc`:

```sh
TAG=momonga-rpm-feed-YYYY.MM.DD-N
SRC="$PWD/build-packages/tmp/deploy/rpm/armv8a_tegra"
tar -C "$SRC" -czf /tmp/opencode/feed-repodata.tar.gz repodata

gh release upload momonga-rpm-packages "$RPM_FILES" \
  --repo ftulabs/momonga-os

git tag -a "$TAG" -m "$TAG"
git push origin "refs/tags/$TAG"
gh release create "$TAG" \
  "$SRC/RPM-GPG-KEY-momonga" \
  /tmp/opencode/feed-repodata.tar.gz \
  --repo ftulabs/momonga-os \
  --title "Momonga RPM feed update" \
  --notes "Signed Momonga ARM64 RPM repository metadata."
```

Create `momonga-rpm-packages` as a published release before the first upload. `gh release create` publishes the feed release immediately. A published `momonga-rpm-feed-*` release triggers `.github/workflows/publish-momonga-rpm-feed.yml`, which assembles metadata under `/rpm/momonga/aarch64/`, generates Jinja2 directory indexes with direct GitHub Releases RPM links, and deploys Pages. The workflow can also be run manually with `workflow_dispatch` and a published `release_tag`.

## Configure and update Xavier

Use this DNF repo configuration after the custom domain is reachable:

```ini
[momonga-extra]
name=Momonga Extra Packages
baseurl=https://kani.ftds.online/rpm/momonga/aarch64/
enabled=1
gpgcheck=1
gpgkey=https://kani.ftds.online/rpm/momonga/aarch64/RPM-GPG-KEY-momonga
repo_gpgcheck=1
```

`gpgcheck=1` verifies RPM signatures. `repo_gpgcheck=1` verifies the detached `repomd.xml.asc` with the same published key. After adding the file under `/etc/yum.repos.d/`, refresh and preview the transaction before installing:

```sh
sudo dnf makecache --refresh
sudo dnf --assumeno install fzf bat nodejs24 zsh
sudo dnf install fzf bat nodejs24 zsh
```

Neovim's prebuilt binary requires glibc 2.34 or newer; check Xavier's glibc before installing it. Node.js 24 requires glibc 2.28 or newer. Do not assume the target RPM solver checks every required symbol version.

The latest successful legacy feed release is `momonga-rpm-feed-2026.10.09-5`; its 315 RPMs must be uploaded to `momonga-rpm-packages` before publishing the first metadata-only feed release. It includes both `locale-base-c` and `glibc-binary-localedata-c` so existing systems can install C.UTF-8. The Pages workflow requires the metadata asset to be named exactly `feed-repodata.tar.gz`. Verify live RPM and metadata URLs after each release. The current Pages custom domain is `kani.ftds.online`; check its DNS/Pages configuration if the feed URL changes.
