#!/usr/bin/env bash
set -e

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_SCRIPT="$PROJECT_ROOT/src/cli.py"

# Python virtual environment setup
ENV_DIR="$PROJECT_ROOT/.venv"
PYTHON_BIN="python3.10"

# Check if python3.10 is available
if ! command -v $PYTHON_BIN &> /dev/null; then
    echo "Error: $PYTHON_BIN not found. Please install it first."
    exit 1
fi

# Create venv if it doesn't exist
if [ ! -d "$ENV_DIR" ]; then
    echo "Creating virtual environment..."
    $PYTHON_BIN -m venv "$ENV_DIR"
else
    echo "Virtual environment already exists, skipping creation."
fi

# Activate venv and upgrade pip
source "$ENV_DIR/bin/activate"
pip install --upgrade pip

# Install dependencies
if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    echo "Installing requirements..."
    pip install -r "$PROJECT_ROOT/requirements.txt"
    pip install -e .
else
    echo "No requirements.txt found!"
    exit 1
fi

# Make cli.py executable and create symlink
chmod +x "$CLI_SCRIPT"

TARGET="$HOME/.local/bin/usgs-download"
mkdir -p "$HOME/.local/bin"

# Remove existing symlink if present
[ -L "$TARGET" ] && rm "$TARGET"

ln -s "$CLI_SCRIPT" "$TARGET"
echo "Created symlink: $TARGET -> $CLI_SCRIPT"

# Add ~/.local/bin to PATH if not already there
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    echo "Added ~/.local/bin to PATH. Restart your terminal or run: source ~/.bashrc"
fi

echo "Installation complete! Run these commands to get started:"
echo "   source $ENV_DIR/bin/activate"
echo "   usgs-download --help"
