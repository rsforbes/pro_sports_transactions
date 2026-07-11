#!/bin/bash
# Shebang: tells the system to execute this script using bash

# Exit immediately if any command fails (prevents partial setup)
# This ensures the development environment is either fully set up or fails clearly
set -e

# Display status message to user during container setup
echo "Setting up development environment..."

# Install all dependencies (including the dev group) from pyproject.toml and
# uv.lock into ./.venv. --frozen fails loudly if the lock is out of sync rather
# than silently re-resolving, so the container matches CI exactly.
uv sync --frozen

# Configure shell activation for all future terminal sessions so the project's
# .venv is active in every new terminal. Guarded so a missing venv is not fatal.
echo 'source /workspace/.venv/bin/activate 2>/dev/null || true' >> ~/.bashrc

# Display completion message to user
echo "Setup complete! uv environment activated."
