#!/bin/bash
# =============================================================================
# build.sh — Build Chromium 42 chrome_shell_apk for Android 4.0 ICS
#
# Prerequisites:
#   - setup_env.sh completed
#   - fetch_source.sh completed
#   - apply_patches.py completed
#
# This script:
#   1. Sources chromium42_env.sh (sets PATH, GYP_DEFINES, etc.)
#   2. Runs gyp_chromium (regenerates ninja files)
#   3. Runs ninja_run -C out/Release chrome_shell_apk
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

# Verify prerequisites
if [ ! -f "$BUILD_DIR/chromium42_env.sh" ]; then
    err "Build env not set up. Run: bash $SCRIPT_DIR/setup_env.sh"
fi

if [ ! -d "$CHROMIUM_ROOT/src/chrome" ]; then
    err "Chromium source not found at $CHROMIUM_ROOT/src/"
    err "Run: bash $SCRIPT_DIR/fetch_source.sh"
fi

if [ ! -f "$CHROMIUM_ROOT/src/chrome/browser/chrome_shell_stubs.cc" ]; then
    err "Stubs file not found. Run apply_patches.py first:"
    err "  cd $CHROMIUM_ROOT/src && python3 $BUILD_DIR/patches/apply_patches.py"
fi

# Source env (sets PATH, GYP_DEFINES, defines gyp_chromium + ninja_run)
info "Sourcing env..."
source "$BUILD_DIR/chromium42_env.sh" > /dev/null 2>&1 || true

# Verify functions loaded
if ! type gyp_chromium >/dev/null 2>&1; then
    err "gyp_chromium function not loaded. Check $BUILD_DIR/chromium42_env.sh"
fi
if ! type ninja_run >/dev/null 2>&1; then
    err "ninja_run function not loaded. Check $BUILD_DIR/chromium42_env.sh"
fi

# Show GYP_DEFINES summary
info "GYP_DEFINES:"
echo "$GYP_DEFINES" | tr ' ' '\n' | grep -E "^(OS|target_arch|arm_version|enable_extensions|enable_plugins|safe_browsing|clang|host_clang|proprietary_codecs|enable_widevine)" | sed 's/^/    /'

cd "$CHROMIUM_ROOT/src"

# === Step 1: Run GYP ===
info "Step 1/2: gyp_chromium (regenerate ninja files)"
echo ""
gyp_chromium
GYP_RC=$?
echo ""

if [ $GYP_RC -ne 0 ]; then
    err "gyp_chromium failed (exit $GYP_RC)"
fi
info "GYP complete"

# === Step 2: Run ninja ===
info "Step 2/2: ninja_run (compile chrome_shell_apk)"
echo ""
echo "  This will take 1-4 hours depending on your CPU."
echo "  Watch: $CHROMIUM_ROOT/src/out/Release/obj/"
echo ""
ninja_run -C out/Release chrome_shell_apk
NINJA_RC=$?
echo ""

if [ $NINJA_RC -ne 0 ]; then
    err "ninja failed (exit $NINJA_RC)"
fi

# === Result ===
APK=""
for candidate in \
    "$CHROMIUM_ROOT/src/out/Release/apks/ChromeShell.apk" \
    "$CHROMIUM_ROOT/src/out/Release/ChromeShell.apk" \
    "$CHROMIUM_ROOT/src/out/Release/apks/chrome_shell_apk.apk"; do
    if [ -f "$candidate" ]; then
        APK="$candidate"
        break
    fi
done

echo ""
echo "==================================================================="
echo -e " ${GREEN}BUILD COMPLETE!${NC}"
echo "==================================================================="
if [ -n "$APK" ]; then
    info "APK location:"
    echo "    $APK"
    info "APK size: $(du -h "$APK" | awk '{print $1}')"
    echo ""
    info "Install on Android device:"
    echo "    adb install -r $APK"
else
    warn "APK not found in expected locations. Check:"
    find "$CHROMIUM_ROOT/src/out/Release" -name "*.apk" 2>/dev/null | head -5
fi
echo ""
info "Result .so:"
ls -lh "$CHROMIUM_ROOT/src/out/Release/lib/libchromeshell.so" 2>/dev/null || true
echo "==================================================================="
