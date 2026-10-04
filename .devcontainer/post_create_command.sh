#!/bin/bash
# Shebang: tells the system to execute this script using bash

# Exit immediately if any command fails (prevents partial setup)
# This ensures the development environment is either fully set up or fails clearly
set -e

# Display status message to user during container setup
echo "Setting up development environment..."

# The ~/.claude directory is backed by a named volume (see devcontainer.json)
# so Claude Code history/memory survives rebuilds. Named volumes mount
# root-owned on first creation, so hand ownership to the vscode user.
sudo chown -R vscode:vscode /home/vscode/.claude 2>/dev/null || true

# Install all dependencies (including the dev group and optional extras such as
# [nodriver]) from pyproject.toml and uv.lock into ./.venv. --frozen fails
# loudly if the lock is out of sync rather than silently re-resolving, so the
# container matches CI exactly.
uv sync --frozen --all-extras

# Enable the repo's git hooks (.githooks/pre-commit runs the checks in
# .pre-commit-config.yaml on every commit). The setting lives in .git/config,
# which the host shares, so commits made outside the container are checked
# too. Skipped, not fatal, when git can't use /workspace: it isn't a checkout
# (e.g. a downloaded zip), or git refuses it (e.g. "dubious ownership" on a
# bind mount); git's own message is printed so the cause is visible.
if git_error=$(git -C /workspace rev-parse --git-dir 2>&1 >/dev/null); then
    git -C /workspace config core.hooksPath .githooks
else
    echo "Skipping git hook setup: ${git_error}"
fi

# Configure shell activation for all future terminal sessions so the project's
# .venv is active in every new terminal. Guarded so a missing venv is not fatal.
echo 'source /workspace/.venv/bin/activate 2>/dev/null || true' >> ~/.bashrc

# Display completion message to user
echo "Setup complete! uv environment activated."
