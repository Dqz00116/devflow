#!/usr/bin/env python3
"""Streamlined PyPI release script for agent-devflow.

Prevents common mistakes:
- Uploading stale artifacts from dist/
- Version mismatch between pyproject.toml and dist files
- Forgetting to bump version
- Accidentally including extra files in the distribution

Usage:
    uv run python scripts/release.py patch   # 0.1.4 -> 0.1.5
    uv run python scripts/release.py minor   # 0.1.4 -> 0.2.0
    uv run python scripts/release.py major   # 0.1.4 -> 1.0.0
    uv run python scripts/release.py --dry-run patch  # Preview only
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = PROJECT_ROOT / "pyproject.toml"
DIST_DIR = PROJECT_ROOT / "dist"

# Files that must stay in sync with pyproject.toml version
VERSION_SOURCES: list[tuple[Path, str, str]] = [
    # (path, read_pattern, replace_pattern)
    (
        PYPROJECT,
        r'^version\s*=\s*"([^"]+)"',
        r'^(version\s*=\s*")([^"]+)(")',
    ),
    (
        PROJECT_ROOT / "src" / "devflow" / "__init__.py",
        r'^__version__\s*=\s*"([^"]+)"',
        r'^(__version__\s*=\s*")([^"]+)(")',
    ),
    (
        PROJECT_ROOT / "src" / "devflow" / "config.py",
        r'^(\s+)version:\s*str\s*=\s*"([^"]+)"',
        r'^(\s+version:\s*str\s*=\s*")([^"]+)(")',
    ),
]


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a shell command and return the result."""
    return subprocess.run(
        cmd,
        cwd=cwd or PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=check,
    )


def get_current_version() -> str:
    """Read version from pyproject.toml."""
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise RuntimeError("Could not find version in pyproject.toml")
    return match.group(1)


def get_all_versions() -> dict[Path, str]:
    """Read version from all tracked source files."""
    versions: dict[Path, str] = {}
    for path, read_re, _ in VERSION_SOURCES:
        text = path.read_text(encoding="utf-8")
        match = re.search(read_re, text, re.MULTILINE)
        if not match:
            raise RuntimeError(f"Could not find version in {path}")
        versions[path] = match.group(match.lastindex)
    return versions


def check_version_consistency(expected: str) -> dict[Path, str]:
    """Return files whose version does not match *expected*."""
    versions = get_all_versions()
    return {path: v for path, v in versions.items() if v != expected}


def bump_version(current: str, level: str) -> str:
    """Bump version string: patch/minor/major."""
    parts = current.split(".")
    if len(parts) != 3:
        raise ValueError(f"Expected semver X.Y.Z, got: {current}")
    major, minor, patch = map(int, parts)
    if level == "patch":
        patch += 1
    elif level == "minor":
        minor += 1
        patch = 0
    elif level == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        raise ValueError(f"Unknown bump level: {level}")
    return f"{major}.{minor}.{patch}"


def set_all_versions(new_version: str) -> None:
    """Write new version to all tracked source files."""
    for path, _, replace_re in VERSION_SOURCES:
        text = path.read_text(encoding="utf-8")
        new_text = re.sub(
            replace_re,
            rf'\g<1>{new_version}\g<3>',
            text,
            flags=re.MULTILINE,
        )
        if new_text == text:
            raise RuntimeError(f"Version replacement failed in {path} — file unchanged")
        path.write_text(new_text, encoding="utf-8")
    print(f"  Updated version to {new_version} in {len(VERSION_SOURCES)} file(s).")


def clean_dist() -> None:
    """Remove all files in dist/ directory."""
    if DIST_DIR.exists():
        for item in DIST_DIR.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        print(f"  Cleaned {DIST_DIR} ({len(list(DIST_DIR.iterdir()))} items remaining)")
    else:
        DIST_DIR.mkdir(parents=True, exist_ok=True)
        print(f"  Created {DIST_DIR}")


def build() -> list[Path]:
    """Build source distribution and wheel."""
    result = run(["uv", "build"])
    if result.returncode != 0:
        print(f"Build failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    artifacts = sorted(DIST_DIR.iterdir())
    print(f"  Built {len(artifacts)} artifact(s):")
    for a in artifacts:
        print(f"    - {a.name}")
    return artifacts


def verify_artifacts(version: str, artifacts: list[Path]) -> None:
    """Ensure dist contains exactly the expected files for this version."""
    expected = {
        f"agent_devflow-{version}-py3-none-any.whl",
        f"agent_devflow-{version}.tar.gz",
    }
    actual = {a.name for a in artifacts if a.name != ".gitignore"}
    if actual != expected:
        print(f"Artifact mismatch!", file=sys.stderr)
        print(f"  Expected: {sorted(expected)}", file=sys.stderr)
        print(f"  Actual:   {sorted(actual)}", file=sys.stderr)
        sys.exit(1)
    print("  Artifact verification passed.")


def check_git_clean() -> bool:
    """Check if working tree is clean."""
    result = run(["git", "status", "--porcelain"], check=False)
    return result.stdout.strip() == ""


def git_commit_version(version: str) -> None:
    """Stage all version files and create version bump commit."""
    paths = [str(p.relative_to(PROJECT_ROOT)) for p, _, _ in VERSION_SOURCES]
    run(["git", "add", *paths])
    run(["git", "commit", "-m", f"chore: bump version to {version}"])
    print(f"  Committed version bump.")


def git_tag(version: str) -> None:
    """Create an annotated git tag."""
    tag = f"v{version}"
    run(["git", "tag", "-a", tag, "-m", f"Release {tag}"])
    print(f"  Created tag {tag}.")


def git_push(with_tags: bool = False) -> None:
    """Push current branch to origin."""
    run(["git", "push"])
    print("  Pushed commits.")
    if with_tags:
        run(["git", "push", "--tags"])
        print("  Pushed tags.")


def publish() -> None:
    """Upload to PyPI via twine (respects .pypirc)."""
    result = run(["uv", "run", "twine", "upload", "dist/*"])
    if result.returncode != 0:
        print(f"Upload failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    print("  Uploaded to PyPI.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Release agent-devflow to PyPI")
    parser.add_argument(
        "level",
        choices=["patch", "minor", "major"],
        help="Version bump level",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without executing",
    )
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="Skip git commit/tag/push",
    )
    parser.add_argument(
        "--no-tag",
        action="store_true",
        help="Skip git tag creation (implies --no-git has no effect on tag)",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("PyPI Release — agent-devflow")
    print("=" * 50)

    # 1. Detect current version
    current = get_current_version()
    print(f"\n1. Current version: {current}")

    # 2. Check version consistency across source files
    print("\n2. Checking version consistency...")
    mismatches = check_version_consistency(current)
    if mismatches:
        print("  WARNING: Version mismatch detected:")
        for path, v in sorted(mismatches.items(), key=lambda x: str(x[0])):
            rel = path.relative_to(PROJECT_ROOT)
            print(f"    {rel}: {v} (expected {current})")
        if not args.dry_run:
            response = input("  Versions are inconsistent. Continue anyway? [y/N] ")
            if response.lower() not in ("y", "yes"):
                print("  Aborted.")
                return 1
        else:
            print("  [DRY RUN] Would abort or prompt for inconsistent versions.")
    else:
        print("  All source files are consistent.")

    new_version = bump_version(current, args.level)
    print(f"\n3. Version bump: {current} -> {new_version}")

    # 4. Check git status
    is_clean = check_git_clean()
    if not is_clean:
        print("\n  WARNING: Working tree has uncommitted changes.")
        print("  Run 'git status' to review.")
        if not args.dry_run:
            response = input("  Continue anyway? [y/N] ")
            if response.lower() not in ("y", "yes"):
                print("  Aborted.")
                return 1

    if args.dry_run:
        print("\n  [DRY RUN] No changes made.")
        return 0

    # 5. Clean dist
    print("\n4. Cleaning dist/...")
    clean_dist()

    # 6. Bump version in all source files
    print("\n5. Bumping version...")
    set_all_versions(new_version)

    # 7. Build
    print("\n6. Building...")
    artifacts = build()

    # 8. Verify artifacts
    print("\n7. Verifying artifacts...")
    verify_artifacts(new_version, artifacts)

    # 9. Git commit
    if not args.no_git:
        print("\n8. Committing version bump...")
        git_commit_version(new_version)

        if not args.no_tag:
            print("\n9. Creating git tag...")
            git_tag(new_version)

        print("\n10. Pushing to origin...")
        git_push(with_tags=not args.no_tag)
    else:
        print("\n8. Skipping git operations (--no-git).")

    # 12. Publish
    print("\n11. Publishing to PyPI...")
    publish()

    print("\n" + "=" * 50)
    print(f"Done! agent-devflow {new_version} released.")
    print(f"  PyPI: https://pypi.org/project/agent-devflow/{new_version}/")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())
