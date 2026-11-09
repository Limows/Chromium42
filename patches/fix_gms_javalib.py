#!/usr/bin/env python3
# =============================================================================
# fix_gms_javalib.py — patch android_tools.gyp to NOT generate R.java from
#                       res/ for the google_play_services_default_javalib target.
#
# Problem: Chromium 42's android_tools.gyp defines the target
# google_play_services_default_javalib with 'has_java_resources': 1,
# which makes GYP generate R.java from res/values/strings.xml.
# But the target also has java_in_dir pointing to a directory with
# src/com/google/android/gms/R.java (the stub we created).
# Both R.java files get compiled together by javac → "duplicate class" error.
#
# Solution: set has_java_resources=0 to skip R.java generation from res/.
# Our stub R.java in src/ will be the only R.java compiled.
# =============================================================================
import os
import re
import shutil
import sys
from datetime import datetime

GYP_PATH = "third_party/android_tools/android_tools.gyp"
BACKUP_PATH = GYP_PATH + ".original"


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

    if "google_play_services_default_javalib_no_res" not in content:
        print("ERROR: google_play_services_default_javalib_no_res target not found")
        return 1

    # Find the google_play_services_default_javalib target block (NOT _no_res)
    # Pattern: target_name': 'google_play_services_default_javalib',\n
    # ... 'has_java_resources': 1, ...
    # 
    # We need to replace 'has_java_resources': 1 → 0 ONLY in this target,
    # not in google_play_services_default_javalib_no_res or others.
    
    # Find the target block by locating the exact line that has
    # 'has_java_resources': 1 inside the google_play_services_default_javalib
    # target (which is the one WITHOUT _no_res suffix).
    
    # Find positions of all target_name occurrences
    target_pattern = re.compile(r"'target_name':\s*'([^']+)'", re.MULTILINE)
    targets = list(target_pattern.finditer(content))
    
    # Find the google_play_services_default_javalib target (without _no_res)
    target_start = None
    target_end = None
    for i, m in enumerate(targets):
        if m.group(1) == "google_play_services_default_javalib":
            target_start = m.start()
            target_end = targets[i + 1].start() if i + 1 < len(targets) else len(content)
            break
    
    if target_start is None:
        print("ERROR: google_play_services_default_javalib target not found")
        return 1
    
    target_block = content[target_start:target_end]
    
    if "has_java_resources" not in target_block:
        print("ERROR: has_java_resources not found in target block")
        return 1
    
    # Replace 'has_java_resources': 1 with 'has_java_resources': 0 ONLY in this target
    # IMPORTANT: keep the trailing comma! Without it, Python 2 sees the next
    # line as continuation of the same expression → SyntaxError.
    new_target_block = target_block.replace(
        "'has_java_resources': 1,",
        "'has_java_resources': 0,  # PATCHED by fix_gms_javalib.py"
    )
    
    if new_target_block == target_block:
        print("WARN: No change made — pattern 'has_java_resources': 1 not found")
        return 1
    
    new_content = content[:target_start] + new_target_block + content[target_end:]
    
    with open(GYP_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print("Patched android_tools.gyp:")
    print("  google_play_services_default_javalib: 'has_java_resources': 1 → 0")
    print("  (prevents GYP from generating conflicting R.java from res/)")
    print()
    print("Re-run gyp_chromium:")
    print("  gyp_chromium")
    print()
    print("Then clean gen/ cache and re-run ninja:")
    print("  rm -rf out/Release/gen/google_play_services_default_javalib")
    print("  /usr/bin/ninja -C out/Release chrome_shell_apk")
    return 0


if __name__ == "__main__":
    print(f"=== GMS javalib patcher ({datetime.now().isoformat()}) ===")
    print()
    sys.exit(main())
