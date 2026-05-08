#!/bin/bash
# Controller Harness Plugin Installer
# Cross-platform: supports Linux, Mac, WSL, and Windows Git Bash/MSYS2
#
# Installs the Controller Harness into Claude Code's skills directory.
# Supports both global (~/.claude/skills/) and project-level installation.

set -e

# Colors (with fallback for terminals that don't support ANSI)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory - handle UNC paths in MSYS2/WSL Git Bash
SCRIPT_SOURCE="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_SOURCE")" && pwd -W 2>/dev/null || pwd)"

# Get plugin directory (parent of scripts/)
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"

usage() {
    echo "Controller Harness Plugin Installer"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --global    Install globally (~/.claude/skills/controller-harness)"
    echo "  --local     Install in current project (.claude/skills/)"
    echo "  --uninstall Remove installed plugin"
    echo "  --help      Show this help message"
    echo ""
    echo "Default: Global installation"
}

# --- Copy directory contents (cross-platform) ---
copy_plugin() {
    local src="$1"
    local dest="$2"
    
    if [[ -d "$src" ]]; then
        mkdir -p "$dest"
        # Use rsync if available for better handling of special files
        if command -v rsync &> /dev/null; then
            rsync -av --exclude='.git' --exclude='dist' --exclude='*.zip' "$src/" "$dest/"
        else
            # Copy with exclusions using find/cp
            (cd "$src" && find . -maxdepth 1 -type f ! -name '*.zip' -exec cp --target-directory="$dest" {} + 2>/dev/null || true)
            # Copy subdirectories
            find "$src" -mindepth 1 -maxdepth 1 -type d ! -name '.git' ! -name 'dist' -exec cp -r {} "$dest/" \;
        fi
    fi
}

install_global() {
    echo -e "${BLUE}Installing Controller Harness globally...${NC}"
    
    # Determine home directory
    local home_dir="$HOME"
    
    # Handle HOME on Windows MSYS2/WSL (could be Windows path)
    if [[ "$home_dir" == /c/* ]] && command -v cygpath &> /dev/null; then
        # Convert Windows path to MSYS path if needed
        home_dir="$HOME"  # Keep as-is for MSYS2 compatibility
    fi
    
    TARGET_DIR="$home_dir/.claude/skills/controller-harness"
    
    # Check if already installed
    if [[ -d "$TARGET_DIR" ]]; then
        echo -e "${YELLOW}Plugin already installed at $TARGET_DIR${NC}"
        if [[ -t 0 ]]; then  # Only ask if stdin is a terminal
            read -p "Replace existing installation? [y/N] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Installation cancelled."
                exit 0
            fi
        else
            echo "Replacing existing installation..."
        fi
        rm -rf "$TARGET_DIR"
    fi
    
    mkdir -p "$TARGET_DIR"
    copy_plugin "$PLUGIN_DIR" "$TARGET_DIR"
    
    echo -e "${GREEN}Installed to $TARGET_DIR${NC}"
    echo ""
    echo "To activate, restart Claude Code or run:"
    echo "  source ~/.claude/settings.json"
}

install_local() {
    echo -e "${BLUE}Installing Controller Harness in project...${NC}"
    
    # Check if in a git repo
    if [[ ! -d ".git" ]]; then
        echo -e "${RED}Error: Not in a git repository. Project-level installation requires a git repo.${NC}"
        exit 1
    fi
    
    TARGET_DIR=".claude/skills/controller-harness"
    
    # Check if already installed
    if [[ -d "$TARGET_DIR" ]]; then
        echo -e "${YELLOW}Plugin already installed at $TARGET_DIR${NC}"
        if [[ -t 0 ]]; then  # Only ask if stdin is a terminal
            read -p "Replace existing installation? [y/N] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Installation cancelled."
                exit 0
            fi
        else
            echo "Replacing existing installation..."
        fi
        rm -rf "$TARGET_DIR"
    fi
    
    mkdir -p ".claude/skills"
    copy_plugin "$PLUGIN_DIR" "$TARGET_DIR"
    
    echo -e "${GREEN}Installed to $TARGET_DIR${NC}"
    echo ""
    echo "Controller Harness is now available for this project."
}

uninstall() {
    echo -e "${BLUE}Uninstalling Controller Harness...${NC}"
    
    # Determine home directory
    local home_dir="$HOME"
    
    GLOBAL_TARGET="$home_dir/.claude/skills/controller-harness"
    LOCAL_TARGET=".claude/skills/controller-harness"
    
    removed=0
    
    if [[ -d "$GLOBAL_TARGET" ]]; then
        rm -rf "$GLOBAL_TARGET"
        echo -e "${GREEN}Removed global installation${NC}"
        removed=1
    fi
    
    if [[ -d "$LOCAL_TARGET" ]]; then
        rm -rf "$LOCAL_TARGET"
        echo -e "${GREEN}Removed local installation${NC}"
        removed=1
    fi
    
    if [[ $removed -eq 0 ]]; then
        echo -e "${YELLOW}Plugin not found. Nothing to uninstall.${NC}"
    fi
}

# Main
case "${1:-}" in
    --global)
        install_global
        ;;
    --local)
        install_local
        ;;
    --uninstall)
        uninstall
        ;;
    --help)
        usage
        exit 0
        ;;
    "")
        install_global
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        usage
        exit 1
        ;;
esac
