#!/usr/bin/env python3
"""
Setup script for performance testing.
Ensures all dependencies are properly installed.
"""

import subprocess
import sys


def check_playwright_installed():
    """Check if playwright is installed"""
    try:
        import playwright

        return True
    except ImportError:
        return False


def check_browsers_installed():
    """Check if playwright browsers are installed"""
    try:
        result = subprocess.run(
            ["playwright", "show-trace"], capture_output=True, text=True
        )
        # If chromium is mentioned in any error, it's likely not installed
        return "chromium" not in result.stderr.lower()
    except FileNotFoundError:
        return False


def main():
    print("Performance Test Setup")
    print("=" * 50)

    # Check playwright package
    print("\n1. Checking Playwright package...")
    if check_playwright_installed():
        print("   ✓ Playwright package is installed")
    else:
        print("   ✗ Playwright package is NOT installed")
        print("   Please install it with: pip install playwright")
        sys.exit(1)

    # Check browsers
    print("\n2. Checking Playwright browsers...")
    if check_browsers_installed():
        print("   ✓ Playwright browsers appear to be installed")
    else:
        print("   ⚠️  Playwright browsers may not be installed")
        print("\n   Installing Chromium browser...")

        try:
            subprocess.run(["playwright", "install", "chromium"], check=True)
            print("   ✓ Chromium browser installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"   ✗ Failed to install Chromium: {e}")
            sys.exit(1)

    print("\n✅ Setup complete! You can now run:")
    print("   python scripts/performance_test.py")


if __name__ == "__main__":
    main()
