#!/usr/bin/env python3
"""
Smart publishing script for cao package.
This script automates the release process for publishing to PyPI and updating Homebrew formula.
"""

import os
import re
import sys
import subprocess
import argparse
import json
import hashlib
from pathlib import Path
import shutil


def get_current_version():
    """Extract current version from setup.py."""
    with open("setup.py", "r", encoding="utf-8") as f:
        content = f.read()
        match = re.search(r'version="([^"]+)"', content)
        if match:
            return match.group(1)
    return None


def update_version(new_version):
    """Update version in setup.py."""
    current_version = get_current_version()
    if not current_version:
        print("Error: Could not find version in setup.py")
        return False

    with open("setup.py", "r", encoding="utf-8") as f:
        content = f.read()

    updated_content = content.replace(
        f'version="{current_version}"', f'version="{new_version}"'
    )

    with open("setup.py", "w", encoding="utf-8") as f:
        f.write(updated_content)

    print(f"Updated version in setup.py: {current_version} -> {new_version}")
    return True


def create_git_tag(version):
    """Create and push a git tag."""
    tag = f"v{version}"
    try:
        # Check if tag already exists
        result = subprocess.run(
            ["git", "tag", "-l", tag], 
            capture_output=True, 
            text=True, 
            check=True
        )
        if tag in result.stdout:
            print(f"Warning: Tag {tag} already exists!")
            choice = input("Do you want to force update this tag? [y/N] ").lower()
            if choice == 'y':
                subprocess.run(["git", "tag", "-d", tag], check=True)
            else:
                print("Skipping tag creation.")
                return False

        # Add and commit setup.py with version change
        subprocess.run(["git", "add", "setup.py"], check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Bump version to {version}"], 
            check=True
        )
        
        # Create and push the tag
        subprocess.run(
            ["git", "tag", "-a", tag, "-m", f"Release {tag}"], 
            check=True
        )
        subprocess.run(["git", "push", "origin", "HEAD"], check=True)
        subprocess.run(["git", "push", "origin", tag], check=True)
        print(f"Created and pushed git tag: {tag}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error in git operations: {e}")
        return False


def build_package():
    """Build the distribution packages."""
    try:
        # Clean previous builds
        if os.path.exists("dist"):
            shutil.rmtree("dist")
        if os.path.exists("build"):
            shutil.rmtree("build")
        for path in Path(".").glob("*.egg-info"):
            shutil.rmtree(path)

        # Install build if not already installed
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "build"],
            check=True
        )

        # Build distribution packages
        subprocess.run(
            [sys.executable, "-m", "build"], 
            check=True
        )
        print("Successfully built package")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error building package: {e}")
        return False


def calculate_sha256(version):
    """Calculate SHA256 hash for GitHub release tarball."""
    try:
        url = f"https://github.com/zhouatie/cao/archive/refs/tags/v{version}.tar.gz"
        result = subprocess.run(
            ["curl", "-sL", url],
            capture_output=True,
            check=True
        )
        sha256 = hashlib.sha256(result.stdout).hexdigest()
        print(f"SHA256 for v{version}: {sha256}")
        return sha256
    except subprocess.CalledProcessError as e:
        print(f"Error calculating SHA256: {e}")
        print("You may need to manually create a GitHub release first.")
        return None


def upload_to_pypi(test=False):
    """Upload the package to PyPI or TestPyPI."""
    try:
        # Install twine if not already installed
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "twine"],
            check=True
        )

        # Upload to PyPI or TestPyPI
        cmd = [sys.executable, "-m", "twine", "upload", "dist/*"]
        if test:
            cmd.extend(["--repository", "testpypi"])
            print("Uploading to TestPyPI...")
        else:
            print("Uploading to PyPI...")
            
        result = subprocess.run(cmd, check=True)
        print("Successfully uploaded package")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error uploading to {'TestPyPI' if test else 'PyPI'}: {e}")
        return False


def update_homebrew(version, sha256=None):
    """Provide instructions for updating the Homebrew formula."""
    if not sha256:
        print("\nCouldn't automatically calculate SHA256.")
        print("Please manually calculate it with:")
        print(f"curl -sL https://github.com/zhouatie/cao/archive/refs/tags/v{version}.tar.gz | shasum -a 256")

    print("\nTo update the Homebrew formula:")
    print("1. Edit your Homebrew formula (cao.rb)")
    print("2. Update the URL to:")
    print(f"   url \"https://github.com/zhouatie/cao/archive/refs/tags/v{version}.tar.gz\"")
    if sha256:
        print("3. Update the sha256 to:")
        print(f"   sha256 \"{sha256}\"")
    print("\nAfter updating, remember to test with:")
    print("   brew update")
    print("   brew upgrade cao")


def test_installation(version):
    """Test installation from PyPI."""
    try:
        print("\nTesting pip installation...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--force-reinstall", "zhouatie-cao"],
            check=True
        )
        print("Installation successful!")
        
        # Try running the package
        print("Testing cao command...")
        result = subprocess.run(
            ["cao", "--version"], 
            capture_output=True,
            text=True
        )
        if version in result.stdout:
            print(f"Success! Installed version: {result.stdout.strip()}")
        else:
            print(f"Warning: Version mismatch. Expected: {version}, Got: {result.stdout.strip()}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error testing installation: {e}")
        return False
    except FileNotFoundError:
        print("Warning: cao command not found in PATH after installation")
        return False


def main():
    parser = argparse.ArgumentParser(description="Smart publish script for cao package.")
    parser.add_argument(
        "--version", 
        help="Specify version to release (if not provided, increment patch version)"
    )
    parser.add_argument(
        "--test", 
        action="store_true", 
        help="Upload to TestPyPI instead of PyPI"
    )
    parser.add_argument(
        "--skip-build", 
        action="store_true", 
        help="Skip building the package"
    )
    parser.add_argument(
        "--skip-upload", 
        action="store_true", 
        help="Skip uploading to PyPI"
    )
    parser.add_argument(
        "--skip-git", 
        action="store_true", 
        help="Skip git operations"
    )
    parser.add_argument(
        "--skip-test", 
        action="store_true", 
        help="Skip installation test"
    )

    args = parser.parse_args()

    # Get current version and determine new version
    current_version = get_current_version()
    if not current_version:
        print("Error: Could not determine current version.")
        return 1

    if args.version:
        new_version = args.version
    else:
        # Auto-increment patch version
        version_parts = current_version.split('.')
        version_parts[-1] = str(int(version_parts[-1]) + 1)
        new_version = '.'.join(version_parts)

    print(f"Current version: {current_version}")
    print(f"New version: {new_version}")
    
    # Confirm with user
    choice = input("Proceed with release? [y/N] ").lower()
    if choice != 'y':
        print("Release cancelled.")
        return 0

    # Update version in setup.py
    if not update_version(new_version):
        return 1

    # Git operations: commit and tag
    if not args.skip_git:
        if not create_git_tag(new_version):
            print("Warning: Git operations failed. Continuing...")

    # Build package
    if not args.skip_build:
        if not build_package():
            return 1

    # Upload to PyPI
    if not args.skip_upload:
        if not upload_to_pypi(args.test):
            return 1

    # Calculate SHA256 for Homebrew formula
    sha256 = None
    if not args.skip_git:
        sha256 = calculate_sha256(new_version)

    # Provide instructions for Homebrew formula update
    update_homebrew(new_version, sha256)

    # Test installation
    if not args.skip_test:
        test_installation(new_version)

    print(f"\nRelease v{new_version} completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
