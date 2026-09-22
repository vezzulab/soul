#!/bin/bash
# Ayudante de mantenimiento de SOul (Vezzu Studio).
#
# Se ejecuta como root a través de pkexec. Por seguridad NO acepta comandos
# libres: solo esta lista cerrada de tareas. El único argumento variable es
# el identificador de una app Flatpak, y se valida con una expresión
# estricta antes de usarlo.
set -euo pipefail

case "${1:-}" in
  dnf-cache)
    dnf clean packages
    ;;
  journal)
    journalctl --vacuum-time=2weeks
    ;;
  flatpak-unused)
    flatpak uninstall --unused -y
    ;;
  coredumps)
    # volcados de programas que se cerraron mal: solo sirven para depurar
    journalctl --vacuum-time=1s --identifier=systemd-coredump >/dev/null 2>&1 || true
    find /var/lib/systemd/coredump -type f -delete 2>/dev/null || true
    ;;
  autoremove)
    dnf autoremove -y
    ;;
  flatpak-remove)
    APP_ID="${2:-}"
    # solo letras, números, punto, guion y guion bajo: nada de rutas,
    # espacios, comillas ni separadores de comando.
    if ! [[ "$APP_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._+-]{1,127}$ ]]; then
      echo "Identificador de app no válido" >&2
      exit 2
    fi
    # debe existir de verdad como app instalada
    if ! flatpak list --app --columns=application | grep -qx -- "$APP_ID"; then
      echo "Esa app Flatpak no está instalada" >&2
      exit 3
    fi
    flatpak uninstall -y -- "$APP_ID"
    ;;
  smart)
    # solo LEE el estado SMART de un disco. No escribe nada.
    DEV="${2:-}"
    if ! [[ "$DEV" =~ ^/dev/(nvme[0-9]+n[0-9]+|sd[a-z]+|hd[a-z]+|mmcblk[0-9]+)$ ]]; then
      echo "Dispositivo no válido" >&2
      exit 5
    fi
    smartctl -j -a -- "$DEV"
    ;;
  install-policy)
    # instala la política que evita pedir la contraseña cada vez
    ORIGEN="${2:-}"
    if [ ! -f "$ORIGEN" ]; then
      echo "No encuentro el archivo de política" >&2
      exit 4
    fi
    install -m 0644 -o root -g root "$ORIGEN" \
      /usr/share/polkit-1/actions/studio.vezzu.soul.policy
    ;;
  *)
    echo "Uso: soul-mantenimiento.sh {dnf-cache|journal|coredumps|autoremove|flatpak-unused|flatpak-remove <app-id>|install-policy <ruta>}" >&2
    exit 1
    ;;
esac
