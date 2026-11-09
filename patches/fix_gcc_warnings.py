#!/usr/bin/env python3
# =============================================================================
# fix_gcc_warnings.py v3 — patch build/common.gypi to disable GCC 7/8 warnings
#                         ONLY for host compilation (not target NDK gcc 4.9).
#
# v2 added flags to target_defaults.cflags which applied to BOTH host (g++ 7)
# and target (arm-linux-androideabi-gcc 4.9). But NDK gcc 4.9 doesn't know
# these flags → "no option -Wimplicit-fallthrough" errors.
#
# v3 uses 'target_conditions' with ['_toolset=="host"', { ... }] to apply
# the flags ONLY to host compilation (g++ on the build machine).
# =============================================================================
import os
import re
import shutil
import sys
from datetime import datetime

GYP_PATH = "build/common.gypi"
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

    if "fix_gcc_warnings.py v3" in content:
        print("Already patched with v3")
        return 0

    # Remove v2 patch if present (revert to clean state)
    if "fix_gcc_warnings.py v2" in content:
        print("Removing v2 patch first...")
        # Remove the v2 block
        content = re.sub(
            r"\n\s*# === Added by fix_gcc_warnings\.py v2 for GCC 7/8 ===.*?# === End fix_gcc_warnings\.py v2 ===",
            "",
            content,
            flags=re.DOTALL,
        )
        print("  v2 patch removed")

    # Find the cflags section under os_posix condition
    # We'll add a target_conditions block with _toolset=="host" right after
    # the cflags_cc block (which is inside the same target_defaults).
    #
    # The structure is:
    #   ['os_posix==1 and OS!="mac" and OS!="ios"', {
    #     'target_defaults': {
    #       'cflags': [ ... ],
    #       'cflags_cc': [ ... ],   ← we add target_conditions AFTER this
    #       'ldflags': [ ... ],
    #       ...

    # Find 'cflags_cc': [ ... ] block end in the os_posix section
    # Marker: the line with '-Wsign-compare,' followed by '],' (end of cflags_cc)
    # Then 'ldflags': [ on the next meaningful line
    
    # Pattern: '-Wsign-compare,\n        ],\n        (optional) target_conditions'
    # We insert target_conditions after the '],' that closes cflags_cc.
    
    # Actually, simpler: find '-Wsign-compare,' (in cflags_cc) and insert
    # after the closing '],'
    
    # Find the cflags_cc block that contains -Wsign-compare
    pattern = re.compile(
        r"(\s*'-Wsign-compare',\s*\n\s*\],\s*\n)"  # the line + closing ],
        r"(?=\s*'ldflags':\s*\[)",  # lookahead: ldflags follows
        re.MULTILINE,
    )
    
    match = pattern.search(content)
    if not match:
        print("ERROR: Could not find cflags_cc block (looking for -Wsign-compare + ldflags)")
        # Try alternative: maybe ldflags is not immediately after
        # Just find -Wsign-compare and the next '],'
        alt_pattern = re.compile(r"(\s*'-Wsign-compare',\s*\n\s*\],\s*\n)")
        match = alt_pattern.search(content)
        if not match:
            print("ERROR: Could not find -Wsign-compare marker at all")
            return 1
    
    insert_pos = match.end()
    
    # Get indentation from the match
    indent_match = re.match(r"(\s*)", match.group(1))
    indent = indent_match.group(1) if indent_match else "        "
    
    # Build the target_conditions block
    # NOTE: Only include flags that exist in GCC 7 (Ubuntu 18.04 default).
    # GCC 8+ flags (-Wclass-memaccess, -Wstringop-truncation) cause
    # "no option -Wclass-memaccess" errors on GCC 7.
    flags = [
        # GCC 7+ warnings
        '-Wno-error=implicit-fallthrough',
        '-Wno-error=unused-but-set-variable',
        '-Wno-error=maybe-uninitialized',
        '-Wno-error=format-truncation',
        '-Wno-error=sizeof-pointer-memaccess',
        '-Wno-error=restrict',
        '-Wno-error=stringop-overflow',
        '-Wno-error=unused-function',
        '-Wno-error=unused-variable',
        '-Wno-error=strict-aliasing',
        '-Wno-error=parentheses',
        '-Wno-error=missing-field-initializers',
        '-Wno-error=deprecated-declarations',
        '-Wno-error=write-strings',
        '-Wno-error=sign-compare',
        '-Wno-error=type-limits',
        '-Wno-error=return-type',
        '-Wno-error=uninitialized',
        '-Wno-error=bool-compare',
        '-Wno-error=int-in-bool-context',
        '-Wno-error=switch',
        '-Wno-error=enum-compare',
        '-Wno-error=literal-suffix',
        '-Wno-error=narrowing',
        '-Wno-error=attributes',
        '-Wno-error=ignored-attributes',
        # NOTE: -Wclass-memaccess and -Wstringop-truncation are GCC 8+ only.
        # They cause "no option" errors on GCC 7. Do NOT include them.
    ]
    
    flags_lines = '\n'.join(f"{indent}  '{f}'," for f in flags)
    
    target_conditions_block = f"""{indent}'target_conditions': [
{indent}  ['_toolset=="host"', {{
{indent}    'cflags': [
{indent}      # === Added by fix_gcc_warnings.py v3 for GCC 7/8 (host only) ===
{flags_lines}
{indent}      # === End fix_gcc_warnings.py v3 ===
{indent}    ],
{indent}  }}],
{indent}],
"""
    
    new_content = content[:insert_pos] + target_conditions_block + content[insert_pos:]
    
    with open(GYP_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)

    print()
    print("Patched build/common.gypi (v3 — host-only):")
    print("  Added target_conditions with _toolset==\"host\" condition")
    print("  GCC 7/8 warning suppressions apply ONLY to host g++ compilation")
    print("  Target (NDK gcc 4.9) is NOT affected")
    print(f"  Added {len(flags)} -Wno-error=... flags")
    print()
    print("Re-run gyp_chromium:")
    print("  gyp_chromium")
    print()
    print("Then re-run ninja:")
    print("  /usr/bin/ninja -C out/Release chrome_shell_apk")
    return 0


if __name__ == "__main__":
    print(f"=== GCC warnings patcher v3 ({datetime.now().isoformat()}) ===")
    print()
    sys.exit(main())
