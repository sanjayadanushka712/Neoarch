#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="NeoArch"
EXEC_PATH="$REPO_DIR/bin/neoarch.sh"
ICON_SVG="$REPO_DIR/assets/icons/NeoarchLogo.svg"
ICON_PNG="$REPO_DIR/assets/icons/app/icon.png"
if [[ -f "$ICON_SVG" ]]; then
  ICON_PATH="$ICON_SVG"
else
  ICON_PATH="$ICON_PNG"
fi
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/neoarch.desktop"
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=$APP_NAME
Comment=NeoArch Package Manager
Exec="$EXEC_PATH"
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=System;Utility;
EOF
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" || true
fi
printf "Installed desktop entry: %s\n" "$DESKTOP_FILE"
