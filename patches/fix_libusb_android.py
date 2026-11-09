#!/usr/bin/env python3
# =============================================================================
# fix_libusb_android.py — patch libusb.gyp to add Android support.
#
# Chromium 42's libusb.gyp doesn't have Android-specific conditions.
# On Android:
#   - 'OS=="linux" or OS=="mac"' doesn't match → no POSIX threads → 
#     "unknown type name 'usbi_mutex_t'" error
#   - 'OS=="linux"' doesn't match → no OS_LINUX define →
#     "Unsupported OS" #error in core.c
#
# This script:
#   1. Adds OS=="android" to the POSIX threads condition (for usbi_mutex_t)
#   2. Adds OS=="android" to the OS_LINUX condition (for linux_usbfs backend)
#   3. Adds OS=="android" to the linux_netlink condition (no udev on Android)
#
# Android is POSIX-based and Linux-kernel-based, so it can use the same
# backend code as Linux. libusb functions will return errors at runtime
# (no /dev/bus/usb access without root), but compilation succeeds.
# =============================================================================
import os
import re
import shutil
import sys
from datetime import datetime

GYP_PATH = "third_party/libusb/libusb.gyp"
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

    changes = 0

    # Patch 1: Add Android to POSIX threads condition
    old1 = "['OS==\"linux\" or OS==\"mac\"', {"
    new1 = "['OS==\"linux\" or OS==\"mac\" or OS==\"android\"', {"
    if old1 in content:
        content = content.replace(old1, new1)
        changes += 1
        print(f"  Patched POSIX threads condition: added 'OS==\"android\"'")
    elif new1 in content:
        print(f"  POSIX threads condition already patched")
    else:
        print(f"  WARN: POSIX threads pattern not found")

    # Patch 2: Add Android to OS_LINUX condition (for linux_usbfs.c)
    old2 = "['OS==\"linux\"', {\n          'sources': [\n            'src/libusb/os/linux_usbfs.c',"
    new2 = "['OS==\"linux\" or OS==\"android\"', {\n          'sources': [\n            'src/libusb/os/linux_usbfs.c',"
    if old2 in content:
        content = content.replace(old2, new2)
        changes += 1
        print(f"  Patched OS_LINUX condition: added 'OS==\"android\"'")
    elif new2 in content:
        print(f"  OS_LINUX condition already patched")
    else:
        print(f"  WARN: OS_LINUX pattern not found")

    # Patch 3: Do NOT add Android to linux_netlink condition.
    # linux_netlink.c uses SOCK_RAW which Android NDK API 14 doesn't define.
    # Android doesn't use netlink for hotplug events anyway.
    # Revert this condition to OS=="linux" only (without android).
    # 
    # If a previous run of this script patched it, undo that patch.
    old3 = "['(OS==\"linux\" or OS==\"android\") and use_udev==0', {"
    new3 = "['OS==\"linux\" and use_udev==0', {"
    if old3 in content:
        content = content.replace(old3, new3)
        changes += 1
        print(f"  Reverted linux_netlink condition: removed 'OS==\"android\"'")
    elif new3 in content:
        print(f"  linux_netlink condition correct (Android excluded)")
    else:
        print(f"  WARN: linux_netlink pattern not found")

    if changes > 0:
        with open(GYP_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\nApplied {changes} patches to libusb.gyp")
        print()
        print("Re-run gyp_chromium:")
        print("  gyp_chromium")
        print()
        print("Then re-run ninja:")
        print("  /usr/bin/ninja -C out/Release chrome_shell_apk")
    else:
        print("\nAll patches already applied — nothing to do.")
    return 0


if __name__ == "__main__":
    print(f"=== libusb Android patcher ({datetime.now().isoformat()}) ===")
    print()
    sys.exit(main())
