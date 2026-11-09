#!/bin/bash
# =============================================================================
# stub_google_play_services.sh — create empty stub for Google Play Services
#                                 SDK that Chromium 42 GYP expects.
#
# Chromium 42 build references google_play_services in:
#   sdk/extras/google/google_play_services/libproject/google-play-services_lib/
#
# But this directory doesn't exist in the android_tools repo anymore
# (Google moved GMS to Maven/Google Play Services SDK distribution).
#
# This script creates the minimal stub structure that:
#   1. Makes `find ... -type f` not fail with "No such file or directory"
#   2. Provides a minimal valid JAR file (so Java compilation doesn't fail)
#   3. Provides minimal AndroidManifest.xml and project.properties
#   4. Provides a minimal res/values/strings.xml
#
# What this loses: Google Sign-in, GCM (push), Location, Maps. We don't care
# because (a) we're targeting Android 4.0 where GMS is dead anyway, and
# (b) we plan to apply ungoogled-chromium patches later that strip all
# Google integration.
# =============================================================================
set -e

SDK_ROOT="${1:-$HOME/chromium42/src/third_party/android_tools/sdk}"
GMS_DIR="$SDK_ROOT/extras/google/google_play_services/libproject/google-play-services_lib"

echo "=== Creating Google Play Services stub ==="
echo "SDK root: $SDK_ROOT"
echo "GMS dir:  $GMS_DIR"
echo ""

# Check SDK root exists
if [ ! -d "$SDK_ROOT" ]; then
    echo "ERROR: SDK root not found at $SDK_ROOT"
    echo "Usage: $0 [path_to_sdk]"
    exit 1
fi

# Create directory structure
mkdir -p "$GMS_DIR/res/values"
mkdir -p "$GMS_DIR/res/layout"
mkdir -p "$GMS_DIR/res/drawable"
mkdir -p "$GMS_DIR/res/drawable-hdpi"
mkdir -p "$GMS_DIR/res/drawable-mdpi"
mkdir -p "$GMS_DIR/res/drawable-xhdpi"
mkdir -p "$GMS_DIR/res/drawable-xxhdpi"
mkdir -p "$GMS_DIR/libs"
mkdir -p "$GMS_DIR/src/com/google/android/gms"
echo "✓ Created directory structure"

# Create minimal AndroidManifest.xml
cat > "$GMS_DIR/AndroidManifest.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<!-- Stub Google Play Services library manifest.
     Created by stub_google_play_services.sh for Chromium 42 build.
     Real GMS is not available for Android 4.0 anymore. -->
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.google.android.gms"
    android:versionCode="7095000"
    android:versionName="7.0.95">

    <uses-sdk android:minSdkVersion="9" />

</manifest>
EOF
echo "✓ Created AndroidManifest.xml"

# Create project.properties (needed by Android build system)
cat > "$GMS_DIR/project.properties" <<'EOF'
# Stub Google Play Services project properties.
# Created by stub_google_play_services.sh
target=android-21
android.library=true
EOF
echo "✓ Created project.properties"

# Create minimal res/values/strings.xml (so aapt doesn't fail)
cat > "$GMS_DIR/res/values/strings.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<!-- Stub Google Play Services strings. -->
<resources>
    <string name="gms_stub">Google Play Services (stub)</string>
</resources>
EOF
echo "✓ Created res/values/strings.xml"

# Create minimal res/values/styles.xml (some Android builds need this)
cat > "$GMS_DIR/res/values/styles.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<resources>
</resources>
EOF
echo "✓ Created res/values/styles.xml"

# Create empty placeholder drawables for common GMS resources that GYP may scan
# (without these, some aapt invocations may fail)
for d in drawable drawable-hdpi drawable-mdpi drawable-xhdpi drawable-xxhdpi; do
    cat > "$GMS_DIR/res/$d/.gitkeep" <<'EOF'
EOF
done
echo "✓ Created drawable placeholders"

# Create a minimal valid empty JAR file (zip with MANIFEST.MF only — NO .class files!)
# This needs `zip` installed: sudo apt install zip
#
# IMPORTANT: We MUST NOT include any .class files in this JAR, because:
#   - The Android `dx` tool parses every .class file inside the JAR
#   - If the .class is empty/truncated, dx fails with:
#     "com.android.dx.cf.iface.ParseException: severely truncated class file"
#   - An empty JAR (just MANIFEST.MF) is accepted by dx without errors
cd "$GMS_DIR/libs"
TMPDIR=$(mktemp -d)
mkdir -p "$TMPDIR/META-INF"
cat > "$TMPDIR/META-INF/MANIFEST.MF" <<'EOF'
Manifest-Version: 1.0
Created-By: stub_google_play_services.sh
Implementation-Title: Google Play Services (stub — no classes)
Implementation-Version: 7.0.95
EOF

# Build the JAR — ONLY MANIFEST.MF, no .class files
(cd "$TMPDIR" && zip -q -r "$GMS_DIR/libs/google-play-services.jar" . )
rm -rf "$TMPDIR"

echo "✓ Created google-play-services.jar (empty stub, no .class files — dx-safe)"

# Create a stub src/com/google/android/gms/R.java
# IMPORTANT: must be a unique class (no fields, just declaration)
# This is needed because GYP's java.gypi enumerates ALL .java files
# in java_in_dir/src/ as compilation inputs.
# 
# This stub R.java will compile fine (it's a valid Java class).
# The generated R.java (from res/) will be excluded by --jar-excluded-classes
# pattern in javac invocation (see jar_excluded_classes in android_tools.gyp).
mkdir -p "$GMS_DIR/src/com/google/android/gms"
cat > "$GMS_DIR/src/com/google/android/gms/R.java" <<'EOF'
// Stub R.java — created by stub_google_play_services.sh
// This is a placeholder; real R.java is generated by GYP from res/.
// This stub exists because GYP enumerates src/**/*.java as inputs.
// jar.py excludes */R.class via jar_excluded_classes, so this class
// will NOT appear in the final jar.
package com.google.android.gms;

public final class R {
    private R() {}
}
EOF
echo "✓ Created src/com/google/android/gms/R.java (stub — empty class)"

# IMPORTANT: We also need at least one NON-R.java file in src/ that will
# remain in the jar after jar.py excludes */R.class. Otherwise `jar cf0`
# fails with "c flag requires manifest or input files to be specified!".
# Create a stub GmsStub class that survives the exclusion filter.
cat > "$GMS_DIR/src/com/google/android/gms/GmsStub.java" <<'EOF'
// Stub GmsStub.java — created by stub_google_play_services.sh
// This class exists so that jar.py has at least one .class file to pack
// after excluding R.class (via jar_excluded_classes="*/R.class").
package com.google.android.gms;

public class GmsStub {
    public GmsStub() {}
}
EOF
echo "✓ Created src/com/google/android/gms/GmsStub.java (placeholder class)"

# Also remove res/values/strings.xml to PREVENT GYP from generating
# a conflicting R.java with string resource IDs.
# Without res/ files, GYP's process_resources action will produce an
# empty R.java (no fields), which won't conflict with our stub.
# But find ... -type f needs at least one file, so keep .gitkeep
rm -f "$GMS_DIR/res/values/strings.xml" "$GMS_DIR/res/values/styles.xml"
# Re-add minimal placeholder so find doesn't fail
cat > "$GMS_DIR/res/values/strings.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<resources>
</resources>
EOF
echo "  (replaced res/values/strings.xml with empty <resources/>)"

echo "=== Stub created successfully ==="
echo ""
echo "Verifying structure:"
find "$GMS_DIR" -type f | sort
echo ""
echo "JAR file info:"
ls -la "$GMS_DIR/libs/google-play-services.jar"
echo ""
echo "Test find command (the one GYP uses):"
find "$GMS_DIR/res" -type f
echo ""
echo "Now re-run gyp_chromium:"
echo "  cd ~/chromium42/src"
echo "  gyp_chromium"
