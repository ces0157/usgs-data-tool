#!/usr/bin/env bash
set -e

# Ensure script is run from project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_SCRIPT="$PROJECT_ROOT/src/cli.py"

# --- Conda environment setup ---
ENV_NAME="usgs-env"
PYTHON_VERSION="3.10"

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "❌ Conda not found. Please install Miniconda or Anaconda first."
    exit 1
fi

# Create conda environment if it doesn't exist
if ! conda env list | grep -q "^${ENV_NAME} "; then
    echo "Creating conda environment: $ENV_NAME"
    conda create -y -n "$ENV_NAME" python=$PYTHON_VERSION
else
    echo "Conda environment '$ENV_NAME' already exists, skipping creation."
fi

# Activate the environment
echo "Activating conda environment: $ENV_NAME"
# shellcheck disable=SC1091
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_NAME"

# Install PDAL + Python bindings from conda-forge
echo "Installing PDAL and Python bindings..."
conda install -y -c conda-forge pdal python-pdal

# --- Project-specific setup ---

# 1. Install Python dependencies
if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    echo "Installing requirements..."
    pip install -r "$PROJECT_ROOT/requirements.txt"
else
    echo "No requirements.txt found!"
    exit 1
fi

# 2. Make cli.py executable
chmod +x "$CLI_SCRIPT"

# 3. Create symlink in ~/.local/bin
TARGET="$HOME/.local/bin/usgs-download"
mkdir -p "$HOME/.local/bin"

# Remove existing symlink if present
if [ -L "$TARGET" ]; then
    rm "$TARGET"
fi

ln -s "$CLI_SCRIPT" "$TARGET"
echo "Created symlink: $TARGET -> $CLI_SCRIPT"

# 4. Add ~/.local/bin to PATH if not already
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    echo "Added ~/.local/bin to PATH. Restart your terminal or run: source ~/.bashrc"
fi

echo "✅ Installation complete! You can now run:"
echo "   conda activate $ENV_NAME"
echo "   usgs-download --help"