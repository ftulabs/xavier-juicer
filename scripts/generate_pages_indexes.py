#!/usr/bin/env python3
"""Generate Apache-style static directory indexes for a GitHub Pages tree."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape


def display_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TiB"


def release_rpm_entries(
    assets_json: Path, repository: str, release_tag: str
) -> list[dict[str, str]]:
    """Return directory entries for RPM assets stored in a GitHub release."""
    try:
        assets = json.loads(assets_json.read_text(encoding="utf-8"))["assets"]
    except (json.JSONDecodeError, KeyError, OSError) as error:
        raise SystemExit(f"Cannot read GitHub release assets from {assets_json}: {error}") from error

    base_url = (
        f"https://github.com/{repository}/releases/download/"
        f"{quote(release_tag, safe='@:+,.-_~')}/"
    )
    entries = []
    for asset in assets:
        name = asset.get("name")
        if not isinstance(name, str) or not name.endswith(".rpm"):
            continue
        size = asset.get("size")
        updated_at = asset.get("updatedAt")
        try:
            modified = datetime.fromisoformat(updated_at.replace("Z", "+00:00")).strftime(
                "%Y-%m-%d %H:%M UTC"
            )
        except (AttributeError, ValueError):
            modified = "—"
        entries.append(
            {
                "name": name,
                "href": base_url + quote(name, safe="@:+,.-_~"),
                "kind": "RPM",
                "modified": modified,
                "size": display_size(size) if isinstance(size, int) else "—",
            }
        )

    if not entries:
        raise SystemExit(f"No RPM assets found in GitHub release {release_tag}")
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="root of the Pages site")
    parser.add_argument("--template", required=True, type=Path, help="Jinja2 HTML template")
    parser.add_argument(
        "--rpm-assets-json",
        type=Path,
        help="GitHub release-view JSON containing the append-only RPM asset pool",
    )
    parser.add_argument(
        "--release-repository",
        help="GitHub owner/repository for direct RPM download links",
    )
    parser.add_argument(
        "--asset-release-tag",
        help="GitHub Release tag containing the RPM asset pool",
    )
    args = parser.parse_args()

    remote_rpms = []
    remote_options = (args.rpm_assets_json, args.release_repository, args.asset_release_tag)
    if any(remote_options) and not all(remote_options):
        parser.error(
            "--rpm-assets-json, --release-repository, and --asset-release-tag must be used together"
        )
    if args.rpm_assets_json:
        remote_rpms = release_rpm_entries(
            args.rpm_assets_json, args.release_repository, args.asset_release_tag
        )

    root = args.root.resolve()
    template_path = args.template.resolve()
    env = Environment(
        loader=FileSystemLoader(template_path.parent),
        autoescape=select_autoescape(("html", "j2")),
    )
    template = env.get_template(template_path.name)

    for directory in sorted(path for path in root.rglob("*") if path.is_dir()) + [root]:
        children = []
        for child in sorted(directory.iterdir(), key=lambda item: (item.is_file(), item.name.casefold())):
            if child.name == "index.html":
                continue
            is_directory = child.is_dir()
            children.append(
                {
                    "name": child.name + ("/" if is_directory else ""),
                    "href": quote(child.name, safe="@:+,.-_~") + ("/" if is_directory else ""),
                    "kind": "Directory" if is_directory else "File",
                    "modified": datetime.fromtimestamp(
                        child.stat().st_mtime, timezone.utc
                    ).strftime("%Y-%m-%d %H:%M UTC"),
                    "size": "—" if is_directory else display_size(child.stat().st_size),
                }
            )

        # Pages intentionally contains metadata only.  Show RPMs from the
        # release asset pool at the repository root as direct download links.
        if directory == root / "rpm/momonga/aarch64":
            children.extend(remote_rpms)
            children.sort(key=lambda entry: (entry["kind"] != "Directory", entry["name"].casefold()))

        relative = directory.relative_to(root).as_posix()
        display_path = "/" if relative == "." else f"/{relative}/"
        rendered = template.render(
            title=f"Index of {display_path}",
            path=display_path,
            parent_href=None if directory == root else "../",
            entries=children,
        )
        (directory / "index.html").write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
