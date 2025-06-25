ARG VARIANT="3.11-bullseye"
FROM mcr.microsoft.com/devcontainers/python:1-${VARIANT}

# Switch to vscode user and install Poetry for this user
USER vscode

# Install Poetry for the vscode user
RUN curl -sSL https://install.python-poetry.org -o /tmp/install-poetry.py \
    && python3 /tmp/install-poetry.py \
    && rm /tmp/install-poetry.py

# Add Poetry to PATH for vscode user
ENV PATH="/home/vscode/.local/bin:$PATH"

# Configure Poetry to create virtual environments inside the project directory
# This creates a .venv folder in your project root instead of Poetry's global cache
# This setting acts as a "gate" - it ensures proper environment setup before shells can run
# Set cache directory to /tmp to enable fast package downloads during build
# while preventing cache bloat in the final Docker image
RUN poetry config virtualenvs.in-project true \
    && poetry config cache-dir /tmp/poetry_cache

# Set working directory
WORKDIR /workspace

# The project files will be mounted/available via the devcontainer
# No need to copy since we're using the project directory directly