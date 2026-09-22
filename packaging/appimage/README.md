# Empaquetado en AppImage

`build.sh` genera `SOul-x86_64.AppImage` en la raíz del repo.

## Qué empaqueta y qué no

El AppImage lleva dentro el código de SOul y las librerías de GTK4 /
libadwaita (vía `linuxdeploy` + su plugin de GTK). **No** lleva un
intérprete de Python propio: usa el `python3` del sistema, con
`python3-gobject` (el binding `gi`) instalado. Esto es así porque
empaquetar un CPython + PyGObject completos y reubicables dentro de un
AppImage es frágil y poco confiable; casi cualquier escritorio
GNOME/KDE moderno en Fedora ya trae `python3-gobject` de fábrica, así
que en la práctica no es un requisito nuevo para el usuario. Si falta,
el AppImage lo dice claro al abrir en vez de fallar en silencio.

El ayudante de root (`soul-mantenimiento.sh`) y su política de polkit
viajan dentro del AppImage y se instalan solos la primera vez que
hace falta una acción de administrador (un solo `pkexec`, ver
`soul/core.py:instalar_polkit`).

## Requisitos para compilar

- `gtk4-devel` y `libadwaita-devel` instalados (para que
  `linuxdeploy-plugin-gtk` encuentre `gtk4.pc`).
- Las herramientas en `tools/` (no van al repo, se descargan aparte):

```bash
mkdir -p tools && cd tools
curl -fLo linuxdeploy https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
curl -fLo linuxdeploy-plugin-gtk https://raw.githubusercontent.com/linuxdeploy/linuxdeploy-plugin-gtk/master/linuxdeploy-plugin-gtk.sh
curl -fLo appimagetool https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x linuxdeploy linuxdeploy-plugin-gtk appimagetool
```

## Compilar

```bash
./packaging/appimage/build.sh
```

## Probar

```bash
./SOul-x86_64.AppImage
```
