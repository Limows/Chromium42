#!/usr/bin/env python3
# =============================================================================
# fix_stlport_vector_data.py — patch STLport's <vector> headers to add
#                               std::vector::data() method (C++11).
#
# Problem: NDK r9d uses STLport which doesn't have vector::data().
# Chromium 42 code uses vector.data() in many places (C++11 feature).
#
# STLport has TWO vector implementations:
#   1. stl/_vector.h — main vector class (uses this->_M_start)
#   2. stl/pointers/_vector.h — pointer specialization (uses _M_impl.begin())
#      Activated by _STLP_USE_PTR_SPECIALIZATIONS=1 (set in GYP_DEFINES)
#
# This script patches BOTH files.
# =============================================================================
import os
import re
import shutil
import sys
from datetime import datetime

# Path to STLport vector headers
NDK_STL = "third_party/android_tools/ndk/sources/cxx-stl/stlport/stlport/stl"

MAIN_VECTOR = f"{NDK_STL}/_vector.h"
PTR_VECTOR = f"{NDK_STL}/pointers/_vector.h"


def patch_main_vector():
    """Patch stl/_vector.h — add data() using this->_M_start"""
    if not os.path.exists(MAIN_VECTOR):
        print(f"  SKIP (file not found): {MAIN_VECTOR}")
        return False

    backup = MAIN_VECTOR + ".original"
    if not os.path.exists(backup):
        shutil.copy2(MAIN_VECTOR, backup)

    with open(MAIN_VECTOR, "r", errors="replace") as f:
        content = f.read()

    if "fix_stlport_vector_data.py" in content:
        print(f"  Already patched: {MAIN_VECTOR}")
        return False

    # Find insertion point — after back() methods
    # Pattern: '  const_reference back() const  { return *(end() - 1); }'
    pattern = re.compile(
        r"(  const_reference back\(\) const  \{ return \*\(end\(\) - 1\); \})",
    )
    match = pattern.search(content)
    if not match:
        # Try without double space
        pattern = re.compile(
            r"(  const_reference back\(\) const \{ return \*\(end\(\) - 1\); \})",
        )
        match = pattern.search(content)

    if not match:
        print(f"  WARN: Could not find back() in {MAIN_VECTOR}")
        return False

    insert_pos = match.end()
    data_methods = """
  // === Added by fix_stlport_vector_data.py — C++11 vector::data() ===
  value_type* data() { return this->_M_start; }
  const value_type* data() const { return this->_M_start; }
  // === End fix_stlport_vector_data.py ===
"""
    new_content = content[:insert_pos] + data_methods + content[insert_pos:]

    with open(MAIN_VECTOR, "w") as f:
        f.write(new_content)

    print(f"  Patched: {MAIN_VECTOR} (added data() using this->_M_start)")
    return True


def patch_ptr_vector():
    """Patch stl/pointers/_vector.h — add data() using begin()"""
    if not os.path.exists(PTR_VECTOR):
        print(f"  SKIP (file not found): {PTR_VECTOR}")
        return False

    backup = PTR_VECTOR + ".original"
    if not os.path.exists(backup):
        shutil.copy2(PTR_VECTOR, backup)

    with open(PTR_VECTOR, "r", errors="replace") as f:
        content = f.read()

    if "fix_stlport_vector_data.py" in content:
        print(f"  Already patched: {PTR_VECTOR}")
        return False

    # Find insertion point — after back() methods
    # Pattern: '  const_reference back() const  { return cast_traits::to_value_type_cref(_M_impl.back()); }'
    pattern = re.compile(
        r"(  const_reference back\(\) const  \{ return cast_traits::to_value_type_cref\(_M_impl\.back\(\)\); \})",
    )
    match = pattern.search(content)
    if not match:
        print(f"  WARN: Could not find back() in {PTR_VECTOR}")
        # Show what back() looks like
        back_lines = [l for l in content.split('\n') if 'back()' in l]
        for l in back_lines:
            print(f"    Found: {l.strip()}")
        return False

    insert_pos = match.end()
    # In pointers/_vector.h, data is accessed through begin() which does
    # cast_traits conversion. Using begin() is the safest approach.
    data_methods = """
  // === Added by fix_stlport_vector_data.py — C++11 vector::data() ===
  pointer data() { return begin(); }
  const_pointer data() const { return begin(); }
  // === End fix_stlport_vector_data.py ===
"""
    new_content = content[:insert_pos] + data_methods + content[insert_pos:]

    with open(PTR_VECTOR, "w") as f:
        f.write(new_content)

    print(f"  Patched: {PTR_VECTOR} (added data() using begin())")
    return True


def main():
    print(f"=== STLport vector::data() patcher ({datetime.now().isoformat()}) ===")
    print()

    if not os.path.exists("third_party/android_tools/ndk"):
        print("ERROR: Run from ~/chromium42/src/")
        return 1

    changes = 0
    print("Patching main vector header (stl/_vector.h):")
    if patch_main_vector():
        changes += 1

    print("\nPatching pointer specialization vector (stl/pointers/_vector.h):")
    if patch_ptr_vector():
        changes += 1

    if changes > 0:
        print(f"\nApplied {changes} patches.")
        print()
        print("Re-run ninja (no need to re-run gyp_chromium):")
        print("  /usr/bin/ninja -C out/Release chrome_shell_apk")
    else:
        print("\nAll patches already applied — nothing to do.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
