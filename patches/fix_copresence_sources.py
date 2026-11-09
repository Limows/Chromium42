#!/usr/bin/env python3
# =============================================================================
# fix_copresence_sources.py — exclude copresence-related source files from
#                               chrome_browser_extensions.gypi on Android.
#
# We already removed copresence IDL files (fix_copresence_api.py) and
# copresence_proto dependency (fix_gyp_components.py). But the source files
# that reference generated copresence headers are still being compiled.
#
# This script comments out ALL copresence source entries in
# chrome_browser_extensions.gypi.
# =============================================================================
import os
import re
import shutil
import sys
from datetime import datetime

GYP_PATH = "chrome/chrome_browser_extensions.gypi"
BACKUP_PATH = GYP_PATH + ".original"

# All copresence AND audio_modem related source file patterns to comment out
COPRESENCE_PATTERNS = [
    # copresence sources
    "browser/copresence/chrome_whispernet_config.h",
    "browser/copresence/chrome_whispernet_client.cc",
    "browser/copresence/chrome_whispernet_client.h",
    "browser/extensions/api/copresence/copresence_api.cc",
    "browser/extensions/api/copresence/copresence_api.h",
    "browser/extensions/api/copresence/copresence_translations.cc",
    "browser/extensions/api/copresence/copresence_translations.h",
    "browser/extensions/api/copresence_private/copresence_private_api.cc",
    "browser/extensions/api/copresence_private/copresence_private_api.h",
    # audio_modem sources (IDL removed from schemas.gypi, so generated
    # header audio_modem.h doesn't exist)
    "browser/extensions/api/audio_modem/audio_modem_api.cc",
    "browser/extensions/api/audio_modem/audio_modem_api.h",
]


def main():
    if not os.path.exists(GYP_PATH):
        print(f"ERROR: {GYP_PATH} not found")
        print("Run this script from ~/chromium42/src/")
        return 1

    if not os.path.exists(BACKUP_PATH):
        shutil.copy2(GYP_PATH, BACKUP_PATH)
        print(f"Backed up {GYP_PATH} → {BACKUP_PATH}")

    with open(GYP_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    changes = 0
    for pattern in COPRESENCE_PATTERNS:
        # Match: 'browser/copresence/...',
        # with any indentation
        regex = re.compile(
            r"^(\s*)'" + re.escape(pattern) + r"',\s*$",
            re.MULTILINE,
        )
        if regex.search(content):
            # Check if already commented out
            commented_regex = re.compile(
                r"^(\s*)#.*" + re.escape(pattern), re.MULTILINE
            )
            if commented_regex.search(content):
                print(f"  Already commented: {pattern}")
                continue

            new_content = regex.sub(
                lambda m: f"{m.group(1)}# PATCHED OUT by fix_copresence_sources.py: {pattern}",
                content,
            )
            content = new_content
            changes += 1
            print(f"  Commented out: {pattern}")
        else:
            print(f"  Not found: {pattern}")

    if changes > 0:
        with open(GYP_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\nApplied {changes} patches to {GYP_PATH}")
    else:
        print("\nAll patches already applied — nothing to do.")

    print()
    print("Re-run gyp_chromium:")
    print("  gyp_chromium")
    print()
    print("Then re-run ninja:")
    print("  /usr/bin/ninja -C out/Release chrome_shell_apk")
    return 0


if __name__ == "__main__":
    print(f"=== Copresence sources patcher ({datetime.now().isoformat()}) ===")
    print()
    sys.exit(main())
