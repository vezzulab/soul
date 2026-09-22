#!/bin/bash
# Arma el AppImage de SOul (Vezzu Studio).
#
# Requiere las herramientas en packaging/appimage/tools/ (descargadas
# aparte, no van al repo): linuxdeploy, linuxdeploy-plugin-gtk, appimagetool.
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(cd "$AQUI/../.." && pwd)"
HERRAMIENTAS="$AQUI/tools"
APPDIR="$AQUI/AppDir"

for h in linuxdeploy linuxdeploy-plugin-gtk appimagetool; do
    if [ ! -x "$HERRAMIENTAS/$h" ]; then
        echo "Falta $HERRAMIENTAS/$h — descárgalo antes de correr este script." >&2
        exit 1
    fi
done

echo "==> Limpiando AppDir anterior"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" \
         "$APPDIR/usr/lib/soul/soul" \
         "$APPDIR/usr/lib/soul/packaging" \
         "$APPDIR/usr/share/applications" \
         "$APPDIR/usr/share/icons/hicolor/scalable/apps"

echo "==> Copiando el código de SOul"
cp "$RAIZ/soul-app.py" "$APPDIR/usr/lib/soul/soul-app.py"
cp "$RAIZ"/soul/*.py "$APPDIR/usr/lib/soul/soul/"
cp "$RAIZ/packaging/soul-mantenimiento.sh" "$APPDIR/usr/lib/soul/packaging/"
cp "$RAIZ/packaging/studio.vezzu.soul.policy" "$APPDIR/usr/lib/soul/packaging/"

echo "==> Lanzador, icono y AppRun"
cp "$AQUI/studio.vezzu.SOul.desktop" "$APPDIR/usr/share/applications/"
cp "$AQUI/studio.vezzu.SOul.desktop" "$APPDIR/"
cp "$RAIZ/web/assets/soul.svg" "$APPDIR/usr/share/icons/hicolor/scalable/apps/studio.vezzu.SOul.svg"
cp "$RAIZ/web/assets/soul.svg" "$APPDIR/studio.vezzu.SOul.svg"
install -m 0755 "$AQUI/AppRun" "$APPDIR/AppRun"

# ejecutable señuelo: linuxdeploy exige un binario ELF real para el
# .desktop y para detectar la libc/arquitectura del AppImage. SOul en
# si es Python, así que este binario no se usa en tiempo de ejecución
# (AppRun llama a python3 directamente) — se usa /usr/bin/true, ya
# compilado en el sistema, solo como muestra de arquitectura/libc.
cp /usr/bin/true "$APPDIR/usr/bin/soul-app"

echo "==> Empaquetando GTK4/libadwaita con linuxdeploy"
export LINUXDEPLOY_PLUGIN_GTK_SKIP_APPSTREAM=1
export DEPLOY_GTK_VERSION=4
"$HERRAMIENTAS/linuxdeploy" \
    --appdir "$APPDIR" \
    --executable "$APPDIR/usr/bin/soul-app" \
    --library /usr/lib64/libgtk-4.so.1 \
    --library /usr/lib64/libadwaita-1.so.0 \
    --desktop-file "$AQUI/studio.vezzu.SOul.desktop" \
    --icon-file "$RAIZ/web/assets/soul.svg" \
    --plugin gtk

echo "==> Generando el AppImage"
cd "$AQUI"
ARCH=x86_64 "$HERRAMIENTAS/appimagetool" "$APPDIR" "$RAIZ/SOul-x86_64.AppImage"

echo
echo "Listo: $RAIZ/SOul-x86_64.AppImage"
echo "Necesita python3-gobject, gtk4 y libadwaita instalados en el sistema"
echo "que lo ejecute (SOul solo empaqueta su propio código + libs de GTK)."
