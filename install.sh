#!/bin/bash
# Instala SOul (Vezzu Studio) en Fedora / derivadas.
set -euo pipefail
cd "$(dirname "$0")"
RAIZ="$(pwd)"

echo "==> Comprobando dependencias"
python3 -c "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1')" 2>/dev/null \
  || sudo dnf install -y python3-gobject gtk4 libadwaita
python3 -c "import psutil" 2>/dev/null || sudo dnf install -y python3-psutil
command -v smartctl >/dev/null || sudo dnf install -y smartmontools

echo "==> Instalando el ayudante de mantenimiento"
sudo install -m 0755 -o root -g root \
  packaging/soul-mantenimiento.sh /usr/local/bin/soul-mantenimiento.sh

echo "==> Creando el lanzador del menú"
mkdir -p ~/.local/share/applications ~/.local/share/icons/hicolor/scalable/apps
cat > ~/.local/share/applications/studio.vezzu.SOul.desktop <<DESKTOP
[Desktop Entry]
Type=Application
Name=SOul
GenericName=System care
Comment=SO + alma: el alma de tu sistema, en simple
Exec=python3 $RAIZ/soul-app.py
Icon=studio.vezzu.SOul
Terminal=false
Categories=System;Monitor;Utility;
DESKTOP
update-desktop-database ~/.local/share/applications 2>/dev/null || true

echo
echo "Listo. Abre SOul desde el menú de aplicaciones."
echo "La primera vez te ofrecerá dar permiso una sola vez para no"
echo "volver a pedirte la contraseña."
