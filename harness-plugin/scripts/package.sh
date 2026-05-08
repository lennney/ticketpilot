#!/bin/bash
# Package the harness plugin for distribution
# Cross-platform: supports Linux, Mac, WSL, and Windows Git Bash/MSYS2

set -e

# --- Platform Detection ---
detect_platform() {
    # Check for WSL first (WSL sets WSL_DISTRO_NAME or has WSL in /proc/version)
    if [[ -n "${WSL_DISTRO_NAME:-}" ]] || grep -qi "wsl\|microsoft" /proc/version 2>/dev/null; then
        echo "wsl"
        return
    fi
    
    case "$(uname -s)" in
        Linux*)     echo "linux";;
        Darwin*)    echo "mac";;
        MINGW*|MSYS*|CYGWIN*) echo "windows";;
        *)          echo "linux";;
    esac
}

# --- Find Python interpreter (that actually works) ---
find_python() {
    # Try python3 first (check if it actually works)
    if command -v python3 &> /dev/null; then
        if python3 --version &> /dev/null; then
            echo "python3"
            return
        fi
    fi
    # Try python
    if command -v python &> /dev/null; then
        if python --version &> /dev/null; then
            echo "python"
            return
        fi
    fi
    # Try direct paths (Windows common locations)
    if [[ -f /c/Users/len/AppData/Local/Programs/Python/Python310/python.exe ]]; then
        echo "/c/Users/len/AppData/Local/Programs/Python/Python310/python.exe"
        return
    fi
    if [[ -f /c/Users/len/AppData/Local/Programs/Python/Python39/python.exe ]]; then
        echo "/c/Users/len/AppData/Local/Programs/Python/Python39/python.exe"
        return
    fi
    echo ""
}

# --- Main ---
PLATFORM=$(detect_platform)
echo "Detected platform: $PLATFORM"

# Get script directory - handle UNC paths in MSYS2/WSL Git Bash
SCRIPT_SOURCE="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_SOURCE")" && pwd -W 2>/dev/null || pwd)"

# Get parent directory (PLUGIN_DIR)
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"

echo "Plugin dir: $PLUGIN_DIR"
echo ""

# Change to plugin directory first - this avoids UNC path issues in MSYS2
cd "$PLUGIN_DIR" || {
    echo "Error: Cannot access plugin directory: $PLUGIN_DIR"
    exit 1
}

# Create dist directory (using relative path)
DIST_DIR="dist"
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

echo "Packaging Controller Harness Plugin..."
echo ""

# Get version from plugin.json if exists
VERSION="1.0.0"
if [[ -f plugin.json ]]; then
    VERSION=$(grep -o '"version": *"[^"]*"' plugin.json 2>/dev/null | head -1 | sed 's/.*: *"\([^"]*\)"/\1/' || echo "1.0.0")
fi

ARCHIVE_NAME="controller-harness-${VERSION}"

# Create tarball (Unix/Linux/WSL/Mac)
echo "Creating tar.gz archive..."
tar -czf "$DIST_DIR/${ARCHIVE_NAME}.tar.gz" \
    --exclude='.git' \
    --exclude='dist' \
    --exclude='*.zip' \
    --exclude='node_modules' \
    .

# Create zip (cross-platform compatible, no symlinks)
echo "Creating zip archive..."
PYTHON=$(find_python)
if [[ -n "$PYTHON" ]]; then
    $PYTHON -c "
import zipfile
import os
import sys

dist_dir = sys.argv[1]
name = sys.argv[2]

with zipfile.ZipFile(f'{dist_dir}/{name}.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk('.'):
        # Skip excluded dirs
        dirs[:] = [d for d in dirs if d not in ['.git', 'dist', 'node_modules']]
        for file in files:
            if file.endswith('.zip'):
                continue
            filepath = os.path.join(root, file)
            arcname = filepath[2:] if filepath.startswith('./') else filepath
            zf.write(filepath, arcname)
print(f'Created {dist_dir}/{name}.zip')
" "$DIST_DIR" "$ARCHIVE_NAME"
elif command -v zip &> /dev/null; then
    # Fallback to zip command
    zip -r "$DIST_DIR/${ARCHIVE_NAME}.zip" \
        --exclude='.git/*' \
        --exclude='dist/*' \
        --exclude='node_modules/*' \
        --exclude='*.zip' \
        .
else
    echo "Warning: Neither python nor zip found. Skipping .zip archive."
fi

echo ""
echo "Package created:"
ls -la "$DIST_DIR/"

echo ""
echo "Distribution files:"
echo "  dist/${ARCHIVE_NAME}.tar.gz (Unix/Linux/WSL/Mac)"
[[ -f "$DIST_DIR/${ARCHIVE_NAME}.zip" ]] && echo "  dist/${ARCHIVE_NAME}.zip (Windows)"
