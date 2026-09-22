"""Icono en la bandeja del sistema.

Implementa StatusNotifierItem directamente sobre D-Bus (el estándar que usa
KDE Plasma y también GNOME con extensión). Se hace así a propósito, en vez
de usar libappindicator, porque esa librería es GTK3 y obligaría a meter
GTK3 entero dentro del AppImage además de GTK4.
"""
import os

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib  # noqa: E402

ICONO_NOMBRE = "studio.vezzu.SOul"

INTROSPECCION = """
<node>
  <interface name="org.kde.StatusNotifierItem">
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="IconThemePath" type="s" access="read"/>
    <property name="ToolTip" type="(sa(iiay)ss)" access="read"/>
    <property name="ItemIsMenu" type="b" access="read"/>
    <method name="Activate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="SecondaryActivate">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="ContextMenu">
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
    </method>
    <method name="Scroll">
      <arg name="delta" type="i" direction="in"/>
      <arg name="dir" type="s" direction="in"/>
    </method>
    <signal name="NewIcon"/>
    <signal name="NewStatus"><arg name="status" type="s"/></signal>
    <signal name="NewToolTip"/>
  </interface>
</node>
"""

LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24"
 fill="none" stroke="#A88BFF" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
<circle cx="12" cy="12" r="8.4" stroke-opacity="0.5"/>
<path d="M12 4.2a7.8 7.8 0 015.6 13.3" stroke-opacity="0.95"/>
<path d="M12 8.2l1.3 3.1 3.1 1.3-3.1 1.3L12 17l-1.3-3.1L7.6 12.6l3.1-1.3z"/>
</svg>"""


def instalar_icono():
    """Deja el logo donde el sistema busca iconos, para poder nombrarlo."""
    destino = os.path.expanduser("~/.local/share/icons/hicolor/scalable/apps")
    try:
        os.makedirs(destino, exist_ok=True)
        ruta = os.path.join(destino, f"{ICONO_NOMBRE}.svg")
        with open(ruta, "w") as f:
            f.write(LOGO_SVG)
        return destino
    except OSError:
        return ""


class Bandeja:
    """Publica el icono y avisa cuando el usuario hace clic."""

    def __init__(self, al_activar, titulo="SOul", tooltip="SOul by Vezzu Studio"):
        self.al_activar = al_activar
        self.titulo = titulo
        self.tooltip = tooltip
        self.icon_path = instalar_icono()
        self.conexion = None
        self.reg_id = None
        self._nodo = Gio.DBusNodeInfo.new_for_xml(INTROSPECCION)

        Gio.bus_own_name(
            Gio.BusType.SESSION,
            f"org.kde.StatusNotifierItem-{os.getpid()}-1",
            Gio.BusNameOwnerFlags.NONE,
            self._on_bus, self._on_name, None,
        )

    # --- publicación del objeto
    def _on_bus(self, conexion, _nombre):
        self.conexion = conexion
        try:
            self.reg_id = conexion.register_object(
                "/StatusNotifierItem",
                self._nodo.interfaces[0],
                self._metodo, self._propiedad, None,
            )
        except GLib.Error:
            self.reg_id = None

    def _on_name(self, conexion, nombre):
        """Cuando ya somos dueños del nombre, nos registramos con el sistema."""
        def listo(fuente, res):
            try:
                fuente.call_finish(res)
            except GLib.Error:
                pass  # no hay bandeja disponible: la app sigue igual

        conexion.call(
            "org.kde.StatusNotifierWatcher", "/StatusNotifierWatcher",
            "org.kde.StatusNotifierWatcher", "RegisterStatusNotifierItem",
            GLib.Variant("(s)", (nombre,)), None,
            Gio.DBusCallFlags.NONE, 4000, None, listo,
        )

    # --- interfaz
    def _metodo(self, _con, _sender, _path, _iface, metodo, _params, invocacion):
        if metodo in ("Activate", "SecondaryActivate", "ContextMenu"):
            GLib.idle_add(self.al_activar)
        invocacion.return_value(None)

    def _propiedad(self, _con, _sender, _path, _iface, prop):
        if prop == "Category":
            return GLib.Variant("s", "SystemServices")
        if prop == "Id":
            return GLib.Variant("s", "SOul")
        if prop == "Title":
            return GLib.Variant("s", self.titulo)
        if prop == "Status":
            return GLib.Variant("s", "Active")
        if prop == "IconName":
            return GLib.Variant("s", ICONO_NOMBRE)
        if prop == "IconThemePath":
            return GLib.Variant("s", self.icon_path)
        if prop == "ItemIsMenu":
            return GLib.Variant("b", False)
        if prop == "ToolTip":
            return GLib.Variant("(sa(iiay)ss)",
                                (ICONO_NOMBRE, [], self.titulo, self.tooltip))
        return None
