#!/bin/bash
# Run tests in Playwright Docker container (matches CI environment)
# This ensures visual regression baselines match CI exactly.
#
# Usage:
#   ./scripts/test-docker.sh                    # Run all tests including visual
#   ./scripts/test-docker.sh -v                 # Run with verbose output
#   ./scripts/test-docker.sh --update-snapshots # Update visual baselines
#   ./scripts/test-docker.sh tests/test_theme_visual.py --update-snapshots
#
# The container uses the same image as CI, ensuring:
# - Identical font rendering (FreeType on Ubuntu)
# - Same browser version (pre-installed Chromium)
# - Consistent visual snapshots
#
# Note: --run-visual is automatically added to include visual regression tests.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Use -it only if we have a TTY
DOCKER_OPTS="--rm"
if [ -t 0 ]; then
  DOCKER_OPTS="--rm -it"
fi

docker run $DOCKER_OPTS \
  -v "$PROJECT_ROOT:/app" \
  -w /app/python \
  -e UV_PROJECT_ENVIRONMENT=/tmp/.venv \
  mcr.microsoft.com/playwright:v1.57.0-noble \
  bash -c "curl -LsSf https://astral.sh/uv/install.sh | sh && source \$HOME/.local/bin/env && uv sync && uv run pytest --run-visual $*"
