"""Iconografía propia de SOul — Vezzu Studio.

SVG dibujados a mano con un trazo consistente (24x24, stroke 1.7,
extremos redondeados). Se renderizan con el color que pida cada módulo,
así que no dependen del tema de iconos del sistema ni se ven genéricos.
"""
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib  # noqa: E402

_CACHE = {}

_BASE = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
    'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{sw}" '
    'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
)

# ---------------------------------------------------------------- trazos
PATHS = {
    # --- módulos ---
    "smart": (
        '<path d="M12 3l1.9 4.6L18.5 9.5 13.9 11.4 12 16l-1.9-4.6L5.5 9.5 10.1 7.6z"/>'
        '<path d="M18.5 16.2l.8 1.9 1.9.8-1.9.8-.8 1.9-.8-1.9-1.9-.8 1.9-.8z"/>'
    ),
    "cleanup": (
        '<path d="M14.6 3.6l5.8 5.8"/>'
        '<path d="M17.5 6.5L9.9 14.1"/>'
        '<path d="M10.6 11.4l2 2"/>'
        '<path d="M9.2 12.8l-4.4 4.4a2.6 2.6 0 000 3.7 2.6 2.6 0 003.7 0l4.4-4.4z"/>'
    ),
    "processes": (
        '<rect x="3.4" y="4.4" width="17.2" height="15.2" rx="2.6"/>'
        '<path d="M7 9h4M7 12.4h7.5M7 15.8h5.5"/>'
        '<circle cx="17.6" cy="9" r="1.5"/>'
    ),
    "performance": (
        '<path d="M4 17a8 8 0 1116 0"/>'
        '<path d="M12 17l4.2-4.8"/>'
        '<circle cx="12" cy="17" r="1.2"/>'
    ),
    "apps": (
        '<rect x="3.5" y="3.5" width="7" height="7" rx="2"/>'
        '<rect x="13.5" y="3.5" width="7" height="7" rx="2"/>'
        '<rect x="3.5" y="13.5" width="7" height="7" rx="2"/>'
        '<rect x="13.5" y="13.5" width="7" height="7" rx="2"/>'
    ),
    "privacy": (
        '<path d="M12 3l7 3v5.5c0 4.3-2.9 8.2-7 9.5-4.1-1.3-7-5.2-7-9.5V6z"/>'
        '<path d="M9.2 11.8l2 2 3.6-3.9"/>'
    ),
    "space": (
        '<circle cx="12" cy="12" r="8.5"/>'
        '<path d="M12 3.5V12l6 6"/>'
        '<circle cx="12" cy="12" r="1.6"/>'
    ),
    "health": (
        '<path d="M20.4 8.6a4.6 4.6 0 00-8.4-2.6 4.6 4.6 0 00-8.4 2.6c0 5 8.4 10.4 8.4 10.4s8.4-5.4 8.4-10.4z"/>'
        '<path d="M3.8 12.4h3.6l1.6-2.6 2 4.8 1.8-3.4 1.2 1.2h5.6"/>'
    ),
    # --- tareas ---
    "cache": (
        '<path d="M12 3.2l8.4 4.2-8.4 4.2-8.4-4.2z"/>'
        '<path d="M3.6 12l8.4 4.2 8.4-4.2"/>'
        '<path d="M3.6 16.4l8.4 4.2 8.4-4.2"/>'
    ),
    "thumbs": (
        '<rect x="3.4" y="4.6" width="17.2" height="14.8" rx="2.6"/>'
        '<circle cx="8.6" cy="9.8" r="1.6"/>'
        '<path d="M3.8 16.6l4.8-4.4 3.6 3.2 3-2.6 5 4.4"/>'
    ),
    "trash": (
        '<path d="M4.4 6.6h15.2"/>'
        '<path d="M9.4 6.6V4.9a1.4 1.4 0 011.4-1.4h2.4a1.4 1.4 0 011.4 1.4v1.7"/>'
        '<path d="M6.3 6.6l.9 12.1a1.9 1.9 0 001.9 1.8h5.8a1.9 1.9 0 001.9-1.8l.9-12.1"/>'
        '<path d="M10.3 10.4v6M13.7 10.4v6"/>'
    ),
    "packages": (
        '<path d="M20.4 8.2v7.6a1.7 1.7 0 01-.9 1.5l-6.7 3.6a1.7 1.7 0 01-1.6 0l-6.7-3.6a1.7 1.7 0 01-.9-1.5V8.2"/>'
        '<path d="M3.9 7.9l7.3-3.9a1.7 1.7 0 011.6 0l7.3 3.9-8.1 4.3z"/>'
        '<path d="M12 12.2V20"/>'
    ),
    "logs": (
        '<path d="M6.2 3.6h8.2l4.4 4.4v12.4a1.6 1.6 0 01-1.6 1.6H6.2a1.6 1.6 0 01-1.6-1.6V5.2a1.6 1.6 0 011.6-1.6z"/>'
        '<path d="M14.2 3.8V8h4.2"/>'
        '<path d="M8.4 12.6h7.2M8.4 15.8h7.2M8.4 18.4h4.4"/>'
    ),
    "flatpak": (
        '<path d="M12 3.6v9.8"/>'
        '<path d="M8.4 10l3.6 3.6 3.6-3.6"/>'
        '<path d="M4.6 15.4v3.2a1.8 1.8 0 001.8 1.8h11.2a1.8 1.8 0 001.8-1.8v-3.2"/>'
    ),
    "browser": (
        '<circle cx="12" cy="12" r="8.6"/>'
        '<path d="M3.5 12h17"/>'
        '<path d="M12 3.4c2.2 2.4 3.4 5.4 3.4 8.6s-1.2 6.2-3.4 8.6c-2.2-2.4-3.4-5.4-3.4-8.6S9.8 5.8 12 3.4z"/>'
    ),
    "cookies": (
        '<path d="M20.5 12.6A8.6 8.6 0 1111.2 3.5a3.4 3.4 0 004.6 4 3.4 3.4 0 004.7 5.1z"/>'
        '<circle cx="9.4" cy="10.4" r="1"/>'
        '<circle cx="13.6" cy="14.6" r="1"/>'
        '<circle cx="8.8" cy="15.4" r="1"/>'
    ),
    "recent": (
        '<circle cx="12" cy="12" r="8.6"/>'
        '<path d="M12 6.8V12l3.6 2.2"/>'
    ),
    "shell": (
        '<rect x="3.2" y="4.4" width="17.6" height="15.2" rx="2.6"/>'
        '<path d="M7.4 9.6l2.8 2.6-2.8 2.6"/>'
        '<path d="M12.8 15.2h4"/>'
    ),
    "crash": (
        '<path d="M12 3.4l8.6 15a1.8 1.8 0 01-1.6 2.7H5a1.8 1.8 0 01-1.6-2.7z"/>'
        '<path d="M12 9.4v4.4"/>'
        '<circle cx="12" cy="17.2" r="0.9"/>'
    ),
    "dev": (
        '<path d="M8.6 7.6L3.8 12l4.8 4.4"/>'
        '<path d="M15.4 7.6L20.2 12l-4.8 4.4"/>'
        '<path d="M13.4 4.6l-2.8 14.8"/>'
    ),
    "kofi": (
        '<path d="M4.4 6h12.2v6.6a4.4 4.4 0 01-4.4 4.4H8.8a4.4 4.4 0 01-4.4-4.4z"/>'
        '<path d="M16.6 8.2h1.6a2.6 2.6 0 010 5.2h-1.6"/>'
        '<path d="M7.6 3v1.6M11 3v1.6M14.4 3v1.6"/>'
    ),
    "settings": (
        '<circle cx="12" cy="12" r="2.8"/>'
        '<path d="M12 3.6v2.4M12 18v2.4M20.4 12h-2.4M6 12H3.6"/>'
        '<path d="M17.7 6.3l-1.7 1.7M8 16l-1.7 1.7M17.7 17.7L16 16M8 8L6.3 6.3"/>'
    ),
}

COLORES = {
    "smart": "#A88BFF",
    "processes": "#5BA8F5",
    "cleanup": "#3FD9B0",
    "performance": "#FFB259",
    "apps": "#5BA8F5",
    "privacy": "#F27BC8",
    "space": "#8093F7",
    "health": "#4FD98A",
    "logs": "#F2B84B",
    "default": "#9FB0C4",
}


def pintar(nombre, size=20, color=None):
    """Devuelve un Gtk.Image con el icono dibujado en el color pedido."""
    color = color or COLORES.get(nombre, COLORES["default"])
    clave = (nombre, size, color)
    if clave in _CACHE:
        return Gtk.Image.new_from_paintable(_CACHE[clave])

    body = PATHS.get(nombre)
    if body is None:
        img = Gtk.Image.new_from_icon_name("application-x-executable-symbolic")
        img.set_pixel_size(size)
        return img

    grosor = 1.7 if size <= 28 else 1.5
    svg = _BASE.format(size=size * 2, color=color, sw=grosor, body=body).encode("utf-8")
    try:
        stream = Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(svg))
        pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
            stream, size * 2, size * 2, True, None)
        textura = Gdk.Texture.new_for_pixbuf(pixbuf)
        _CACHE[clave] = textura
        img = Gtk.Image.new_from_paintable(textura)
        img.set_pixel_size(size)
        return img
    except Exception:
        img = Gtk.Image.new_from_icon_name("application-x-executable-symbolic")
        img.set_pixel_size(size)
        return img


# --- casilla de seleccion: propia, multicolor, no pasa por pintar() ---
# GTK con el CheckButton por defecto casi no se ve contra un fondo
# oscuro y con tema personalizado — de ahi que nadie notara si estaba
# marcado o no. Esta se dibuja entera a mano, con tres estados bien
# distintos a simple vista.
_CASILLA_SVG = {
    "off": (
        '<rect x="2.5" y="2.5" width="17" height="17" rx="5.5" '
        'fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.32)" stroke-width="1.6"/>'
    ),
    "on": (
        '<rect x="2.5" y="2.5" width="17" height="17" rx="5.5" '
        'fill="#8A7CFF" stroke="#A88BFF" stroke-width="1.6"/>'
        '<path d="M6.6 11.2l3 3 5.6-6.1" fill="none" stroke="#ffffff" '
        'stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "done": (
        '<circle cx="11" cy="11" r="8.5" fill="rgba(63,217,176,0.16)" '
        'stroke="#3FD9B0" stroke-width="1.6"/>'
        '<path d="M6.6 11.2l3 3 5.2-5.6" fill="none" stroke="#3FD9B0" '
        'stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/>'
    ),
}
_CASILLA_CACHE = {}


def casilla(estado, size=22):
    """estado: 'off' (sin marcar), 'on' (marcada, se va a limpiar),
    'done' (ya estaba limpio, no hace falta marcarla)."""
    clave = (estado, size)
    if clave in _CASILLA_CACHE:
        return Gtk.Image.new_from_paintable(_CASILLA_CACHE[clave])
    cuerpo = _CASILLA_SVG.get(estado, _CASILLA_SVG["off"])
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size*2}" height="{size*2}" '
           f'viewBox="0 0 22 22">{cuerpo}</svg>').encode("utf-8")
    stream = Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(svg))
    pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream, size * 2, size * 2, True, None)
    textura = Gdk.Texture.new_for_pixbuf(pixbuf)
    _CASILLA_CACHE[clave] = textura
    img = Gtk.Image.new_from_paintable(textura)
    img.set_pixel_size(size)
    return img


def logo_svg(size=64, color="#A88BFF"):
    """Marca de SOul: una esfera con el destello del escaneo."""
    body = (
        '<circle cx="12" cy="12" r="8.4" stroke-opacity="0.45"/>'
        '<path d="M12 4.2a7.8 7.8 0 015.6 13.3" stroke-opacity="0.95"/>'
        '<path d="M12 8.2l1.3 3.1 3.1 1.3-3.1 1.3L12 17l-1.3-3.1L7.6 12.6l3.1-1.3z"/>'
    )
    svg = _BASE.format(size=size, color=color, sw=1.5, body=body).encode("utf-8")
    stream = Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(svg))
    pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream, size, size, True, None)
    return Gdk.Texture.new_for_pixbuf(pixbuf)
