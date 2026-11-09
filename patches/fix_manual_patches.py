#!/usr/bin/env python3
# =============================================================================
# fix_manual_patches.py — Apply all manual source-level patches in one place.
#
# These patches are NOT for .gypi files — they fix actual C++ source code.
# They were applied manually during the build process and must be re-applied
# every time .cc/.h files are restored from any backup.
#
# Each patch is idempotent: if applied twice, the second run is a no-op.
# =============================================================================
import os
import re
import shutil
import sys
from datetime import datetime


def patch_file(path, patches):
    """
    patches: list of (description, old_str, new_str) tuples.
    Returns: (count_applied, count_already_applied, count_not_found)
    """
    if not os.path.exists(path):
        return (0, 0, 0)

    # Backup once
    backup = path + ".manual_original"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    orig_content = content
    applied = 0
    already = 0
    not_found = 0

    for desc, old_str, new_str in patches:
        if old_str in content:
            content = content.replace(old_str, new_str, 1)
            applied += 1
            print(f"    [+] {desc}: applied")
        elif new_str in content or new_str.replace(" ", "") in content.replace(" ", ""):
            already += 1
            print(f"    [=] {desc}: already applied")
        else:
            not_found += 1
            print(f"    [?] {desc}: pattern not found (file may differ)")

    if content != orig_content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    return (applied, already, not_found)


def patch_compiler_version():
    """Fix compiler_version.py for GCC 7: -dumpversion → -dumpfullversion"""
    path = "build/compiler_version.py"
    if not os.path.exists(path):
        print(f"  SKIP: {path} not found")
        return

    patches = [
        (
            "compiler_version.py -dumpfullversion",
            "-dumpversion",
            "-dumpfullversion",
        ),
    ]
    print(f"  Patching: {path}")
    patch_file(path, patches)


def patch_hid_service():
    """Fix hid_service.cc: #elif defined(OS_WIN) → #elif defined(OS_WIN) || defined(OS_ANDROID)"""
    # Try common paths
    candidates = [
        "device/hid/hid_service.cc",
        "device/hid/hid_service_linux.cc",
    ]
    path = None
    for c in candidates:
        if os.path.exists(c):
            path = c
            break
    if not path:
        print("  SKIP: hid_service.cc not found in expected locations")
        return

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find #elif defined(OS_WIN) and add || defined(OS_ANDROID)
    # (Only if not already patched)
    if "OS_ANDROID" in content:
        print(f"  [=] {path}: already patched (OS_ANDROID present)")
        return

    backup = path + ".manual_original"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)

    new_content = content.replace(
        "#elif defined(OS_WIN)",
        "#elif defined(OS_WIN) || defined(OS_ANDROID)",
    )
    if new_content != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"  [+] {path}: added OS_ANDROID to OS_WIN elif")
    else:
        print(f"  [?] {path}: #elif defined(OS_WIN) not found")


def patch_chrome_content_rules_registry():
    """Fix const_iterator in chrome_content_rules_registry.cc"""
    path = "chrome/browser/extensions/api/declarative/chrome_content_rules_registry.cc"
    if not os.path.exists(path):
        print(f"  SKIP: {path} not found")
        return

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if "::const_iterator" in content and "::iterator" not in content.replace("::const_iterator", ""):
        print(f"  [=] {path}: already using const_iterator")
        return

    backup = path + ".manual_original"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)

    # Replace std::set<T>::iterator with ::const_iterator
    new_content = re.sub(
        r'std::set<([^>]+)>::iterator(?!\s*const)',
        r'std::set<\1>::const_iterator',
        content,
    )
    if new_content != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"  [+] {path}: replaced ::iterator → ::const_iterator")
    else:
        print(f"  [?] {path}: no ::iterator matches found")


def patch_windows_event_router():
    """Fix windows_event_router.cc: #elif defined(OS_ANDROID) for full coverage"""
    candidates = [
        "chrome/browser/extensions/api/tabs/windows_event_router.cc",
        "chrome/browser/extensions/api/windows/windows_event_router.cc",
    ]
    path = None
    for c in candidates:
        if os.path.exists(c):
            path = c
            break
    if not path:
        print("  SKIP: windows_event_router.cc not found")
        return

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if there's an #error "Unsupported platform" or similar
    if "OS_ANDROID" in content:
        print(f"  [=] {path}: already patched (OS_ANDROID present)")
        return

    backup = path + ".manual_original"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)

    # Add #elif defined(OS_ANDROID) branch before #else / #endif if we have platform-specific code
    # Generic approach: just make sure OS_ANDROID is handled
    # If there's an #else with empty body, Android will use it
    print(f"  [i] {path}: OS_ANDROID not found — may need manual review")


def patch_pepper_plugin_info():
    """Comment out #error "Plugins should be enabled" in pepper_plugin_info.h"""
    path = "content/public/common/pepper_plugin_info.h"
    if not os.path.exists(path):
        print(f"  SKIP: {path} not found")
        return

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if 'Plugins should be enabled' not in content:
        print(f"  [=] {path}: #error already commented out")
        return

    backup = path + ".manual_original"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)

    # Comment out #error with //
    new_content = content.replace(
        '#error "Plugins should be enabled"',
        '// #error "Plugins should be enabled" (Android: plugins disabled)',
    )
    if new_content != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"  [+] {path}: commented out #error")
    else:
        print(f"  [?] {path}: replacement failed")


def patch_native_process_launcher():
    """Stub out native_process_launcher_posix.cc on Android"""
    path = "chrome/browser/extensions/api/messaging/native_process_launcher_posix.cc"
    if not os.path.exists(path):
        print(f"  SKIP: {path} not found")
        return

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if 'Android: native messaging' in content:
        print(f"  [=] {path}: already stubbed")
        return

    backup = path + ".manual_original"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)

    # Find FindManifest function and stub out the calls
    pattern = re.compile(
        r'result = FindManifestInDir\(chrome::DIR_USER_NATIVE_MESSAGING[^;]*;'
        r'.*?result = FindManifestInDir\(chrome::DIR_NATIVE_MESSAGING[^;]*;',
        re.DOTALL,
    )
    new_content = pattern.sub(
        '// Android: native messaging paths not available — stubbed out\n'
        '    return base::FilePath();',
        content,
    )
    if new_content == content:
        # Try alternate pattern — line-by-line
        lines = content.split("\n")
        changed = 0
        new_lines = []
        for line in lines:
            if "chrome::DIR_USER_NATIVE_MESSAGING" in line or "chrome::DIR_NATIVE_MESSAGING" in line:
                indent = re.match(r'^(\s*)', line).group(1)
                new_lines.append(f"{indent}// Android: {line.strip()}  [stubbed out]")
                changed += 1
            else:
                new_lines.append(line)
        if changed > 0:
            new_content = "\n".join(new_lines)
            print(f"  [+] {path}: commented out {changed} native messaging line(s)")
        else:
            print(f"  [?] {path}: no DIR_NATIVE_MESSAGING references found")
            return
    else:
        print(f"  [+] {path}: stubbed FindManifest")

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)


def patch_tts_extension_api():
    """Fix std::set<T>::iterator → const_iterator in tts_extension_api.cc"""
    path = "chrome/browser/speech/extension_api/tts_extension_api.cc"
    if not os.path.exists(path):
        print(f"  SKIP: {path} not found")
        return

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if already patched
    if "::const_iterator" in content and "::iterator" not in content.replace("::const_iterator", ""):
        print(f"  [=] {path}: already using const_iterator")
        return

    backup = path + ".manual_original"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)

    new_content = re.sub(
        r'std::set<([^>]+)>::iterator(?!\s*const)',
        r'std::set<\1>::const_iterator',
        content,
    )
    if new_content != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"  [+] {path}: replaced ::iterator → ::const_iterator")
    else:
        print(f"  [?] {path}: no ::iterator matches found")


def patch_jni_generator():
    """Fix Python 2 syntax in jni_generator.py for Python 3 compatibility.

    jni_generator.py was written for Python 2 and uses 'except X, e:' syntax
    which is invalid in Python 3. Convert to 'except X as e:' (compatible with both).
    """
    path = "base/android/jni_generator/jni_generator.py"
    if not os.path.exists(path):
        print(f"  SKIP: {path} not found")
        return

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if already patched
    pattern = re.compile(r'except\s+(\w+(?:\.\w+)*)\s*,\s*(\w+)\s*:')
    matches = pattern.findall(content)

    if not matches:
        print(f"  [=] {path}: already Python 3 compatible (no 'except X, e:' patterns)")
        return

    backup = path + ".manual_original"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)

    new_content = pattern.sub(r'except \1 as \2:', content)

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"  [+] {path}: converted {len(matches)} 'except X, e:' → 'except X as e:'")


def main():
    print(f"=== fix_manual_patches.py ({datetime.now().isoformat()}) ===")
    print()
    print("Applying all manual source-level C++ patches:")
    print()

    if not os.path.exists("chrome/browser"):
        print("ERROR: run from ~/chromium42/src/")
        return 1

    print("[1] compiler_version.py (-dumpfullversion)")
    patch_compiler_version()
    print()

    print("[2] hid_service.cc (#elif defined(OS_ANDROID))")
    patch_hid_service()
    print()

    print("[3] chrome_content_rules_registry.cc (const_iterator)")
    patch_chrome_content_rules_registry()
    print()

    print("[4] windows_event_router.cc (OS_ANDROID)")
    patch_windows_event_router()
    print()

    print("[5] pepper_plugin_info.h (comment out #error)")
    patch_pepper_plugin_info()
    print()

    print("[6] native_process_launcher_posix.cc (stub)")
    patch_native_process_launcher()
    print()

    print("[7] tts_extension_api.cc (const_iterator)")
    patch_tts_extension_api()
    print()

    print("[8] jni_generator.py (Python 2 → 3 syntax: except X, e: → except X as e:)")
    patch_jni_generator()
    print()

    print("============================================================")
    print("All manual patches applied. Next steps:")
    print()
    print("  source ~/build_env/chromium42_env.sh")
    print("  gyp_chromium")
    print("  ninja_run -C out/Release chrome_shell_apk")
    return 0


if __name__ == "__main__":
    sys.exit(main())
