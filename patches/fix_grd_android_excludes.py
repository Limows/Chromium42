#!/usr/bin/env python3
# =============================================================================
# fix_grd_android_excludes.py v5 — SMART patcher
#
# Problem with v3/v4: replaced 'not is_android' → 'True', which ACTIVATED
# desktop blocks. But some IDS_ exist in BOTH 'is_android' AND 'not is_android'
# blocks → DuplicateKey error from GRIT.
#
# v5 solution:
#   1. Restore .grd from backup (undo v3/v4 damage)
#   2. For each <if expr="not is_android..."> block:
#      - Collect IDS_ inside the block
#      - If ANY of those IDS_ also exists in an is_android block
#        (or unconditionally) → set to False (is_android version wins)
#      - If ALL IDS_ are unique (not in is_android/unconditional)
#        → set to True (activate for Android, e.g. IDS_CONTENT_CONTEXT_COPY)
#
# This way:
#   - Duplicates eliminated (is_android version kept)
#   - Desktop-only IDS_ (like IDS_CONTENT_CONTEXT_COPY) still generated
# =============================================================================
import os
import re
import shutil
import sys
from datetime import datetime

GRD_FILES = [
    "chrome/app/generated_resources.grd",
    "chrome/app/google_chrome_strings.grd",
    "chrome/app/chromium_strings.grd",
    "chrome/app/locale_settings.grd",
    "content/app/strings/content_strings.grd",
    "ui/base/strings/ui_strings.grd",
    "components/strings/components_strings.grd",
    "extensions/strings/app_strings.grd",
]


def find_if_blocks(content):
    """
    Find all top-level <if expr="...">...</if> blocks with proper nesting.
    Returns list of dicts: {start, tag_end, end, after_end, expr, inner}
    """
    blocks = []
    pos = 0
    while True:
        start = content.find('<if ', pos)
        if start == -1:
            break
        tag_end = content.find('>', start)
        if tag_end == -1:
            break
        tag = content[start:tag_end + 1]
        m = re.match(r'<if\s+expr="([^"]*)"\s*>', tag)
        if not m:
            pos = tag_end + 1
            continue
        expr = m.group(1)

        # Find matching </if> accounting for nesting
        depth = 1
        search = tag_end + 1
        end = -1
        while depth > 0:
            next_if = content.find('<if ', search)
            next_close = content.find('</if>', search)
            if next_close == -1:
                break
            if next_if != -1 and next_if < next_close:
                depth += 1
                # skip to end of opening tag
                inner_tag_end = content.find('>', next_if)
                if inner_tag_end == -1:
                    break
                search = inner_tag_end + 1
            else:
                depth -= 1
                if depth == 0:
                    end = next_close
                    break
                search = next_close + 5

        if end == -1:
            break

        blocks.append({
            'start': start,
            'tag_end': tag_end + 1,
            'end': end,
            'after_end': end + 5,
            'expr': expr,
            'inner': content[tag_end + 1:end],
        })
        pos = end + 5
    return blocks


def extract_ids(text):
    """Extract all IDS_/IDR_/IDS message names from text."""
    return set(re.findall(r'name="(IDS_[A-Z0-9_]+)"', text))


def collect_ids_outside_if(content, if_blocks):
    """
    Collect IDS_ defined OUTSIDE any <if> block (unconditional).
    """
    # Build sorted list of if-block ranges
    ranges = sorted([(b['start'], b['after_end']) for b in if_blocks])

    # Extract content outside if blocks
    pieces = []
    last = 0
    for s, e in ranges:
        pieces.append(content[last:s])
        last = e
    pieces.append(content[last:])

    outside = ''.join(pieces)
    return extract_ids(outside)


def patch_grd_file(grd_path):
    if not os.path.exists(grd_path):
        return None

    backup = grd_path + ".original"
    if os.path.exists(backup):
        shutil.copy2(backup, grd_path)

    with open(grd_path, "r", encoding="utf-8") as f:
        content = f.read()

    if_blocks = find_if_blocks(content)

    # Classify blocks
    is_android_ids = set()
    not_is_android_blocks = []

    for b in if_blocks:
        expr = b['expr']
        if 'is_android' in expr and 'not is_android' not in expr:
            # is_android block (active on Android)
            is_android_ids.update(extract_ids(b['inner']))
        elif 'not is_android' in expr:
            not_is_android_blocks.append(b)

    # Collect unconditional IDS_ (outside any <if>)
    unconditional_ids = collect_ids_outside_if(content, if_blocks)

    # Also collect IDS_ from OTHER conditional blocks (is_ios, etc.)
    # that would be inactive on Android — skip, they don't matter
    existing_ids = is_android_ids | unconditional_ids

    # Decide True/False for each not_is_android block
    decisions = []  # (block, 'True'/'False')
    true_count = 0
    false_count = 0

    for b in not_is_android_blocks:
        block_ids = extract_ids(b['inner'])
        overlap = block_ids & existing_ids
        if overlap:
            decisions.append((b, 'False'))
            false_count += 1
        else:
            decisions.append((b, 'True'))
            true_count += 1

    # Apply decisions by replacing expr in the original content
    # Process from END to START so positions don't shift
    decisions.sort(key=lambda x: x[0]['start'], reverse=True)

    for b, val in decisions:
        old_tag = content[b['start']:b['tag_end']]
        new_tag = '<if expr="%s">' % val
        content = content[:b['start']] + new_tag + content[b['tag_end']:]

    with open(grd_path, "w", encoding="utf-8") as f:
        f.write(content)

    return true_count, false_count, len(is_android_ids), len(unconditional_ids)


def main():
    print("=== GRD Android excludes patcher v5 (%s) ===" % datetime.now().isoformat())
    print()
    print("Strategy: not_is_android blocks with UNIQUE IDS_ → True (activate)")
    print("          not_is_android blocks with DUPLICATE IDS_ → False (is_android wins)")
    print()

    if not os.path.exists("chrome/app"):
        print("ERROR: Run from ~/chromium42/src/")
        return 1

    for grd in GRD_FILES:
        if not os.path.exists(grd):
            continue
        result = patch_grd_file(grd)
        if result is None:
            continue
        t, f, n_android, n_uncond = result
        print("  %s:" % grd)
        print("    is_android IDS_: %d, unconditional IDS_: %d" % (n_android, n_uncond))
        print("    not_is_android blocks: True=%d, False=%d" % (t, f))

    print()
    print("Next steps:")
    print("  rm -rf out/Release/gen/chrome/grit out/Release/gen/content/grit \\")
    print("         out/Release/gen/ui/grit out/Release/gen/components/grit")
    print("  gyp_chromium")
    print("  /usr/bin/ninja -C out/Release chrome_shell_apk")
    return 0


if __name__ == "__main__":
    sys.exit(main())
