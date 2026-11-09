#!/usr/bin/env python3
# =============================================================================
# fix_copresence_api_sources.py v3 — Remove copresence from ALL api_sources.gypi
#
# Problem: generated_api_registration.cc still #includes copresence_api.h
# because the .h is listed in api_sources.gypi (the file that lists which
# API source files to compile and register).
#
# Solution: Find ALL api_sources.gypi and similar .gypi files that reference
# copresence, and comment out those lines.
#
# Files to scan:
#   chrome/common/extensions/api/api_sources.gypi
#   chrome/browser/extensions/api/sources.gypi
#   chrome/browser/extensions/api/api_sources.gypi
#   chrome/common/extensions/api/sources.gypi
#   Any .gypi referencing copresence in chrome/common/extensions/api or
#   chrome/browser/extensions/api
# =============================================================================
import os
import re
import shutil
import sys
from datetime import datetime

# Patterns to remove — anything copresence/audio_modem related
EXCLUDE_PATTERNS = [
    r"copresence_api\.h",
    r"copresence_api\.cc",
    r"copresence_private_api\.h",
    r"copresence_private_api\.cc",
    r"copresence_translations\.h",
    r"copresence_translations\.cc",
    r"copresence\.idl",
    r"copresence_private\.idl",
    r"audio_modem\.idl",
    r"audio_modem_api\.h",
    r"audio_modem_api\.cc",
    r"copresence/copresence",
    r"copresence_private/copresence_private",
    r"audio_modem/audio_modem",
    # Match path patterns like 'browser/extensions/api/copresence/...'
    r"api/copresence/",
    r"api/copresence_private/",
    r"api/audio_modem/",
]

# Directories to scan — scan ALL of chrome/ for .gypi references
SCAN_DIRS = [
    "chrome",
    "components",
    "content",
    "extensions",
]


def find_gypi_files():
    found = set()
    for d in SCAN_DIRS:
        if not os.path.exists(d):
            continue
        for root, dirs, files in os.walk(d):
            for fn in files:
                if fn.endswith((".gypi", ".gyp")):
                    found.add(os.path.join(root, fn))
    return sorted(found)


def patch_file(path):
    if not os.path.exists(path):
        return 0

    backup = path + ".original"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    patched = 0
    new_lines = []
    for line in lines:
        stripped = line.strip()

        # Skip already-commented lines (Python # style for .gypi)
        if stripped.startswith("#"):
            new_lines.append(line)
            continue
        # Skip JSON-style comments (// for .json files)
        if stripped.startswith("//"):
            new_lines.append(line)
            continue

        # Check if this line references any excluded pattern
        matched = False
        for pat in EXCLUDE_PATTERNS:
            if re.search(pat, stripped):
                indent = re.match(r'^(\s*)', line).group(1)
                # Use # comment for .gypi/.gyp files
                if path.endswith((".gypi", ".gyp")):
                    new_lines.append(f"{indent}# ANDROID-EXCLUDED: {stripped}\n")
                else:
                    # For .json files, just leave it alone (we'll regenerate)
                    new_lines.append(line)
                    continue
                patched += 1
                matched = True
                break
        if not matched:
            new_lines.append(line)

    if patched > 0:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    return patched


def clean_generated():
    """Delete generated API registration files."""
    paths = [
        "out/Release/gen/chrome/browser/extensions/api/generated_api_registration.cc",
        "out/Release/gen/chrome/browser/extensions/api/generated_api_schemas.cc",
    ]
    deleted = []
    for p in paths:
        if os.path.exists(p):
            os.remove(p)
            deleted.append(p)
    # Also clean entire dir if exists
    d = "out/Release/gen/chrome/browser/extensions/api"
    if os.path.exists(d):
        shutil.rmtree(d)
        deleted.append(d + " (whole dir)")
    return deleted


def main():
    print(f"=== fix_copresence_api_sources.py v3 ({datetime.now().isoformat()}) ===")
    print()
    print("Scanning ALL .gypi/.gyp/.json files in chrome/ for copresence references")
    print()

    if not os.path.exists("chrome/browser"):
        print("ERROR: run from ~/chromium42/src/")
        return 1

    files = find_gypi_files()
    print(f"Found {len(files)} .gypi/.gyp/.json files to scan")

    total = 0
    touched = 0
    for path in files:
        n = patch_file(path)
        if n > 0:
            print(f"  {path}: removed {n} reference(s)")
            total += n
            touched += 1

    print()
    print(f"Total: {total} copresence references removed from {touched} files")

    print()
    print("[Clean] Deleting generated API files to force regeneration...")
    deleted = clean_generated()
    for p in deleted:
        print(f"  Deleted: {p}")

    print()
    print("Next steps:")
    print("  gyp_chromium")
    print("  /usr/bin/ninja -C out/Release chrome_shell_apk")
    return 0


if __name__ == "__main__":
    sys.exit(main())
