#!/usr/bin/env python3
# =============================================================================
# fix_dead_target_refs.py — Remove references to removed GYP targets
#
# Problem: Earlier we removed target definitions for:
#   - audio_modem_test_support (from components/components.gyp)
#   - copresence
#   - copresence_proto
#   - cryptauth
#   - proximity_auth (and others)
#
# But other .gypi files (especially test targets like unit_tests) still
# reference them as dependencies. GYP fails: "Dependency ... not found".
#
# Solution: Scan ALL .gypi/.gyp files for dependency references to these
# removed targets, and comment them out with #.
# =============================================================================
import os
import re
import shutil
import sys
from datetime import datetime

# Targets that we removed earlier — must not be referenced anywhere
# Include _test_support variants too (we removed those alongside)
_BASE_TARGETS = [
    "audio_modem",
    "copresence",
    "copresence_proto",
    "cryptauth",
    "proximity_auth",
    "storage_monitor",
    "wifi",
    "user_manager",
    "feedback",
    "browser_watcher",
    # Components-level test_support/build targets that are also dead
    "feedback_component",
    "feedback_test_support",
    "storage_monitor_test_support",
    "user_manager_test_support",
]

REMOVED_TARGETS = set()
for t in _BASE_TARGETS:
    REMOVED_TARGETS.add(t)
    if not t.endswith("_test_support"):
        REMOVED_TARGETS.add(t + "_test_support")
REMOVED_TARGETS = sorted(REMOVED_TARGETS)


def find_gypi_files():
    files = []
    for root_dir in ["chrome", "extensions", "device", "components",
                     "content", "ui", "net", "base", "skia",
                     "third_party"]:
        if not os.path.exists(root_dir):
            continue
        for root, dirs, fnames in os.walk(root_dir):
            # DO NOT skip test dirs — test_support references live there
            for fn in fnames:
                if fn.endswith((".gypi", ".gyp")):
                    files.append(os.path.join(root, fn))
    return files


def patch_gypi(gypi_path):
    """Comment out dependency lines referencing removed targets."""
    if not os.path.exists(gypi_path):
        return 0

    with open(gypi_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    removed = 0
    new_lines = []
    for line in lines:
        stripped = line.strip()

        # Skip already-commented lines
        if stripped.startswith("#"):
            new_lines.append(line)
            continue

        # Check if this line references any removed target
        # Use very permissive match: just looking for the target name
        # in a dependency-like context
        matched = False
        for target in REMOVED_TARGETS:
            # Multiple patterns to be aggressive:
            # 1. .gyp:target_name (any quote/comma after)
            # 2. just 'target_name' alone as a dependency
            # 3. <(DEPTH)/...:target_name
            patterns = [
                r"\.gyp:" + re.escape(target) + r"(#target)?\b",
                r"['\"]" + re.escape(target) + r"['\"]",
                r":" + re.escape(target) + r"(#target)?['\"\s,]",
            ]
            for pat in patterns:
                if re.search(pat, stripped):
                    indent = re.match(r'^(\s*)', line).group(1)
                    new_lines.append(f"{indent}# DEAD-REF-REMOVED: {stripped}\n")
                    removed += 1
                    matched = True
                    break
            if matched:
                break
        if not matched:
            new_lines.append(line)

    if removed > 0:
        with open(gypi_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    return removed


def main():
    print(f"=== fix_dead_target_refs.py ({datetime.now().isoformat()}) ===")
    print()
    print(f"Targets to remove references to: {len(REMOVED_TARGETS)}")
    for t in REMOVED_TARGETS:
        print(f"  - {t}")
    print()

    if not os.path.exists("chrome/browser"):
        print("ERROR: run from ~/chromium42/src/")
        return 1

    gypi_files = find_gypi_files()
    print(f"Scanning {len(gypi_files)} .gypi/.gyp files...")

    total = 0
    touched = 0
    for gyp in gypi_files:
        n = patch_gypi(gyp)
        if n > 0:
            print(f"  {gyp}: removed {n} dead reference(s)")
            total += n
            touched += 1

    print()
    print(f"Total: {total} dead references removed from {touched} files")
    if total > 0:
        print()
        print("Regenerate GYP and rebuild:")
        print("  gyp_chromium")
        print("  /usr/bin/ninja -C out/Release chrome_shell_apk")
    else:
        print("No dead references found. May be a different issue.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
