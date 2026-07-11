# Specify the Python version and base OS for the container
# VARIANT allows customization of Python version (default: 3.11 on Debian Bullseye)
ARG VARIANT="3.11-bullseye"

# Use Microsoft's official Python dev container as the base image
FROM mcr.microsoft.com/devcontainers/python:1-${VARIANT}

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
