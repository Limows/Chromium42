#!/bin/bash
# =============================================================================
# setup_env.sh — One-shot environment setup for building Chromium 42 on Android 4.0 ICS
#
# Run on Ubuntu 18.04 x86_64:
#   bash setup_env.sh
#
# This script installs:
#   - System packages (git, ninja-build, openjdk-8, etc.)
#   - Python 3.11 via pyenv (modern depot_tools needs 3.9+)
#   - Python 2.7 (Chromium 42 GYP scripts need it)
#   - depot_tools (modern main, supports Python 3)
#   - .gclient config with custom_deps for Chromium 42
# =============================================================================
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[+]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
err()   { echo -e "${RED}[!]${NC} $*"; }

# Resolve script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

BUILD_DIR="${BUILD_DIR:-$HOME/build_env}"
CHROMIUM_ROOT="${CHROMIUM_ROOT:-$HOME/chromium42}"

echo "==================================================================="
echo " Chromium 42 build environment setup"
echo " BUILD_DIR     = $BUILD_DIR"
echo " CHROMIUM_ROOT = $CHROMIUM_ROOT"
echo "==================================================================="

mkdir -p "$BUILD_DIR" "$CHROMIUM_ROOT"

# --- Step 1: System packages --------------------------------------------------
info "Step 1/5: Installing system packages (needs sudo)"
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    git curl wget unzip bzip2 tar \
    python3 python3-pip \
    python2.7 \
    openjdk-8-jdk ant \
    ninja-build \
    pkg-config \
    libgl1-mesa-glx libgl1-mesa-dev \
    libnss3-dev libnspr4-dev \
    libglib2.0-dev libcairo2-dev libpango1.0-dev \
    libgtk2.0-dev libgnome-keyring-dev \
    libasound2-dev libpulse-dev \
    libxss1 libxss-dev \
    libxext6 libxext-dev \
    libx11-xcb1 libx11-xcb-dev \
    libxtst6 libxtst-dev \
    libdrm2 libdrm-dev \
    bison flex gperf \
    libncurses5 \
    ca-certificates \
    software-properties-common \
    ;

# --- Step 1a: Upgrade git to 2.29+ ------------------------------------------
info "Step 1a/5: Checking git version (need 2.29+ for object-format=sha1)"
GIT_VERSION="$(git --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
GIT_MAJOR_MINOR="$(echo "$GIT_VERSION" | awk -F. '{print $1"."$2}')"
NEEDED="2.29"
if [ -z "$GIT_VERSION" ] || \
   awk -v cur="$GIT_MAJOR_MINOR" -v need="$NEEDED" \
       'BEGIN{split(cur,a,"."); split(need,b,"."); exit !(a[1]>b[1] || (a[1]==b[1] && a[2]>=b[2]))}'; then
    info "Already have git $GIT_VERSION (>= $NEEDED required)"
else
    warn "Current git is $GIT_VERSION, need >= $NEEDED. Upgrading..."
    sudo add-apt-repository -y ppa:git-core/ppa
    sudo apt-get update
    sudo apt-get install -y --only-upgrade git
    info "New git version: $(git --version)"
fi

# --- Step 1b: Install Python 3.11 via pyenv ---------------------------------
info "Step 1b/5: Installing Python 3.11 via pyenv (compiles from source, ~10-15 min)"

sudo apt-get install -y --no-install-recommends \
    make build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
    libncursesw5-dev xz-utils tk-dev \
    libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev

export PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
if [ ! -d "$PYENV_ROOT" ]; then
    info "Cloning pyenv..."
    git clone --depth=1 https://github.com/pyenv/pyenv.git "$PYENV_ROOT"
else
    info "pyenv already installed, updating..."
    cd "$PYENV_ROOT" && git pull --ff-only origin master
fi

export PATH="$PYENV_ROOT/bin:$PATH"
if command -v pyenv >/dev/null 2>&1; then
    eval "$(pyenv init -)"
fi

PY_VERSION="3.11.9"
if ! pyenv versions --bare | grep -q "^${PY_VERSION}$"; then
    info "Compiling Python $PY_VERSION (this takes ~10-15 minutes)..."
    pyenv install "$PY_VERSION"
else
    info "Python $PY_VERSION already installed"
fi
pyenv global "$PY_VERSION"

# Add pyenv init to .bashrc
if ! grep -q "pyenv init" "$HOME/.bashrc" 2>/dev/null; then
    echo "" >> "$HOME/.bashrc"
    echo "# pyenv setup (added by chromium42 setup)" >> "$HOME/.bashrc"
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> "$HOME/.bashrc"
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> "$HOME/.bashrc"
    echo 'eval "$(pyenv init -)"' >> "$HOME/.bashrc"
fi

info "python3: $(python3 --version 2>&1) at $(command -v python3)"
info "python2.7: $(python2.7 --version 2>&1) at $(command -v python2.7)"

# --- Step 2: depot_tools ----------------------------------------------------
info "Step 2/5: Cloning depot_tools"
if [ ! -d "$BUILD_DIR/depot_tools" ]; then
    git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git "$BUILD_DIR/depot_tools"
else
    info "depot_tools already exists, updating..."
    cd "$BUILD_DIR/depot_tools"
    git fetch origin
    git checkout main
    git pull --ff-only origin main
fi

# --- Step 3: Copy env file to BUILD_DIR ------------------------------------
info "Step 3/5: Copying chromium42_env.sh"
cp -f "$SCRIPT_DIR/chromium42_env.sh" "$BUILD_DIR/chromium42_env.sh"
chmod +x "$BUILD_DIR/chromium42_env.sh"

# --- Step 4: .gclient config ------------------------------------------------
info "Step 4/5: Writing .gclient config"
cat > "$CHROMIUM_ROOT/.gclient" <<'EOF'
solutions = [
  {
    "name": "src",
    "url": "https://chromium.googlesource.com/chromium/src.git",
    "deps_file": "DEPS",
    "managed": True,
    "custom_deps": {
      # === Override dead /trunk/ SVN paths with live git URLs ===
      "build":
        "https://chromium.googlesource.com/chromium/tools/build.git@HEAD",
      "build/scripts/command_wrapper/bin":
        "https://chromium.googlesource.com/chromium/tools/command_wrapper/bin.git@HEAD",
      "build/scripts/gsd_generate_index":
        "https://chromium.googlesource.com/chromium/tools/gsd_generate_index.git@HEAD",
      "build/scripts/tools/deps2git":
        "https://chromium.googlesource.com/chromium/tools/deps2git.git@HEAD",
      "src/third_party/opus/src":
        "https://github.com/bpsinc-native/src_third_party_opus_src.git@cae696156f1e60006e39821e79a1811ae1933c69",

      # === Skip NOT NEEDED deps ===
      # Test data
      "src/chrome/test/data/perf/canvas_bench": None,
      "src/chrome/test/data/perf/frame_rate/content": None,
      "src/chrome/tools/test/reference_build/chrome_linux": None,
      "src/chrome/tools/test/reference_build/chrome_mac": None,
      "src/chrome/tools/test/reference_build/chrome_win": None,
      "src/tools/page_cycler/acid3": None,
      "src/third_party/safe_browsing/testing": None,
      "src/third_party/appurify-python/src": None,

      # Windows-only
      "src/third_party/cygwin": None,
      "src/third_party/mingw-w64/mingw/bin": None,
      "src/third_party/swig/win": None,
      "src/third_party/pefile": None,
      "src/third_party/psyco_win32": None,
      "src/third_party/perl": None,
      "src/third_party/omaha/src/omaha": None,

      # Mac/iOS-only
      "src/third_party/gcdwebserver/src": None,
      "src/third_party/google_toolbox_for_mac/src": None,
      "src/third_party/swig/mac": None,
      "src/third_party/pdfsqueeze": None,
      "src/chrome/installer/mac/third_party/xz/xz": None,
      "src/testing/iossim/third_party/class-dump": None,

      # Linux desktop test server
      "src/third_party/lighttpd": None,

      # ChromeOS-only
      "src/third_party/chromite": None,
      "src/third_party/cros_system_api": None,

      # Test/dev tools
      "src/third_party/findbugs": None,
      "src/third_party/stp/src": None,
      "src/third_party/bidichecker": None,
      "src/third_party/undoview": None,

      # Old/superseded deps
      "src/third_party/freetype2/src": None,

      # NaCl-only build tools (dead)
      "src/third_party/gnu_binutils": None,
      "src/third_party/scons-2.0.1": None,
      "src/third_party/nacl_sdk_binaries": None,

      # Other dead
      "build/scripts/private/data/reliability": None,
      "build/third_party/lighttpd": None,
      "depot_tools": None,
      "build/third_party/xvfb": None,
    },
    "custom_vars": {
      "google_internal_path": ".",
      "google_internal": "",
      "webrtc_test_resources": False,
    },
  },
]
target_os = ["android"]
EOF
info "$CHROMIUM_ROOT/.gclient written"

# --- Step 5: Copy patches dir to BUILD_DIR ----------------------------------
info "Step 5/5: Copying patches to $BUILD_DIR/patches"
mkdir -p "$BUILD_DIR/patches"
cp -rf "$PROJECT_ROOT/patches/." "$BUILD_DIR/patches/"
chmod +x "$BUILD_DIR/patches/"*.py "$BUILD_DIR/patches/"*.sh 2>/dev/null || true

# --- Done -------------------------------------------------------------------
echo ""
echo "==================================================================="
echo " ${GREEN}Setup complete!${NC}"
echo "==================================================================="
echo ""
echo " Next steps:"
echo "   1. Source env file (every new shell):"
echo "        source $BUILD_DIR/chromium42_env.sh"
echo ""
echo "   2. Fetch Chromium 42 source (~12 GB, 30-60 min):"
echo "        bash $SCRIPT_DIR/fetch_source.sh"
echo ""
echo "   3. Apply patches (after fetch completes):"
echo "        python3 $BUILD_DIR/patches/apply_patches.py"
echo ""
echo "   4. Build APK:"
echo "        bash $SCRIPT_DIR/build.sh"
echo ""
echo " Result: $CHROMIUM_ROOT/src/out/Release/apks/ChromeShell.apk"
echo ""
echo " See BUILD.md for detailed instructions."
echo "==================================================================="
