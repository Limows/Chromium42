#!/bin/bash
# =============================================================================
# run_hooks.sh — manually run the gclient hooks that we skipped via --nohooks.
#
# When running `gclient sync --nohooks`, several post-checkout hooks are NOT
# run. Some of these generate files that the build needs:
#   - LASTCHANGE       — git SHA of chromium/src (for version.h)
#   - LASTCHANGE.blink — git SHA of third_party/WebKit (for webkit_version.h)
#
# Run this after `gyp_chromium` and BEFORE `ninja`:
#   cd ~/chromium42/src
#   bash ~/build_env/run_hooks.sh
# =============================================================================
set -e

# Determine Chromium source root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_ROOT="${CHROMIUM_ROOT:-$HOME/chromium42}/src"

if [ ! -d "$SRC_ROOT" ]; then
    echo "ERROR: Chromium source root not found: $SRC_ROOT"
    echo "  Set CHROMIUM_ROOT env var or run from default location"
    exit 1
fi

if ! command -v python2.7 >/dev/null 2>&1; then
    echo "ERROR: python2.7 not installed"
    echo "  Install:  sudo apt install python2.7  (Ubuntu/Debian)"
    echo "           sudo pacman -S python2       (Arch/Manjaro, may need AUR)"
    exit 1
fi

cd "$SRC_ROOT"
echo "=== Running gclient hooks manually (cwd: $(pwd)) ==="
echo ""

# === Hook: lastchange (chromium/src SHA → build/util/LASTCHANGE) ===
echo "[1/2] Generating build/util/LASTCHANGE (chromium SHA)"
if [ ! -f "build/util/LASTCHANGE" ]; then
    python2.7 build/util/lastchange.py -o build/util/LASTCHANGE
    echo "  ✓ Created build/util/LASTCHANGE"
else
    echo "  ✓ Already exists"
fi

# === Hook: lastchange (Blink SHA → build/util/LASTCHANGE.blink) ===
echo ""
echo "[2/2] Generating build/util/LASTCHANGE.blink (Blink SHA)"
if [ ! -f "build/util/LASTCHANGE.blink" ]; then
    if [ -d "third_party/WebKit" ]; then
        python2.7 build/util/lastchange.py -s third_party/WebKit -o build/util/LASTCHANGE.blink
        echo "  ✓ Created build/util/LASTCHANGE.blink"
    else
        echo "  ⚠ third_party/WebKit not found — creating empty LASTCHANGE.blink"
        echo "Blink-Unknown-Revision" > build/util/LASTCHANGE.blink
    fi
else
    echo "  ✓ Already exists"
fi

echo ""
echo "=== Done. Files created: ==="
ls -la build/util/LASTCHANGE build/util/LASTCHANGE.blink 2>/dev/null
echo ""
echo "Now you can run ninja:"
echo "  /usr/bin/ninja -C out/Release chrome_shell_apk"
