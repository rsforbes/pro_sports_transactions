# Specify the Python version and base OS for the container
# VARIANT allows customization of Python version (default: 3.12 on Debian Bullseye)
ARG VARIANT="3.11-bullseye"

# Use Microsoft's official Python dev container as the base image
FROM mcr.microsoft.com/devcontainers/python:1-${VARIANT}

# Switch from root to the vscode user for security and proper file permissions
# The vscode user is pre-configured in the base image with development tools
USER vscode

# Download and install Poetry package manager for the vscode user
# Poetry manages Python dependencies and virtual environments
RUN curl -sSL https://install.python-poetry.org -o /tmp/install-poetry.py \
    && python3 /tmp/install-poetry.py \
    && rm /tmp/install-poetry.py

# Add Poetry's installation directory to the system PATH
# This allows the 'poetry' command to be run from anywhere
ENV PATH="/home/vscode/.local/bin:$PATH"

# Configure Poetry to create virtual environments inside the project directory
# This creates a .venv folder in your project root instead of Poetry's global cache
# This setting acts as a "gate" - it ensures proper environment setup before shells can run
# Set cache directory to /tmp to enable fast package downloads during build
# while preventing cache bloat in the final Docker image
RUN poetry config virtualenvs.in-project true \
    && poetry config cache-dir /tmp/poetry_cache

# Set the working directory where your project files will be mounted
# This is where VS Code will open and where your code will live
WORKDIR /workspace