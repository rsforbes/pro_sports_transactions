# Specify the Python version and base OS for the container
# VARIANT allows customization of Python version (default: 3.11 on Debian Bookworm)
ARG VARIANT="3.11-bookworm"

# Use Microsoft's official Python dev container as the base image
FROM mcr.microsoft.com/devcontainers/python:1-${VARIANT}

# Browser stack for NodriverRequestHandler (the [nodriver] extra), which drives a
# real Chrome to solve the Cloudflare challenge:
# - google-chrome-stable: branded Chrome is required; unbranded Chromium is
#   detected by Cloudflare and never clears the challenge.
# - xvfb: virtual display. The challenge is not reliably solved headless, so
#   run live nodriver code under `xvfb-run` in this display-less container.
# - libgl1: needed to import opencv-python, which backs nodriver's verify_cf().
# The base image's Yarn apt source (unused here) has carried an expired signing
# key that makes `apt-get update` fail, so drop it first.
# Google ships Linux Chrome for amd64 only; on other architectures (e.g. arm64
# on Apple Silicon) Chrome is skipped so the container still builds, and the
# live nodriver integration test skips itself.
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && CHROME_DEB="" \
    && if [ "$(dpkg --print-architecture)" = "amd64" ]; then \
        curl -fsSLo /tmp/chrome.deb \
            https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
        && CHROME_DEB=/tmp/chrome.deb; \
    fi \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        $CHROME_DEB xvfb xauth libgl1 \
    && rm -rf /tmp/chrome.deb /var/lib/apt/lists/*

# Switch from root to the vscode user for security and proper file permissions
# The vscode user is pre-configured in the base image with development tools
USER vscode

# Install uv, the Python package/project manager that replaces Poetry.
# The installer drops the `uv`/`uvx` binaries into ~/.local/bin.
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv's installation directory to the system PATH
# This allows the 'uv' command to be run from anywhere
ENV PATH="/home/vscode/.local/bin:$PATH"

# Keep uv's project virtualenv inside the workspace (./.venv) and put its cache
# on /tmp so it speeds up installs during the build without bloating the image.
ENV UV_PROJECT_ENVIRONMENT="/workspace/.venv" \
    UV_CACHE_DIR="/tmp/uv-cache"

# Set the working directory where your project files will be mounted
# This is where VS Code will open and where your code will live
WORKDIR /workspace
