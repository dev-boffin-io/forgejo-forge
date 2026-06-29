"""
gitignore_templates.py — .gitignore content for common project types.

Each entry in TEMPLATES is a dict:
  name     : display name (shown in UI)
  icon     : emoji for the button
  content  : the .gitignore block (string)
"""
from __future__ import annotations

TEMPLATES: list[dict] = [

    # ── Python ────────────────────────────────────────────────────────────────
    {
        "name": "Python",
        "icon": "🐍",
        "content": """\
# === Python ===
__pycache__/
*.py[cod]
*$py.class
*.so
*.egg
*.egg-info/
dist/
build/
eggs/
parts/
var/
sdist/
develop-eggs/
.installed.cfg
lib/
lib64/
.eggs/

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Distribution / packaging
.Python
pip-log.txt
pip-delete-this-directory.txt
MANIFEST

# Testing
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/
htmlcov/

# Jupyter Notebook
.ipynb_checkpoints

# pyenv
.python-version

# mypy / pyright
.mypy_cache/
.dmypy.json
dmypy.json
.pytype/
pyrightconfig.json

# Ruff
.ruff_cache/
""",
    },

    # ── Node / JavaScript / TypeScript ───────────────────────────────────────
    {
        "name": "Node / JS / TS",
        "icon": "🟨",
        "content": """\
# === Node / JavaScript / TypeScript ===
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*
lerna-debug.log*

dist/
dist-ssr/
build/
out/
.output/

*.local
.env
.env.*
!.env.example

# Vite
.vite/

# Next.js
.next/
out/

# Nuxt
.nuxt/
.output/

# Parcel
.parcel-cache/

# TypeScript
*.tsbuildinfo

# Misc
.DS_Store
*.pem
.vercel
.netlify
""",
    },

    # ── Flutter / Dart ───────────────────────────────────────────────────────
    {
        "name": "Flutter / Dart",
        "icon": "💙",
        "content": """\
# === Flutter / Dart ===
# Dart
.dart_tool/
.packages
.pub-cache/
.pub/
pubspec.lock

# Flutter
build/
.flutter-plugins
.flutter-plugins-dependencies
.metadata
*.g.dart
*.freezed.dart
*.gr.dart

# Android
**/android/local.properties
**/android/.gradle/
**/android/captures/
**/android/gradlew
**/android/gradlew.bat
**/android/gradle/wrapper/gradle-wrapper.jar
**/android/key.properties
*.keystore
*.jks

# iOS / macOS
**/ios/Pods/
**/ios/.symlinks/
**/macos/Pods/
**/macos/.symlinks/

# Web
lib/generated_plugin_registrant.dart

# IDEs
.idea/
.vscode/
*.iml
""",
    },

    # ── Android (native) ─────────────────────────────────────────────────────
    {
        "name": "Android",
        "icon": "🤖",
        "content": """\
# === Android ===
*.iml
.gradle/
local.properties
.idea/
.DS_Store
build/
captures/
.externalNativeBuild/
.cxx/
*.keystore
!debug.keystore
google-services.json
""",
    },

    # ── Java ─────────────────────────────────────────────────────────────────
    {
        "name": "Java",
        "icon": "☕",
        "content": """\
# === Java ===
*.class
*.log
*.jar
*.war
*.nar
*.ear
*.zip
*.tar.gz
*.rar

# Build
target/
build/
out/

# Maven
pom.xml.tag
pom.xml.releaseBackup
pom.xml.versionsBackup
pom.xml.next
release.properties
dependency-reduced-pom.xml
buildNumber.properties
.mvn/timing.properties
.mvn/wrapper/maven-wrapper.jar

# Gradle
.gradle/
gradle-app.setting
!gradle-wrapper.jar

# IDEs
.idea/
*.iml
*.iws
.classpath
.project
.settings/
""",
    },

    # ── Rust ─────────────────────────────────────────────────────────────────
    {
        "name": "Rust",
        "icon": "🦀",
        "content": """\
# === Rust ===
debug/
target/
Cargo.lock
**/*.rs.bk
*.pdb
""",
    },

    # ── Go ───────────────────────────────────────────────────────────────────
    {
        "name": "Go",
        "icon": "🐹",
        "content": """\
# === Go ===
*.exe
*.exe~
*.dll
*.so
*.dylib
*.test
*.out
go.sum
vendor/
""",
    },

    # ── C / C++ ──────────────────────────────────────────────────────────────
    {
        "name": "C / C++",
        "icon": "⚙️",
        "content": """\
# === C / C++ ===
*.o
*.ko
*.obj
*.elf
*.ilk
*.map
*.exp
*.gch
*.pch
*.lib
*.a
*.la
*.lo
*.dll
*.so
*.so.*
*.dylib
*.exe
*.out
*.app
*.i*86
*.x86_64
*.hex

# Build
build/
cmake-build-*/
CMakeFiles/
CMakeCache.txt
cmake_install.cmake
Makefile
""",
    },

    # ── React / Vite ─────────────────────────────────────────────────────────
    {
        "name": "React / Vite",
        "icon": "⚛️",
        "content": """\
# === React / Vite ===
node_modules/
dist/
dist-ssr/
*.local
.env
.env.*
!.env.example
.vite/
.DS_Store
""",
    },

    # ── Django ───────────────────────────────────────────────────────────────
    {
        "name": "Django",
        "icon": "🎸",
        "content": """\
# === Django ===
*.pyc
__pycache__/
db.sqlite3
db.sqlite3-journal
media/
staticfiles/
.env
.venv/
venv/
*.log
local_settings.py
""",
    },

    # ── Laravel / PHP ────────────────────────────────────────────────────────
    {
        "name": "Laravel / PHP",
        "icon": "🐘",
        "content": """\
# === Laravel / PHP ===
vendor/
node_modules/
public/hot
public/storage
storage/*.key
.env
.env.backup
.phpunit.result.cache
Homestead.json
Homestead.yaml
npm-debug.log
yarn-error.log
/.idea
/.vscode
""",
    },

    # ── Unity ────────────────────────────────────────────────────────────────
    {
        "name": "Unity",
        "icon": "🎮",
        "content": """\
# === Unity ===
[Ll]ibrary/
[Tt]emp/
[Oo]bj/
[Bb]uild/
[Bb]uilds/
[Ll]ogs/
[Uu]ser[Ss]ettings/
[Mm]emoryCaptures/
[Rr]ecordings/
Assets/AssetStoreTools*
*.pidb.meta
*.pdb.meta
*.mdb.meta
sysinfo.txt
*.apk
*.aab
*.unitypackage
*.app
crashlytics-build.properties
export.gradle
""",
    },

    # ── macOS ────────────────────────────────────────────────────────────────
    {
        "name": "macOS",
        "icon": "🍎",
        "content": """\
# === macOS ===
.DS_Store
.AppleDouble
.LSOverride
Icon
._*
.DocumentRevisions-V100
.fseventsd
.Spotlight-V100
.TemporaryItems
.Trashes
.VolumeIcon.icns
.com.apple.timemachine.donotpresent
.AppleDB
.AppleDesktop
Network Trash Folder
Temporary Items
.apdisk
""",
    },

    # ── Windows ──────────────────────────────────────────────────────────────
    {
        "name": "Windows",
        "icon": "🪟",
        "content": """\
# === Windows ===
Thumbs.db
Thumbs.db:encryptable
ehthumbs.db
ehthumbs_vista.db
*.stackdump
[Dd]esktop.ini
$RECYCLE.BIN/
*.cab
*.msi
*.msix
*.msm
*.msp
*.lnk
""",
    },

    # ── Linux ────────────────────────────────────────────────────────────────
    {
        "name": "Linux",
        "icon": "🐧",
        "content": """\
# === Linux ===
*~
.fuse_hidden*
.directory
.Trash-*
.nfs*
""",
    },

    # ── VS Code ──────────────────────────────────────────────────────────────
    {
        "name": "VS Code",
        "icon": "🔵",
        "content": """\
# === VS Code ===
.vscode/*
!.vscode/settings.json
!.vscode/tasks.json
!.vscode/launch.json
!.vscode/extensions.json
!.vscode/*.code-snippets
.history/
*.vsix
""",
    },

    # ── JetBrains IDEs ───────────────────────────────────────────────────────
    {
        "name": "JetBrains",
        "icon": "🧠",
        "content": """\
# === JetBrains IDEs ===
.idea/
*.iml
*.iws
*.ipr
out/
!**/src/main/**/out/
!**/src/test/**/out/
cmake-build-*/
.idea_modules/
atlassian-ide-plugin.xml
com_crashlytics_export_strings.xml
crashlytics.properties
crashlytics-build.properties
fabric.properties
""",
    },

    # ── Docker ───────────────────────────────────────────────────────────────
    {
        "name": "Docker",
        "icon": "🐳",
        "content": """\
# === Docker ===
.docker/
docker-compose.override.yml
.env
*.env
""",
    },

    # ── Terraform ────────────────────────────────────────────────────────────
    {
        "name": "Terraform",
        "icon": "🏗️",
        "content": """\
# === Terraform ===
.terraform/
.terraform.lock.hcl
*.tfstate
*.tfstate.*
crash.log
crash.*.log
*.tfvars
*.tfvars.json
override.tf
override.tf.json
*_override.tf
*_override.tf.json
.terraformrc
terraform.rc
""",
    },

]

# Quick lookup by name
TEMPLATE_MAP: dict[str, str] = {t["name"]: t["content"] for t in TEMPLATES}


def combine_templates(names: list[str]) -> str:
    """Merge multiple templates into one .gitignore content string."""
    parts = []
    for name in names:
        if name in TEMPLATE_MAP:
            parts.append(TEMPLATE_MAP[name])
    return "\n".join(parts)
