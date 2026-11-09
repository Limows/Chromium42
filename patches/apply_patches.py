#!/usr/bin/env python3
# =============================================================================
# apply_patches.py — Apply all patches needed for Chromium 42 Android build
#
# Run from: ~/chromium42/src
# Usage:    python3 apply_patches.py
#
# This script runs all patchers in the correct order:
#   1. GRIT .grd files (Android excludes)
#   2. GCC warnings (host-only)
#   3. STLport vector::data()
#   4. libusb Android
#   5. GMS javalib (has_java_resources=0)
#   6. Google Play Services stub
#   7. Hooks (LASTCHANGE, LASTCHANGE.blink)
#   8. Component-level excludes (audio_modem, copresence, etc.)
#   9. Dead target refs cleanup
#  10. Copresence sources exclusion
#  11. Copresence API schemas.gypi + chrome_browser_extensions.gypi exclusion
#  12. Manual C++ source patches (compiler_version.py, hid_service.cc, etc.)
#  13. Copy chrome_shell_stubs.cc into chrome/browser/
# =============================================================================
import os
import shutil
import subprocess
import sys
from datetime import datetime

# Where this script lives
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run(cmd, desc):
    """Run a command and stream output."""
    print(f"\n{'='*70}")
    print(f"  {desc}")
    print(f"{'='*70}")
    print(f"  $ {' '.join(cmd)}")
    print()
    rc = subprocess.call(cmd)
    if rc != 0:
        print(f"\n  FAILED (exit {rc})")
        return False
    print(f"\n  OK")
    return True


def main():
    print(f"\n{'#'*70}")
    print(f"# apply_patches.py")
    print(f"# Started: {datetime.now().isoformat()}")
    print(f"# Script dir: {SCRIPT_DIR}")
    print(f"{'#'*70}")

    # Verify we're in chromium42/src
    if not os.path.exists("chrome/browser") or not os.path.exists("build/common.gypi"):
        print("\nERROR: Run from ~/chromium42/src/")
        print("       Expected: chrome/browser/ and build/common.gypi present")
        return 1

    patches_dir = SCRIPT_DIR
    if not os.path.basename(SCRIPT_DIR) == "patches":
        # If invoked from elsewhere, patches are in patches/ next to script
        if os.path.basename(SCRIPT_DIR) == "bin":
            patches_dir = os.path.join(os.path.dirname(SCRIPT_DIR), "patches")
        elif os.path.isdir(os.path.join(SCRIPT_DIR, "patches")):
            patches_dir = os.path.join(SCRIPT_DIR, "patches")

    # Verify patches_dir contains expected patchers
    expected_files = [
        "fix_grd_android_excludes.py",
        "fix_manual_patches.py",
        "chrome_shell_stubs.cc",
    ]
    missing = [f for f in expected_files if not os.path.exists(os.path.join(patches_dir, f))]
    if missing:
        print(f"\nERROR: patches directory incomplete: {patches_dir}")
        for f in missing:
            print(f"  Missing: {f}")
        print(f"\nExpected location: $BUILD_DIR/patches/")
        return 1

    print(f"# Patches dir: {patches_dir}")

    # Patchers in correct order
    steps = [
        # === Step 1: GRIT .grd Android excludes ===
        (
            ["python3", os.path.join(patches_dir, "fix_grd_android_excludes.py")],
            "Step 1: Patch .grd files (Android excludes — not is_android → False)",
        ),
        # === Step 2: GCC warnings (host-only) ===
        (
            ["python3", os.path.join(patches_dir, "fix_gcc_warnings.py")],
            "Step 2: Patch GCC warnings (host g++ only, not NDK gcc 4.9)",
        ),
        # === Step 3: STLport vector::data() ===
        (
            ["python3", os.path.join(patches_dir, "fix_stlport_vector_data.py")],
            "Step 3: Patch STLport vector::data() for C++11",
        ),
        # === Step 4: libusb Android ===
        (
            ["python3", os.path.join(patches_dir, "fix_libusb_android.py")],
            "Step 4: Patch libusb for Android (POSIX threads, OS_LINUX)",
        ),
        # === Step 5: GMS javalib ===
        (
            ["python3", os.path.join(patches_dir, "fix_gms_javalib.py")],
            "Step 5: Patch android_tools.gyp (GMS has_java_resources=0)",
        ),
        # === Step 6: Google Play Services stub ===
        (
            ["bash", os.path.join(patches_dir, "stub_google_play_services.sh")],
            "Step 6: Create Google Play Services stub",
        ),
        # === Step 7: Hooks (LASTCHANGE, etc.) ===
        (
            ["bash", os.path.join(patches_dir, "run_hooks.sh")],
            "Step 7: Run hooks (LASTCHANGE, LASTCHANGE.blink)",
        ),
        # === Step 8: Component-level excludes (audio_modem, copresence, etc.) ===
        (
            ["python3", os.path.join(patches_dir, "fix_gyp_components.py")],
            "Step 8: Patch components.gyp (exclude dead Google APIs)",
        ),
        # === Step 9: Dead target refs ===
        (
            ["python3", os.path.join(patches_dir, "fix_dead_target_refs.py")],
            "Step 9: Remove dead target references (audio_modem_test_support, etc.)",
        ),
        # === Step 10: Copresence sources ===
        (
            ["python3", os.path.join(patches_dir, "fix_copresence_sources.py")],
            "Step 10: Exclude copresence source files",
        ),
        # === Step 11: Copresence API schemas.gypi + chrome_browser_extensions.gypi ===
        (
            ["python3", os.path.join(patches_dir, "fix_copresence_api_sources.py")],
            "Step 11: Exclude copresence from schemas.gypi and chrome_browser_extensions.gypi",
        ),
        # === Step 12: Manual C++ source patches ===
        (
            ["python3", os.path.join(patches_dir, "fix_manual_patches.py")],
            "Step 12: Apply manual C++ source patches (compiler_version, hid_service, etc.)",
        ),
    ]

    failed = []
    for cmd, desc in steps:
        if not run(cmd, desc):
            failed.append(desc)

    # === Step 13: Copy chrome_shell_stubs.cc into chrome/browser/ ===
    print(f"\n{'='*70}")
    print(f"  Step 13: Copy chrome_shell_stubs.cc → chrome/browser/")
    print(f"{'='*70}")
    src_stub = os.path.join(patches_dir, "chrome_shell_stubs.cc")
    dst_stub = "chrome/browser/chrome_shell_stubs.cc"
    if os.path.exists(src_stub):
        # Ensure chrome/browser/ exists
        os.makedirs("chrome/browser", exist_ok=True)
        shutil.copy2(src_stub, dst_stub)
        print(f"  Copied: {src_stub} → {dst_stub}")
        print(f"  Size: {os.path.getsize(dst_stub)} bytes")
        print("  OK")
    else:
        print(f"  ERROR: {src_stub} not found")
        failed.append("Step 13: copy stubs")

    # === Final report ===
    print(f"\n{'#'*70}")
    print(f"# Patches summary")
    print(f"#{'#'*68}")
    if failed:
        print(f"#  {len(failed)} step(s) FAILED:")
        for f in failed:
            print(f"#    - {f}")
        print(f"#")
        print(f"# Total: {len(steps) + 1 - len(failed)}/{len(steps) + 1} OK")
        return 1
    else:
        print(f"#  All {len(steps) + 1} steps completed successfully!")
        print(f"#")
        print(f"# Next steps:")
        print(f"#   source ~/build_env/chromium42_env.sh")
        print(f"#   gyp_chromium")
        print(f"#   ninja_run -C out/Release chrome_shell_apk")
        print(f"{'#'*70}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
