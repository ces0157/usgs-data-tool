#!/bin/bash
set -e

# Ensure script is run from project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_SCRIPT="$PROJECT_ROOT/src/cli.py"

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
echo "   usgs-download --help"