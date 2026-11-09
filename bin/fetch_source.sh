#!/bin/bash
# =============================================================================
# fetch_source.sh — Fetch Chromium 42 source code via gclient sync
#
# Prerequisites:
#   - Run setup_env.sh first (it installs depot_tools, pyenv, .gclient)
#   - ~50 GB free disk space
# =============================================================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[+]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
err()   { echo -e "${RED}[!]${NC} $*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${BUILD_DIR:-$HOME/build_env}"
CHROMIUM_ROOT="${CHROMIUM_ROOT:-$HOME/chromium42}"

# Source the env (sets PATH for depot_tools, pyenv, etc.)
if [ ! -f "$BUILD_DIR/chromium42_env.sh" ]; then
    err "Build env not set up. Run: bash $SCRIPT_DIR/setup_env.sh"
fi
source "$BUILD_DIR/chromium42_env.sh" > /dev/null 2>&1 || true

# Verify gclient is available
if ! command -v gclient >/dev/null 2>&1; then
    err "gclient not found in PATH. Check $BUILD_DIR/depot_tools"
fi

# Verify .gclient exists
if [ ! -f "$CHROMIUM_ROOT/.gclient" ]; then
    err "$CHROMIUM_ROOT/.gclient not found. Run setup_env.sh first."
fi

info "Fetching Chromium 42.0.2311.107 source code..."
info "  Target dir: $CHROMIUM_ROOT/src"
info "  Approx size: ~12 GB (after sync)"
info ""
warn "gclient prints 'Still working on: src' every ~10s with NO progress bar."
warn "This is NORMAL, NOT a hang."
warn "To verify download progress in another terminal:"
warn "   watch -n 5 'du -sh $CHROMIUM_ROOT/src 2>/dev/null'"
info ""

cd "$CHROMIUM_ROOT"

# Run gclient sync
# --no-history        : shallow clone (saves ~5 GB)
# --nohooks           : skip post-checkout hooks (most are broken for M42)
# --revision          : pin to Chromium 42 release tag
# -j4                 : parallel git operations
gclient sync \
    --no-history \
    --revision 42.0.2311.107 \
    --nohooks \
    -j4 \
    --reset \
    --force \
    --verbose \
    || err "gclient sync failed"

info ""
info "Source fetch complete!"
info "  Size: $(du -sh $CHROMIUM_ROOT/src 2>/dev/null | awk '{print $1}')"
info ""
info "Next step: apply patches"
info "  source $BUILD_DIR/chromium42_env.sh"
info "  cd $CHROMIUM_ROOT/src"
info "  python3 $BUILD_DIR/patches/apply_patches.py"
