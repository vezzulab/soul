"""Interfaz de SOul — GTK4 + libadwaita.

Estructura: barra lateral con módulos (como CleanMyMac) y un panel
principal con degradado propio por módulo.
"""
import os
import subprocess
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gdk, Gio  # noqa: E402

from . import core  # noqa: E402
from . import icons  # noqa: E402
from .orb import Orbe  # noqa: E402
from .tray import Bandeja  # noqa: E402
from .i18n import t, get_idioma, set_idioma  # noqa: E402

KOFI_URL = "https://ko-fi.com/vezzustudio"
WEB_URL = "https://github.com/vezzulab/soul"

MODULOS = [
    ("smart", "nav.smart", "smart", "grad-smart"),
    ("processes", "nav.processes", "processes", "grad-proc"),
    ("cleanup", "nav.cleanup", "cleanup", "grad-cleanup"),
    ("performance", "nav.performance", "performance", "grad-perf"),
    ("apps", "nav.apps", "apps", "grad-apps"),
    ("privacy", "nav.privacy", "privacy", "grad-privacy"),
    ("space", "nav.space", "space", "grad-space"),
    ("health", "nav.health", "health", "grad-health"),
]


def en_hilo(func, callback=None):
    """Corre algo pesado fuera de la interfaz para que no se congele."""
    def trabajo():
        try:
            res = func()
            error = None
        except Exception as e:  # noqa: BLE001
            res, error = None, e
        if callback:
            GLib.idle_add(callback, res, error)
    threading.Thread(target=trabajo, daemon=True).start()


# ---------------------------------------------------------------- piezas

class Tarjeta(Gtk.Box):
    """Tarjeta base con borde suave."""

    def __init__(self, clase="card"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add_css_class(clase)


class FilaTarea(Gtk.Box):
    """Una tarea de limpieza: icono, nombre, tamaño, casilla y botón."""

    def __init__(self, ventana, tarea, on_toggle=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.add_css_class("task-row")
        self.tarea, self.ventana, self.on_toggle = tarea, ventana, on_toggle
        self.tam = None

        # el CheckButton real de GTK queda oculto: solo se usa para
        # guardar el estado (activo/sensible) y emitir la señal
        # 'toggled'. Lo que se VE es self.indicador, dibujado a mano,
        # porque el checkbox por defecto de GTK casi no se distinguía
        # contra el fondo oscuro — nadie notaba si estaba marcado o no.
        self.check = Gtk.CheckButton()
        self.check.set_visible(False)
        self.check.connect("toggled", self._al_cambiar_estado)
        self.append(self.check)

        self.indicador = icons.casilla("off", 22)
        self.indicador.set_valign(Gtk.Align.CENTER)
        self.append(self.indicador)

        icono = icons.pintar(tarea["icono"], 22)
        icono.add_css_class("task-icon")
        icono.set_valign(Gtk.Align.CENTER)
        self.append(icono)

        textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, hexpand=True)
        self.lbl_titulo = Gtk.Label(label=t(tarea["titulo"]), xalign=0)
        self.lbl_titulo.add_css_class("task-title")
        self.lbl_desc = Gtk.Label(label=t(tarea["desc"]), xalign=0, wrap=True)
        self.lbl_desc.add_css_class("task-desc")
        textos.append(self.lbl_titulo)
        textos.append(self.lbl_desc)
        self.append(textos)

        self.lbl_tam = Gtk.Label(label=t("action.calculating"))
        self.lbl_tam.add_css_class("task-size")
        self.lbl_tam.set_valign(Gtk.Align.CENTER)
        self.append(self.lbl_tam)

        # toda la fila responde al clic, no solo la casilla
        self.set_cursor(Gdk.Cursor.new_from_name("pointer", None))
        clic = Gtk.GestureClick()
        clic.connect("released", self._on_clic_fila)
        self.add_controller(clic)

        self.medir()

    def _on_clic_fila(self, *_args):
        if self.check.get_sensitive():
            self.check.set_active(not self.check.get_active())

    def _al_cambiar_estado(self, *_args):
        """Redibuja el indicador cada vez que cambia el estado real,
        vengasea por un clic o porque medir() lo puso asi de entrada."""
        if not self.check.get_sensitive() and not self.check.get_active():
            estado = "done"   # ya estaba limpio, no hace falta tocarlo
        elif self.check.get_active():
            estado = "on"     # marcada, se va a limpiar
        else:
            estado = "off"    # sin marcar
        nuevo = icons.casilla(estado, 22)
        self.remove(self.indicador)
        self.indicador = nuevo
        self.indicador.set_valign(Gtk.Align.CENTER)
        self.insert_child_after(self.indicador, self.check)
        if self.on_toggle:
            self.on_toggle()

    def medir(self):
        self.lbl_tam.set_label(t("action.calculating"))
        self.check.set_sensitive(False)
        en_hilo(self.tarea["scan"], self._medido)

    def _medido(self, tam, error):
        self.tam = 0 if error else tam
        if tam is None:
            self.lbl_tam.set_label("—")
            self.check.set_sensitive(True)
            # tambien respeta 'peligroso' aqui: antes se marcaba solo
            # sin importar la bandera, y "Paquetes que ya nadie usa"
            # (que si es peligroso) salia marcado por defecto sin querer
            self.check.set_active(not self.tarea.get("peligroso"))
        elif tam < 1024 * 1024:
            self.lbl_tam.set_label(t("action.already_clean"))
            self.check.set_sensitive(False)
            self.check.set_active(False)
        else:
            self.lbl_tam.set_label(core.fmt_size(tam))
            self.check.set_sensitive(True)
            self.check.set_active(not self.tarea.get("peligroso"))
        self._al_cambiar_estado()
        if self.on_toggle:
            self.on_toggle()
        return False

    @property
    def seleccionada(self):
        return self.check.get_active() and self.check.get_sensitive()

    def limpiar(self, cuando_termine):
        self.lbl_tam.set_label(t("action.cleaning"))

        def hacer():
            self.tarea["clean"]()
            return True

        def listo(_res, error):
            if error is not None:
                msg = t("action.failed")
                if isinstance(error, RuntimeError) and str(error) == "browser_open":
                    msg = ("Cierra el navegador primero." if get_idioma() == "es"
                           else "Close the browser first.")
                elif isinstance(error, subprocess.CalledProcessError):
                    msg = t("action.cancelled")
                self.ventana.aviso(msg)
            self.medir()
            cuando_termine()
            return False

        en_hilo(hacer, listo)


class FilaSimple(Gtk.Box):
    """Fila genérica: nombre a la izquierda, dato y botón a la derecha."""

    def __init__(self, titulo, detalle="", boton=None, on_click=None, destructivo=False):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.add_css_class("item-row")

        caja = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=True)
        lbl = Gtk.Label(label=titulo, xalign=0, ellipsize=3)
        lbl.add_css_class("item-title")
        caja.append(lbl)
        if detalle:
            sub = Gtk.Label(label=detalle, xalign=0, ellipsize=3)
            sub.add_css_class("item-sub")
            caja.append(sub)
        self.append(caja)

        if boton:
            btn = Gtk.Button(label=boton)
            btn.add_css_class("pill")
            btn.add_css_class("destructive-action" if destructivo else "soul-btn")
            btn.set_valign(Gtk.Align.CENTER)
            if on_click:
                btn.connect("clicked", lambda *_: on_click())
            self.append(btn)
            self.boton = btn


def seccion(titulo, subtitulo=None):
    caja = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    lbl = Gtk.Label(label=titulo, xalign=0)
    lbl.add_css_class("section-title")
    caja.append(lbl)
    if subtitulo:
        sub = Gtk.Label(label=subtitulo, xalign=0, wrap=True)
        sub.add_css_class("section-sub")
        caja.append(sub)
    return caja


# ---------------------------------------------------------------- vistas

class VistaBase(Gtk.Box):
    def __init__(self, ventana, clave_grad, ancho_maximo=1000):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.ventana = ventana
        self.add_css_class(clave_grad)
        self.scroll = Gtk.ScrolledWindow(vexpand=True)
        self.contenido = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.contenido.set_margin_top(28)
        self.contenido.set_margin_bottom(40)
        self.contenido.set_margin_start(36)
        self.contenido.set_margin_end(36)
        # ancho máximo para que el texto no quede estirado en pantallas
        # grandes; las vistas de tabla (como Procesos) piden uno mayor,
        # para aprovechar el espacio en vez de dejarlo en blanco.
        clamp = Adw.Clamp(maximum_size=ancho_maximo, tightening_threshold=820)
        clamp.set_child(self.contenido)
        self.scroll.set_child(clamp)
        self.append(self.scroll)

    def cabecera(self, titulo, desc):
        caja = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        caja.add_css_class("page-head")
        h = Gtk.Label(label=titulo, xalign=0)
        h.add_css_class("page-title")
        d = Gtk.Label(label=desc, xalign=0, wrap=True)
        d.add_css_class("page-desc")
        caja.append(h)
        caja.append(d)
        self.contenido.append(caja)

    def refrescar(self):
        pass


class VistaLista(VistaBase):
    """Vista genérica de tareas con casillas y un botón de limpiar."""

    def __init__(self, ventana, clave_grad, titulo, desc, tareas):
        super().__init__(ventana, clave_grad)
        self.cabecera(titulo, desc)
        self.tareas_def = tareas
        self.filas = []

        caja = Tarjeta()
        for tarea in tareas:
            fila = FilaTarea(ventana, tarea, on_toggle=self.actualizar_total)
            self.filas.append(fila)
            caja.append(fila)
        self.contenido.append(caja)

        barra = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        barra.set_halign(Gtk.Align.END)
        self.lbl_total = Gtk.Label(label="")
        self.lbl_total.add_css_class("total-label")
        self.lbl_total.set_valign(Gtk.Align.CENTER)
        barra.append(self.lbl_total)

        self.btn = Gtk.Button(label=t("action.clean_selected"))
        self.btn.add_css_class("pill")
        self.btn.add_css_class("cta")
        self.btn.connect("clicked", self.on_limpiar)
        barra.append(self.btn)
        self.contenido.append(barra)

        nota = Gtk.Label(label=t("safe.note"), xalign=0, wrap=True)
        nota.add_css_class("safe-note")
        self.contenido.append(nota)

    def actualizar_total(self):
        total = sum((f.tam or 0) for f in self.filas if f.seleccionada)
        hay = any(f.seleccionada for f in self.filas)
        self.lbl_total.set_label(core.fmt_size(total) if total else "")
        self.btn.set_sensitive(hay)
        return False

    def on_limpiar(self, _btn):
        elegidas = [f for f in self.filas if f.seleccionada]
        if not elegidas:
            return
        total = core.fmt_size(sum((f.tam or 0) for f in elegidas))
        nombres = ", ".join(t(f.tarea["titulo"]) for f in elegidas)
        necesita_pass = any(f.tarea.get("root") for f in elegidas)
        cuerpo = nombres + (t("action.needs_password") if necesita_pass else "")

        dlg = Adw.AlertDialog(heading=t("dialog.clean", name=total), body=cuerpo)
        dlg.add_response("cancel", t("action.cancel"))
        dlg.add_response("ok", t("action.clean"))
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("cancel")
        dlg.set_close_response("cancel")

        def respuesta(_d, resp):
            if resp != "ok":
                return
            self.btn.set_sensitive(False)
            self.btn.set_label(t("action.cleaning"))
            self._pendientes = len(elegidas)

            def una_menos():
                self._pendientes -= 1
                if self._pendientes <= 0:
                    self.btn.set_label(t("action.clean_selected"))
                    self.ventana.aviso(t("action.done"))
                    self.actualizar_total()

            for f in elegidas:
                f.limpiar(una_menos)

        dlg.connect("response", respuesta)
        dlg.present(self.ventana)

    def refrescar(self):
        for f in self.filas:
            f.medir()


class VistaSmart(VistaBase):
    """Pantalla principal: un botón grande que revisa todo."""

    def __init__(self, ventana):
        super().__init__(ventana, "grad-smart")
        self.contenido.set_valign(Gtk.Align.CENTER)
        self.resultados = {}

        caja = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22)
        caja.set_halign(Gtk.Align.CENTER)

        self.titulo = Gtk.Label(label=t("smart.title"))
        self.titulo.add_css_class("hero-title")
        caja.append(self.titulo)

        self.desc = Gtk.Label(label=t("smart.desc"), wrap=True, justify=Gtk.Justification.CENTER)
        self.desc.add_css_class("hero-desc")
        self.desc.set_max_width_chars(52)
        caja.append(self.desc)

        self.orbe = Orbe(244)
        self.orbe.set_texto(t("smart.button"))
        self.orbe.connect("clicked", self.on_scan)
        caja.append(self.orbe)

        self.estado = Gtk.Label(label="")
        self.estado.add_css_class("hero-state")
        caja.append(self.estado)

        self.tiles = Gtk.FlowBox()
        self.tiles.set_selection_mode(Gtk.SelectionMode.NONE)
        self.tiles.set_max_children_per_line(3)
        self.tiles.set_column_spacing(12)
        self.tiles.set_row_spacing(12)
        self.tiles.set_halign(Gtk.Align.CENTER)
        caja.append(self.tiles)

        self.btn_limpiar = Gtk.Button(label=t("smart.run"))
        self.btn_limpiar.add_css_class("pill")
        self.btn_limpiar.add_css_class("cta")
        self.btn_limpiar.set_halign(Gtk.Align.CENTER)
        self.btn_limpiar.set_visible(False)
        self.btn_limpiar.connect("clicked", self.on_limpiar_todo)
        caja.append(self.btn_limpiar)

        self.contenido.append(caja)

    def on_scan(self, _btn):
        self.orbe.set_girando(True)
        self.orbe.set_texto("")
        self.estado.set_label(t("smart.scanning"))
        self.tiles.remove_all() if hasattr(self.tiles, "remove_all") else self._vaciar_tiles()
        self.btn_limpiar.set_visible(False)

        def trabajo():
            res = []
            for tarea in core.TAREAS_LIMPIEZA + core.TAREAS_PRIVACIDAD:
                if tarea.get("peligroso"):
                    continue
                try:
                    tam = tarea["scan"]()
                except Exception:
                    tam = 0
                if tam and tam > 1024 * 1024:
                    res.append((tarea, tam))
            return res

        en_hilo(trabajo, self._scan_listo)

    def _vaciar_tiles(self):
        hijo = self.tiles.get_first_child()
        while hijo:
            sig = hijo.get_next_sibling()
            self.tiles.remove(hijo)
            hijo = sig

    def _scan_listo(self, res, _error):
        self.orbe.set_girando(False)
        self.orbe.set_texto(t("action.rescan"))
        res = res or []
        self.encontrado = res
        total = sum(tam for _t, tam in res)
        self._vaciar_tiles()
        if not res:
            self.estado.set_label(t("smart.nothing"))
            return False
        self.estado.set_label(t("smart.found", size=core.fmt_size(total)))
        for tarea, tam in res:
            tile = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            tile.add_css_class("tile")
            ic = icons.pintar(tarea["icono"], 24)
            ic.add_css_class("tile-icon")
            ic.set_halign(Gtk.Align.CENTER)
            nom = Gtk.Label(label=t(tarea["titulo"]), wrap=True, justify=Gtk.Justification.CENTER)
            nom.add_css_class("tile-name")
            val = Gtk.Label(label=core.fmt_size(tam))
            val.add_css_class("tile-size")
            tile.append(ic)
            tile.append(nom)
            tile.append(val)
            self.tiles.append(tile)
        self.btn_limpiar.set_visible(True)
        self.btn_limpiar.set_sensitive(True)
        self.btn_limpiar.set_label(t("smart.run"))
        return False

    def on_limpiar_todo(self, _btn):
        if not getattr(self, "encontrado", None):
            return
        total = core.fmt_size(sum(tam for _t, tam in self.encontrado))
        necesita = any(tar.get("root") for tar, _ in self.encontrado)
        dlg = Adw.AlertDialog(
            heading=t("dialog.clean", name=total),
            body=", ".join(t(tar["titulo"]) for tar, _ in self.encontrado)
            + (t("action.needs_password") if necesita else ""),
        )
        dlg.add_response("cancel", t("action.cancel"))
        dlg.add_response("ok", t("action.clean"))
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("cancel")
        dlg.set_close_response("cancel")

        def respuesta(_d, resp):
            if resp != "ok":
                return
            self.btn_limpiar.set_sensitive(False)
            self.btn_limpiar.set_label(t("smart.cleaning"))
            liberado = sum(tam for _t, tam in self.encontrado)

            def trabajo():
                for tarea, _tam in self.encontrado:
                    try:
                        tarea["clean"]()
                    except Exception:
                        continue
                return True

            def listo(_r, _e):
                self.btn_limpiar.set_visible(False)
                self.estado.set_label(t("smart.cleaned", size=core.fmt_size(liberado)))
                self._vaciar_tiles()
                self.ventana.aviso(t("smart.cleaned", size=core.fmt_size(liberado)))
                return False

            en_hilo(trabajo, listo)

        dlg.connect("response", respuesta)
        dlg.present(self.ventana)


class FilaProceso(Gtk.Box):
    """Una fila de la tabla de procesos: nombre traducido y uso real.
    Solo las apps reconocidas (columna izquierda) llevan boton de cerrar;
    las de segundo plano son informativas, para no invitar a tocar algo
    que no se entiende del todo."""

    def __init__(self, ventana, datos, con_boton):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.add_css_class("item-row")
        self.ventana = ventana
        self.datos = datos

        punto = Gtk.Box(width_request=8, height_request=8, valign=Gtk.Align.CENTER)
        punto.add_css_class("proc-dot")
        punto.add_css_class("verde" if datos["reconocido"] else "gris")
        self.append(punto)

        textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=True)
        lbl = Gtk.Label(label=datos["nombre"], xalign=0, ellipsize=3)
        lbl.add_css_class("item-title")
        textos.append(lbl)
        desc = datos["desc"] or ""
        if datos["procesos"] > 1:
            extra = t("proc.instances", n=datos["procesos"])
            desc = f"{desc} · {extra}" if desc else extra
        if desc:
            sub = Gtk.Label(label=desc, xalign=0, wrap=True)
            sub.add_css_class("item-sub")
            textos.append(sub)
        self.append(textos)

        lbl_cpu = Gtk.Label(label=f"{datos['cpu']:.0f}%", xalign=1)
        lbl_cpu.add_css_class("proc-metric")
        lbl_cpu.set_size_request(44, -1)
        self.append(lbl_cpu)

        lbl_mb = Gtk.Label(label=core.fmt_size(datos["mb"] * 1024 * 1024), xalign=1)
        lbl_mb.add_css_class("proc-metric")
        lbl_mb.set_size_request(64, -1)
        self.append(lbl_mb)

        if con_boton:
            btn = Gtk.Button(label=t("perf.close"))
            btn.add_css_class("destructive-action")
            btn.add_css_class("pill")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect("clicked", self.on_cerrar)
            self.append(btn)

    def on_cerrar(self, _btn):
        dlg = Adw.AlertDialog(heading=t("dialog.close_app", name=self.datos["nombre"]),
                              body=t("dialog.close_app.body"))
        dlg.add_response("cancel", t("action.cancel"))
        dlg.add_response("ok", t("perf.close"))
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.set_close_response("cancel")

        def resp(_d, r):
            if r == "ok":
                core.cerrar_app(self.datos["pids"])
                GLib.timeout_add(1200, lambda: (self.ventana.refrescar_procesos(), False)[1])
        dlg.connect("response", resp)
        dlg.present(self.ventana)


class VistaProcesos(VistaBase):
    """El corazon de SOul: la tabla de htop, traducida y en vivo.
    Dos columnas separan lo que reconoces (tus apps, con boton de cerrar)
    de lo que no (piezas de fondo, solo para entender que es, no para
    tocarlo) — es la distincion que de verdad combate los jeroglificos."""

    def __init__(self, ventana):
        # ancho amplio: es una tabla de datos, no un texto para leer
        super().__init__(ventana, "grad-proc", ancho_maximo=2200)
        self.cabecera(t("proc.title"), t("proc.desc"))

        buscador = Gtk.SearchEntry(placeholder_text=t("proc.search"))
        buscador.connect("search-changed", self._filtrar)
        self.buscador = buscador
        self.contenido.append(buscador)

        # --- aplicaciones reconocidas, con el resumen de cuanto consumen
        cab_apps = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        cab_apps.append(self._encabezado_columna("verde", "proc.legend_app"))
        self.lbl_resumen_apps = Gtk.Label(xalign=0)
        self.lbl_resumen_apps.add_css_class("item-sub")
        cab_apps.append(self.lbl_resumen_apps)
        self.contenido.append(cab_apps)

        self.flow_apps = Gtk.FlowBox()
        self.flow_apps.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow_apps.set_homogeneous(True)
        self.flow_apps.set_column_spacing(14)
        self.flow_apps.set_row_spacing(10)
        self.flow_apps.set_min_children_per_line(1)
        self.flow_apps.set_max_children_per_line(5)
        self.contenido.append(self.flow_apps)

        # --- segundo plano: mismo patron, sin resumen (no invita a actuar)
        cab_bg = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        cab_bg.append(self._encabezado_columna("gris", "proc.legend_bg"))
        self.contenido.append(cab_bg)
        nota = Gtk.Label(label=t("proc.background.desc"), xalign=0, wrap=True)
        nota.add_css_class("item-sub")
        self.contenido.append(nota)

        self.flow_bg = Gtk.FlowBox()
        self.flow_bg.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow_bg.set_homogeneous(True)
        self.flow_bg.set_column_spacing(14)
        self.flow_bg.set_row_spacing(10)
        self.flow_bg.set_min_children_per_line(1)
        self.flow_bg.set_max_children_per_line(5)
        self.contenido.append(self.flow_bg)

        self._todos = []
        self.refrescar()
        GLib.timeout_add_seconds(2, self._tick)

    def _encabezado_columna(self, color, clave):
        item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        p = Gtk.Box(width_request=9, height_request=9, valign=Gtk.Align.CENTER)
        p.add_css_class("proc-dot")
        p.add_css_class(color)
        item.append(p)
        lbl = Gtk.Label(label=t(clave))
        lbl.add_css_class("titulo-seccion")
        item.append(lbl)
        return item

    def _tick(self):
        if self.get_mapped():
            self.refrescar()
        return True

    def refrescar(self):
        en_hilo(lambda: core.procesos_vivos(80), self._pintar)

    def _pintar(self, datos, _e):
        self._todos = datos or []
        self._render(self.buscador.get_text())
        return False

    def _filtrar(self, entry):
        self._render(entry.get_text())

    def _vaciar_flow(self, flow):
        hijo = flow.get_first_child()
        while hijo:
            sig = hijo.get_next_sibling()
            flow.remove(hijo)
            hijo = sig

    def _tarjeta_fila(self, datos, con_boton):
        """Envuelve la fila en una tarjeta con ancho minimo, para que el
        FlowBox sepa cuantas caben por linea segun el ancho real. Centrada
        verticalmente para que todas las tarjetas se vean simetricas, aunque
        el FlowBox homogeneo las estire a la altura de la mas alta."""
        caja = Gtk.Box(valign=Gtk.Align.CENTER)
        caja.add_css_class("card")
        caja.set_size_request(320, -1)
        fila = FilaProceso(self.ventana, datos, con_boton)
        fila.set_valign(Gtk.Align.CENTER)
        caja.append(fila)
        return caja

    def _render(self, filtro):
        self._vaciar_flow(self.flow_apps)
        self._vaciar_flow(self.flow_bg)
        filtro = (filtro or "").strip().lower()
        mostrados = [d for d in self._todos if filtro in d["nombre"].lower()]
        apps = [d for d in mostrados if d["reconocido"]]
        fondo = [d for d in mostrados if not d["reconocido"]]

        if not apps:
            self.flow_apps.append(self._tarjeta_fila(
                {"nombre": t("proc.empty"), "desc": "", "reconocido": True,
                 "mb": 0, "cpu": 0, "pids": [], "procesos": 1}, con_boton=False))
        else:
            for d in apps:
                self.flow_apps.append(self._tarjeta_fila(d, con_boton=True))

        total_mb = sum(d["mb"] for d in apps)
        total_cpu = sum(d["cpu"] for d in apps)
        self.lbl_resumen_apps.set_label(
            f"{len(apps)} · {core.fmt_size(total_mb*1024*1024)} · {total_cpu:.0f}% CPU"
            if apps else "")

        for d in fondo:
            self.flow_bg.append(self._tarjeta_fila(d, con_boton=False))


class VistaRendimiento(VistaBase):
    def __init__(self, ventana):
        super().__init__(ventana, "grad-perf")
        self.cabecera(t("perf.title"), t("perf.desc"))

        self.contenido.append(seccion(t("perf.hogs")))
        self.caja_apps = Tarjeta()
        self.contenido.append(self.caja_apps)

        self.contenido.append(seccion(t("perf.autostart"), t("perf.autostart.desc")))
        self.caja_auto = Tarjeta()
        self.contenido.append(self.caja_auto)

        self.contenido.append(seccion(t("perf.failed"), t("perf.failed.desc")))
        self.caja_fail = Tarjeta()
        self.contenido.append(self.caja_fail)

        self.refrescar()

    def _vaciar(self, caja):
        hijo = caja.get_first_child()
        while hijo:
            sig = hijo.get_next_sibling()
            caja.remove(hijo)
            hijo = sig

    def refrescar(self):
        en_hilo(core.apps_pesadas, self._pinta_apps)
        en_hilo(core.autostart_items, self._pinta_auto)
        en_hilo(core.servicios_fallidos, self._pinta_fail)

    def _pinta_apps(self, apps, _e):
        self._vaciar(self.caja_apps)
        for nombre, bytes_, pids in (apps or []):
            fila = FilaSimple(nombre, core.fmt_size(bytes_), t("perf.close"),
                              lambda n=nombre, p=pids: self._cerrar(n, p), destructivo=True)
            self.caja_apps.append(fila)
        return False

    def _cerrar(self, nombre, pids):
        dlg = Adw.AlertDialog(heading=t("dialog.close_app", name=nombre),
                              body=t("dialog.close_app.body"))
        dlg.add_response("cancel", t("action.cancel"))
        dlg.add_response("ok", t("perf.close"))
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.set_close_response("cancel")

        def resp(_d, r):
            if r == "ok":
                core.cerrar_app(pids)
                GLib.timeout_add(1200, lambda: (self.refrescar(), False)[1])
        dlg.connect("response", resp)
        dlg.present(self.ventana)

    def _pinta_auto(self, items, _e):
        self._vaciar(self.caja_auto)
        if not items:
            self.caja_auto.append(FilaSimple(t("perf.none_autostart")))
            return False
        for it in items:
            etiqueta = t("perf.disable") if it["activo"] else t("perf.enable")
            estado = "✓" if it["activo"] else "○"
            fila = FilaSimple(f"{estado}  {it['nombre']}", "", etiqueta,
                              lambda i=it: self._toggle(i))
            self.caja_auto.append(fila)
        return False

    def _toggle(self, item):
        core.toggle_autostart(item["ruta"], not item["activo"])
        self.refrescar()

    def _pinta_fail(self, servicios, _e):
        self._vaciar(self.caja_fail)
        if not servicios:
            self.caja_fail.append(FilaSimple(t("perf.none_failed")))
            return False
        for s in servicios:
            self.caja_fail.append(FilaSimple(s))
        return False


class VistaApps(VistaBase):
    def __init__(self, ventana):
        super().__init__(ventana, "grad-apps")
        self.cabecera(t("apps.title"), t("apps.desc"))

        self.contenido.append(seccion(t("apps.updates")))
        self.caja_upd = Tarjeta()
        self.contenido.append(self.caja_upd)

        self.contenido.append(seccion(t("apps.installed")))
        self.caja_apps = Tarjeta()
        self.contenido.append(self.caja_apps)
        self.refrescar()

    def _vaciar(self, caja):
        hijo = caja.get_first_child()
        while hijo:
            sig = hijo.get_next_sibling()
            caja.remove(hijo)
            hijo = sig

    def refrescar(self):
        self._vaciar(self.caja_upd)
        self.caja_upd.append(FilaSimple(t("apps.checking")))
        en_hilo(core.buscar_actualizaciones, self._pinta_upd)
        en_hilo(lambda: core.apps_instaladas(60), self._pinta_apps)

    def _pinta_upd(self, res, _e):
        self._vaciar(self.caja_upd)
        res = res or {"dnf": 0, "flatpak": 0}
        total = res["dnf"] + res["flatpak"]
        if total == 0:
            self.caja_upd.append(FilaSimple(t("apps.no_updates")))
        else:
            if res["dnf"]:
                self.caja_upd.append(FilaSimple("Fedora", f"{res['dnf']}"))
            if res["flatpak"]:
                self.caja_upd.append(FilaSimple("Flatpak", f"{res['flatpak']}"))
        return False

    def _pinta_apps(self, apps, _e):
        self._vaciar(self.caja_apps)
        for a in (apps or []):
            if a["flatpak"]:
                # solo Flatpak se puede quitar desde aquí: es autocontenido
                fila = FilaSimple(a["nombre"], "Flatpak", t("apps.uninstall"),
                                  lambda app=a: self._desinstalar(app), destructivo=True)
            else:
                fila = FilaSimple(a["nombre"], "Fedora")
            self.caja_apps.append(fila)
        return False

    def _desinstalar(self, app):
        cuerpo = (
            f"{app['nombre']}\n\n" +
            ("Se va a quitar del sistema. Te va a pedir tu contraseña."
             if get_idioma() == "es" else
             "It will be removed from the system. It will ask for your password.")
        )
        dlg = Adw.AlertDialog(heading=t("apps.uninstall"), body=cuerpo)
        dlg.add_response("cancel", t("action.cancel"))
        dlg.add_response("ok", t("apps.uninstall"))
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.set_close_response("cancel")

        def resp(_d, r):
            if r != "ok":
                return
            self.ventana.aviso(t("action.cleaning"))

            def hacer():
                return core.desinstalar_app(app)

            def listo(ok, error):
                if error or not ok:
                    self.ventana.aviso(t("action.failed"))
                else:
                    self.ventana.aviso(t("action.done"))
                    self.refrescar()
                return False

            en_hilo(hacer, listo)

        dlg.connect("response", resp)
        dlg.present(self.ventana)


class VistaEspacio(VistaBase):
    def __init__(self, ventana):
        super().__init__(ventana, "grad-space")
        self.cabecera(t("space.title"), t("space.desc"))

        self.btn = Gtk.Button(label=t("space.scan"))
        self.btn.add_css_class("pill")
        self.btn.add_css_class("cta")
        self.btn.set_halign(Gtk.Align.START)
        self.btn.connect("clicked", lambda *_: self.refrescar())
        self.contenido.append(self.btn)

        self.caja_dirs = Tarjeta()
        self.contenido.append(self.caja_dirs)

        self.contenido.append(seccion(t("space.big_files")))
        self.caja_files = Tarjeta()
        self.contenido.append(self.caja_files)

    def _vaciar(self, caja):
        hijo = caja.get_first_child()
        while hijo:
            sig = hijo.get_next_sibling()
            caja.remove(hijo)
            hijo = sig

    def refrescar(self):
        self.btn.set_sensitive(False)
        self.btn.set_label(t("space.scanning"))
        self._vaciar(self.caja_dirs)
        self._vaciar(self.caja_files)
        en_hilo(core.carpetas_grandes, self._pinta_dirs)
        en_hilo(core.archivos_grandes, self._pinta_files)

    def _pinta_dirs(self, dirs, _e):
        self._vaciar(self.caja_dirs)
        dirs = dirs or []
        mayor = dirs[0][1] if dirs else 1
        for nombre, tam, ruta in dirs:
            fila = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            fila.add_css_class("item-row")
            top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            lbl = Gtk.Label(label=nombre, xalign=0, hexpand=True)
            lbl.add_css_class("item-title")
            val = Gtk.Label(label=core.fmt_size(tam))
            val.add_css_class("item-sub")
            top.append(lbl)
            top.append(val)
            fila.append(top)
            barra = Gtk.ProgressBar()
            barra.add_css_class("space-bar")
            barra.set_fraction(min(1.0, tam / mayor))
            fila.append(barra)
            self.caja_dirs.append(fila)
        self.btn.set_sensitive(True)
        self.btn.set_label(t("action.rescan"))
        return False

    def _pinta_files(self, files, _e):
        self._vaciar(self.caja_files)
        for nombre, tam, ruta in (files or []):
            carpeta = os.path.dirname(ruta).replace(core.HOME, "~")
            fila = FilaSimple(nombre, f"{core.fmt_size(tam)} · {carpeta}",
                              t("space.open"), lambda r=ruta: self._abrir(r))
            self.caja_files.append(fila)
        return False

    def _abrir(self, ruta):
        try:
            Gio.AppInfo.launch_default_for_uri(
                GLib.filename_to_uri(os.path.dirname(ruta), None), None)
        except Exception:
            pass


class VistaSalud(VistaBase):
    def __init__(self, ventana):
        super().__init__(ventana, "grad-health")
        self.cabecera(t("health.title"), t("health.desc"))
        self.tarjetas = {}
        grid = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE)
        grid.set_max_children_per_line(2)
        grid.set_column_spacing(14)
        grid.set_row_spacing(14)
        grid.set_homogeneous(True)
        for clave, etiqueta in (("mem", "health.memory"), ("cpu", "health.cpu"),
                                ("disk", "health.disk"), ("bat", "health.battery")):
            tarjeta = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            tarjeta.add_css_class("card")
            titulo = Gtk.Label(label=t(etiqueta), xalign=0)
            titulo.add_css_class("task-title")
            valor = Gtk.Label(label="—", xalign=0)
            valor.add_css_class("metric-value")
            barra = Gtk.ProgressBar()
            barra.add_css_class("metric-bar")
            frase = Gtk.Label(label="", xalign=0, wrap=True)
            frase.add_css_class("task-desc")
            for w in (titulo, valor, barra, frase):
                tarjeta.append(w)
            self.tarjetas[clave] = (valor, barra, frase, tarjeta)
            grid.append(tarjeta)
        self.contenido.append(grid)

        self.extra = Gtk.Label(label="", xalign=0, wrap=True)
        self.extra.add_css_class("section-sub")
        self.contenido.append(self.extra)

        # --- estado del disco (SMART + errores del sistema de archivos)
        self.contenido.append(seccion(t("disk.health")))
        self.caja_disco = Tarjeta()
        self.contenido.append(self.caja_disco)
        self._disco_pedido = False

        # --- registro de problemas, traducido
        self.contenido.append(seccion(t("log.title"), t("log.desc")))
        self.caja_log = Tarjeta()
        self.contenido.append(self.caja_log)
        self._log_pedido = False

        self.refrescar()
        GLib.timeout_add_seconds(3, self._tick)

    def _vaciar(self, caja):
        hijo = caja.get_first_child()
        while hijo:
            sig = hijo.get_next_sibling()
            caja.remove(hijo)
            hijo = sig

    def cargar_disco(self):
        """Se pide una sola vez: SMART tarda y no cambia cada segundo."""
        if self._disco_pedido:
            return
        self._disco_pedido = True
        self._vaciar(self.caja_disco)
        self.caja_disco.append(FilaSimple(t("disk.checking")))
        en_hilo(core.errores_filesystem, self._pinta_fs)
        en_hilo(core.smart, self._pinta_smart)

    def _pinta_fs(self, fs, _e):
        self._fs = fs
        return False

    def _pinta_smart(self, s, _e):
        self._vaciar(self.caja_disco)
        fs = getattr(self, "_fs", None)

        if s:
            if s.get("aprobado") is True:
                titulo = t("disk.good")
            elif s.get("aprobado") is False:
                titulo = t("disk.bad")
            else:
                titulo = s.get("modelo") or t("disk.health")
            self.caja_disco.append(FilaSimple(titulo, s.get("modelo") or ""))

            if s.get("desgaste") is not None:
                self.caja_disco.append(FilaSimple(
                    t("disk.wear"), t("disk.wear.desc", pct=s["desgaste"])))
            if s.get("repuesto") is not None:
                self.caja_disco.append(FilaSimple(t("disk.spare"), f"{s['repuesto']}%"))
            if s.get("horas") is not None:
                self.caja_disco.append(FilaSimple(t("disk.hours"), f"{s['horas']:,}".replace(",", ".")))
        else:
            self.caja_disco.append(FilaSimple(t("disk.unavailable")))

        if fs is not None:
            n = fs.get("total", 0)
            detalle = t("disk.no_errors") if n == 0 else t("disk.some_errors", n=n)
            self.caja_disco.append(FilaSimple(t("disk.errors"), detalle))
        return False

    def cargar_log(self):
        """Tambien se pide una sola vez: revisa varios dias de historial,
        no algo que cambie segundo a segundo."""
        if self._log_pedido:
            return
        self._log_pedido = True
        self._vaciar(self.caja_log)
        self.caja_log.append(FilaSimple(t("disk.checking")))
        en_hilo(lambda: core.registro_problemas(3), self._pinta_log)

    def _pinta_log(self, items, _e):
        self._vaciar(self.caja_log)
        items = items or []
        if not items:
            self.caja_log.append(FilaSimple(t("log.empty")))
            return False
        idioma = get_idioma()
        for it in items:
            tipo = it["tipo"]
            if tipo == "crash":
                clave = "log.crash" if it["veces"] == 1 else "log.crash_pl"
                titulo = t(clave, app=it["programa"], veces=it["veces"])
                self.caja_log.append(FilaSimple(titulo, t("log.crash.desc")))
            elif tipo == "service":
                self.caja_log.append(FilaSimple(
                    t("log.service", s=it["programa"]), t("log.service.desc")))
            elif tipo == "oom":
                clave = "log.oom" if it["veces"] == 1 else "log.oom_pl"
                self.caja_log.append(FilaSimple(t(clave, veces=it["veces"]), t("log.oom.desc")))
            elif tipo == "disk":
                clave = "log.disk" if it["veces"] == 1 else "log.disk_pl"
                self.caja_log.append(FilaSimple(t(clave, veces=it["veces"]), t("log.disk.desc")))
        return False

    def _tick(self):
        if self.get_mapped():
            self.refrescar()
            self.cargar_disco()
            self.cargar_log()
        return True

    def refrescar(self):
        en_hilo(core.salud, self._pinta)

    def _pinta(self, d, _e):
        if not d:
            return False
        idioma = get_idioma()

        val, barra, frase, _c = self.tarjetas["mem"]
        val.set_label(f"{round(d['mem_pct'])}%")
        barra.set_fraction(d["mem_pct"] / 100)
        txt = (t("mem.plenty") if d["mem_pct"] < 50
               else t("mem.filling") if d["mem_pct"] < 80 else t("mem.full"))
        if d["swap_used"] > 512 * 1024 ** 2:
            txt += t("mem.swap")
        frase.set_label(txt)
        self._color(barra, d["mem_pct"], 50, 80)

        val, barra, frase, _c = self.tarjetas["cpu"]
        val.set_label(f"{round(d['cpu_pct'])}%")
        barra.set_fraction(d["cpu_pct"] / 100)
        frase.set_label(t("cpu.idle") if d["cpu_pct"] < 40
                        else t("cpu.busy") if d["cpu_pct"] < 75 else t("cpu.hard"))
        self._color(barra, d["cpu_pct"], 40, 75)

        val, barra, frase, _c = self.tarjetas["disk"]
        val.set_label(f"{round(d['disk_pct'])}%")
        barra.set_fraction(d["disk_pct"] / 100)
        libre = core.fmt_size(d["disk_free"])
        frase.set_label(t("disk.plenty", free=libre) if d["disk_pct"] < 70
                        else t("disk.shrinking", free=libre) if d["disk_pct"] < 90
                        else t("disk.full", free=libre))
        self._color(barra, d["disk_pct"], 70, 90)

        val, barra, frase, tarjeta = self.tarjetas["bat"]
        if d["bateria"]:
            pct = d["bateria"]["pct"]
            val.set_label(f"{pct}%")
            barra.set_fraction(pct / 100)
            txt = (t("bat.charging", pct=pct) if d["bateria"]["cargando"]
                   else t("bat.discharging", pct=pct))
            if d["bat_salud"]:
                txt += " " + t("bat.health", pct=d["bat_salud"])
            frase.set_label(txt)
            self._color(barra, 100 - pct, 40, 80)
            tarjeta.set_visible(True)
        else:
            tarjeta.set_visible(False)

        partes = [f"{t('health.uptime')}: {core.fmt_uptime(d['uptime'], idioma)}"]
        if d["temp"]:
            partes.append(f"{t('health.temp')}: {d['temp']}°C")
        self.extra.set_label(" · ".join(partes))
        return False

    @staticmethod
    def _color(barra, pct, bueno, regular):
        for c in ("verde", "amarillo", "rojo"):
            barra.remove_css_class(c)
        barra.add_css_class("verde" if pct < bueno else "amarillo" if pct < regular else "rojo")


# ---------------------------------------------------------------- ventana

class Ventana(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="SOul")
        self.set_default_size(1180, 820)
        self.maximize()
        self.vistas = {}

        self.toasts = Adw.ToastOverlay()
        split = Adw.NavigationSplitView()
        split.set_min_sidebar_width(248)
        split.set_max_sidebar_width(268)

        # --- barra lateral
        lateral = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        lateral.add_css_class("sidebar-bg")

        marca = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        marca.add_css_class("brand")
        fila_logo = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=11)
        marca_img = Gtk.Image.new_from_paintable(icons.logo_svg(72))
        marca_img.set_pixel_size(34)
        marca_img.set_valign(Gtk.Align.CENTER)
        fila_logo.append(marca_img)
        caja_txt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        caja_txt.set_valign(Gtk.Align.CENTER)
        logo = Gtk.Label(label="SOul", xalign=0)
        logo.add_css_class("brand-name")
        autor = Gtk.Label(label="by Vezzu Studio", xalign=0)
        autor.add_css_class("brand-author")
        caja_txt.append(logo)
        caja_txt.append(autor)
        fila_logo.append(caja_txt)
        marca.append(fila_logo)
        lema = Gtk.Label(label=t("app.tagline"), xalign=0, wrap=True)
        lema.add_css_class("brand-tagline")
        marca.append(lema)
        lateral.append(marca)

        self.lista = Gtk.ListBox()
        self.lista.add_css_class("nav-list")
        self.lista.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.lista.connect("row-selected", self.on_nav)
        for clave, etiqueta, icono, _grad in MODULOS:
            fila = Gtk.ListBoxRow()
            fila.clave = clave
            caja = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            caja.add_css_class("nav-item")
            ic = icons.pintar(icono, 19)
            ic.add_css_class("nav-icon")
            lb = Gtk.Label(label=t(etiqueta), xalign=0)
            lb.add_css_class("nav-label")
            caja.append(ic)
            caja.append(lb)
            fila.set_child(caja)
            self.lista.append(fila)
        lateral.append(self.lista)

        lateral.append(Gtk.Box(vexpand=True))

        pie = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        pie.add_css_class("sidebar-foot")

        kofi = Gtk.Button()
        kofi.add_css_class("kofi-btn")
        kcaja = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        kcaja.set_halign(Gtk.Align.CENTER)
        kcaja.append(icons.pintar("kofi", 17, "#E4DBFF"))
        kcaja.append(Gtk.Label(label="Ko-fi"))
        kofi.set_child(kcaja)
        kofi.set_tooltip_text(t("donate.instructions"))
        kofi.connect("clicked", lambda *_: self._ir_a_kofi())
        pie.append(kofi)

        idioma_caja = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        idioma_caja.set_halign(Gtk.Align.CENTER)
        self.btn_es = Gtk.ToggleButton(label="ES")
        self.btn_en = Gtk.ToggleButton(label="EN")
        for b in (self.btn_es, self.btn_en):
            b.add_css_class("lang-btn")
        self.btn_es.set_active(get_idioma() == "es")
        self.btn_en.set_active(get_idioma() == "en")
        self.btn_es.connect("toggled", lambda b: self._idioma("es", b))
        self.btn_en.connect("toggled", lambda b: self._idioma("en", b))
        idioma_caja.append(self.btn_es)
        idioma_caja.append(self.btn_en)
        pie.append(idioma_caja)
        lateral.append(pie)

        # barra de título propia de la barra lateral (sin botones)
        barra_lat = Adw.ToolbarView()
        cab_lat = Adw.HeaderBar()
        cab_lat.add_css_class("flat-header")
        cab_lat.set_show_end_title_buttons(False)
        cab_lat.set_title_widget(Gtk.Label(label=""))
        barra_lat.add_top_bar(cab_lat)
        barra_lat.set_content(lateral)
        pag_lateral = Adw.NavigationPage(child=barra_lat, title="SOul")
        split.set_sidebar(pag_lateral)

        # --- contenido
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(220)
        self.toasts.set_child(self.stack)

        # barra de título del panel: aquí van minimizar / maximizar / cerrar
        barra_cont = Adw.ToolbarView()
        self.cabecera = Adw.HeaderBar()
        self.cabecera.add_css_class("flat-header")
        self.cabecera.set_show_end_title_buttons(True)
        self.titulo_win = Adw.WindowTitle(title="SOul", subtitle="by Vezzu Studio")
        self.cabecera.set_title_widget(self.titulo_win)
        barra_cont.add_top_bar(self.cabecera)
        barra_cont.set_content(self.toasts)
        pag_cont = Adw.NavigationPage(child=barra_cont, title="SOul")
        split.set_content(pag_cont)

        self.set_content(split)
        self._css()
        self._construir_vistas()

        # abrir siempre en Escaneo inteligente
        self.stack.set_visible_child_name("smart")
        GLib.idle_add(self._seleccionar_inicio)

        # icono en la bandeja del sistema (si el escritorio la ofrece)
        self.bandeja = Bandeja(self._mostrar_desde_bandeja)
        self._salir_de_verdad = False
        self.connect("close-request", self._al_cerrar)

        # cuenta esta apertura. En la primera de todas, nunca se pide
        # donacion: la persona merece usar SOul sin interrupciones antes
        # de que le pidamos algo. Desde la segunda apertura, si.
        self._es_primer_uso = core.contar_apertura() <= 1

        # el permiso si aparece pronto (incluso en el primer uso): hace
        # falta para que la limpieza funcione. La donacion espera mas,
        # y solo desde la segunda vez que se abre la app.
        GLib.timeout_add_seconds(1, self._arranque_permiso)
        if not self._es_primer_uso:
            GLib.timeout_add_seconds(25, self._arranque_donacion)
        # tercer punto de disparo: revisa tambien mientras la app se
        # queda abierta mucho rato, no solo al abrirla o al restaurarla
        GLib.timeout_add_seconds(40 * 60, self._revision_periodica_donacion)

    def _arranque_permiso(self):
        if not core.polkit_listo():
            self._onboarding()
        return False

    def _arranque_donacion(self):
        """Primera aparicion del aviso de donacion, 25s despues de abrir
        la app — no al segundo uno, para no interrumpir antes de que la
        persona alcance a probar algo. Solo desde la segunda apertura."""
        if not self._es_primer_uso and core.polkit_listo() and not core.ya_dono():
            self._pedir_donacion()
        return False

    def _pedir_donacion(self):
        """Aviso de donacion con codigo propio de esta instalacion.

        Solo deja de aparecer cuando el servidor de Vezzu Studio confirma
        que ESE codigo exacto aparecio en un pago real de Ko-fi (ver
        server/worker.js). No hay boton de 'confiar en tu palabra': eso
        era lo que cualquiera saltaba sin pagar. Se puede cerrar por esta
        vez, pero vuelve a aparecer la proxima. No bloquea nada."""
        codigo = core.codigo_donacion()

        dlg = Adw.AlertDialog()
        dlg.add_css_class("donate-dialog")

        cabecera = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        cabecera.set_halign(Gtk.Align.CENTER)
        cabecera.add_css_class("donate-head")

        halo = Gtk.Box(width_request=68, height_request=68)
        halo.add_css_class("donate-halo")
        logo = Gtk.Image.new_from_paintable(icons.logo_svg(84))
        logo.set_pixel_size(44)
        logo.set_halign(Gtk.Align.CENTER)
        logo.set_valign(Gtk.Align.CENTER)
        halo.set_halign(Gtk.Align.CENTER)
        overlay = Gtk.Overlay()
        overlay.set_child(halo)
        overlay.add_overlay(logo)
        cabecera.append(overlay)

        titulo = Gtk.Label(label=t("donate.title"), justify=Gtk.Justification.CENTER, wrap=True)
        titulo.add_css_class("donate-title")
        cabecera.append(titulo)

        cuerpo = Gtk.Label(label=t("donate.body"), justify=Gtk.Justification.CENTER, wrap=True)
        cuerpo.add_css_class("donate-body")
        cuerpo.set_max_width_chars(48)
        cabecera.append(cuerpo)

        # el codigo: se muestra, se puede copiar, nunca se puede escribir
        # uno distinto a mano — asi un codigo ajeno no le sirve a nadie
        caja_codigo = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        caja_codigo.add_css_class("donate-code-box")
        lbl_codigo = Gtk.Label(label=codigo)
        lbl_codigo.add_css_class("donate-code")
        lbl_codigo.set_selectable(True)
        caja_codigo.append(lbl_codigo)
        btn_copiar = Gtk.Button(icon_name="edit-copy-symbolic")
        btn_copiar.add_css_class("flat")
        btn_copiar.set_tooltip_text(t("donate.copy"))
        btn_copiar.connect("clicked", lambda *_: self._copiar_codigo(codigo))
        caja_codigo.append(btn_copiar)
        cabecera.append(caja_codigo)

        instrucciones = Gtk.Label(label=t("donate.instructions"), justify=Gtk.Justification.CENTER, wrap=True)
        instrucciones.add_css_class("donate-instructions")
        instrucciones.set_max_width_chars(50)
        cabecera.append(instrucciones)

        marca = Gtk.Label(label="SOul · Vezzu Studio")
        marca.add_css_class("donate-brand")
        cabecera.append(marca)

        dlg.set_extra_child(cabecera)
        dlg.add_response("later", t("donate.later"))
        dlg.add_response("check", t("donate.check"))
        dlg.add_response("kofi", t("donate.kofi"))
        dlg.set_response_appearance("kofi", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("kofi")
        dlg.set_close_response("later")

        def resp(_d, r):
            if r == "kofi":
                self._ir_a_kofi()
            elif r == "check":
                self.aviso(t("donate.checking"))

                def listo(ok, _error):
                    self.aviso(t("donate.confirmed") if ok else t("donate.not_found"))
                    return False

                en_hilo(core.verificar_donacion, listo)

        dlg.connect("response", resp)
        dlg.present(self)

    def _copiar_codigo(self, codigo, avisar=True):
        clip = self.get_clipboard()
        clip.set(codigo)
        if avisar:
            self.aviso(t("donate.copied"))

    def _ir_a_kofi(self):
        """Un solo camino a Ko-fi, se llame desde donde se llame: el
        boton fijo de la barra lateral o el del modal. Copia el codigo
        SIEMPRE, para que una donacion hecha desde cualquiera de los dos
        pueda conectarse con esta instalacion.

        Ko-fi no deja pre-llenar su campo de mensaje por URL (se
        investigo: ni documentado ni en su codigo). Como eso no se puede
        arreglar del lado de SOul, se compensa con un dialogo — no un
        aviso que desaparece solo — que muestra exactamente que forma
        tiene ese campo en Ko-fi, para que no haya duda de donde va.

        Primero se lee esto, DESPUES se abre Ko-fi (al responder el
        dialogo) — no al reves, para que la pagina no compita por la
        atencion mientras la persona todavia esta leyendo donde pegar
        el codigo."""
        codigo = core.codigo_donacion()
        self._copiar_codigo(codigo, avisar=False)

        dlg = Adw.AlertDialog()
        dlg.add_css_class("donate-dialog")
        caja = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        caja.set_halign(Gtk.Align.CENTER)
        caja.add_css_class("donate-head")

        titulo = Gtk.Label(label=t("donate.paste_title"), justify=Gtk.Justification.CENTER, wrap=True)
        titulo.add_css_class("donate-title")
        caja.append(titulo)

        cuerpo = Gtk.Label(label=t("donate.paste_body"), justify=Gtk.Justification.CENTER, wrap=True)
        cuerpo.add_css_class("donate-body")
        cuerpo.set_max_width_chars(48)
        caja.append(cuerpo)

        # una maqueta del campo real de Ko-fi, para reconocerlo a simple
        # vista en vez de andar buscando por toda la pagina
        maqueta = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        maqueta.add_css_class("donate-mockup")
        etiqueta_campo = Gtk.Label(label=t("donate.mockup_label"), xalign=0)
        etiqueta_campo.add_css_class("donate-mockup-label")
        caja_texto = Gtk.Box()
        caja_texto.add_css_class("donate-mockup-field")
        caja_texto.set_size_request(280, -1)
        valor = Gtk.Label(label=codigo, xalign=0)
        valor.add_css_class("donate-code")
        caja_texto.append(valor)
        maqueta.append(etiqueta_campo)
        maqueta.append(caja_texto)
        caja.append(maqueta)

        # la consecuencia de no poner el codigo, bien clara, no
        # escondida en un texto largo que nadie termina de leer
        aviso = Gtk.Label(label=t("donate.warning"), justify=Gtk.Justification.CENTER, wrap=True)
        aviso.add_css_class("donate-warning")
        aviso.set_max_width_chars(44)
        caja.append(aviso)

        dlg.set_extra_child(caja)
        dlg.add_response("ok", t("donate.understood"))
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("ok")
        dlg.set_close_response("ok")

        def abrir_kofi(*_args):
            try:
                Gio.AppInfo.launch_default_for_uri(KOFI_URL, None)
            except Exception:
                subprocess.Popen(["xdg-open", KOFI_URL])

        dlg.connect("response", abrir_kofi)
        dlg.present(self)

    def _onboarding(self):
        dlg = Adw.AlertDialog(heading=t("onboard.title"), body=t("onboard.body"))
        dlg.add_response("later", t("onboard.later"))
        dlg.add_response("yes", t("onboard.yes"))
        dlg.set_response_appearance("yes", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("yes")
        dlg.set_close_response("later")

        def resp(_d, r):
            if r != "yes":
                return
            origen = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "packaging", "studio.vezzu.soul.policy")

            def hacer():
                return core.instalar_polkit(origen)

            def listo(ok, error):
                self.aviso(t("onboard.done") if (ok and not error)
                           else t("onboard.failed"))
                return False

            en_hilo(hacer, listo)

        dlg.connect("response", resp)
        dlg.present(self)
        return False

    def _al_cerrar(self, *_):
        """Al pulsar la X preguntamos: ¿a la bandeja o cerrar del todo?"""
        if self._salir_de_verdad:
            return False  # dejar que se cierre

        dlg = Adw.AlertDialog(
            heading=t("close.title"),
            body=t("close.body"),
        )
        dlg.add_response("cancel", t("action.cancel"))
        dlg.add_response("tray", t("close.tray"))
        dlg.add_response("quit", t("close.quit"))
        dlg.set_response_appearance("quit", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_response_appearance("tray", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("tray")
        dlg.set_close_response("cancel")

        def resp(_d, r):
            if r == "tray":
                self.set_visible(False)
            elif r == "quit":
                self._salir_de_verdad = True
                self.get_application().quit()

        dlg.connect("response", resp)
        dlg.present(self)
        return True  # frenamos el cierre hasta que responda

    def _seleccionar_inicio(self):
        fila = self.lista.get_row_at_index(0)
        if fila is not None:
            self.lista.select_row(fila)
        self.stack.set_visible_child_name("smart")
        return False

    def _mostrar_desde_bandeja(self):
        estaba_oculta = not self.get_visible()
        if self.get_visible() and not self.is_active():
            self.present()
        elif self.get_visible():
            self.set_visible(False)
        else:
            self.set_visible(True)
            self.present()
        # segundo punto de disparo: volver de la bandeja tambien revisa
        # el estado de donacion, no solo el arranque inicial — salvo en
        # el primer uso, donde nunca se pide
        if (estaba_oculta and not self._es_primer_uso
                and core.polkit_listo() and not core.ya_dono()):
            GLib.timeout_add_seconds(1, self._pedir_donacion_una_vez)
        return False

    def _pedir_donacion_una_vez(self):
        if not self._es_primer_uso and not core.ya_dono():
            self._pedir_donacion()
        return False

    def _revision_periodica_donacion(self):
        if (not self._es_primer_uso and core.polkit_listo()
                and not core.ya_dono() and self.get_visible()):
            self._pedir_donacion()
        return True  # se repite cada 40 minutos mientras la app siga abierta

    # --- helpers
    def aviso(self, texto):
        self.toasts.add_toast(Adw.Toast(title=texto, timeout=3))

    def _abrir_url(self, url):
        try:
            Gio.AppInfo.launch_default_for_uri(url, None)
        except Exception:
            subprocess.Popen(["xdg-open", url])

    def _idioma(self, cual, boton):
        if not boton.get_active():
            return
        if get_idioma() == cual:
            return
        set_idioma(cual)
        self.btn_es.set_active(cual == "es")
        self.btn_en.set_active(cual == "en")
        self.aviso("Idioma cambiado" if cual == "es" else "Language changed")
        self._reconstruir()

    def _reconstruir(self):
        actual = self.stack.get_visible_child_name()
        hijo = self.stack.get_first_child()
        while hijo:
            sig = hijo.get_next_sibling()
            self.stack.remove(hijo)
            hijo = sig
        self.vistas.clear()
        self._construir_vistas()
        # renombrar la navegación
        i = 0
        fila = self.lista.get_row_at_index(i)
        while fila is not None:
            caja = fila.get_child()
            etiqueta = caja.get_last_child()
            etiqueta.set_label(t(MODULOS[i][1]))
            i += 1
            fila = self.lista.get_row_at_index(i)
        if actual:
            self.stack.set_visible_child_name(actual)

    def refrescar_procesos(self):
        if "processes" in self.vistas:
            self.vistas["processes"].refrescar()

    def _construir_vistas(self):
        self.vistas["smart"] = VistaSmart(self)
        self.vistas["processes"] = VistaProcesos(self)
        self.vistas["cleanup"] = VistaLista(
            self, "grad-cleanup", t("cleanup.title"), t("cleanup.desc"), core.TAREAS_LIMPIEZA)
        self.vistas["performance"] = VistaRendimiento(self)
        self.vistas["apps"] = VistaApps(self)
        self.vistas["privacy"] = VistaLista(
            self, "grad-privacy", t("privacy.title"), t("privacy.desc"), core.TAREAS_PRIVACIDAD)
        self.vistas["space"] = VistaEspacio(self)
        self.vistas["health"] = VistaSalud(self)
        for clave, vista in self.vistas.items():
            self.stack.add_named(vista, clave)

    def on_nav(self, _lista, fila):
        if fila is None:
            return
        self.stack.set_visible_child_name(fila.clave)

    def _css(self):
        css = """
        window, .sidebar-bg { background-color: #070A0F; }

        /* ---------- barra lateral ---------- */
        .sidebar-bg {
            background: linear-gradient(178deg,
                        rgba(23,30,46,0.96) 0%,
                        rgba(12,17,27,0.98) 48%,
                        rgba(7,10,15,1) 100%);
            border-right: 1px solid rgba(255,255,255,0.07);
            box-shadow: inset -1px 0 0 rgba(255,255,255,0.03);
        }
        .brand { padding: 26px 22px 18px 22px; }
        .brand-name {
            font-size: 30px; font-weight: 800; color: #ffffff;
            letter-spacing: -0.5px;
        }
        .brand-author {
            font-size: 11px; font-weight: 600; color: #7C8CF8;
            letter-spacing: 0.08em; text-transform: uppercase;
        }
        .brand-tagline {
            font-size: 11px; color: #63758A; margin-top: 8px;
        }
        .nav-list { background: transparent; padding: 4px 12px; }
        .nav-list row {
            border-radius: 12px; margin: 2px 0; background: transparent;
            transition: background 160ms ease;
        }
        .nav-list row:hover { background: rgba(255,255,255,0.055); }
        .nav-list row:selected {
            background: linear-gradient(100deg,
                        rgba(138,124,255,0.30) 0%,
                        rgba(168,139,255,0.13) 65%,
                        rgba(168,139,255,0.04) 100%);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.10),
                        0 4px 16px rgba(124,110,255,0.16);
        }
        .nav-item { padding: 11px 12px; }
        .nav-icon { font-size: 15px; min-width: 20px; }
        .nav-label { font-size: 14px; font-weight: 500; color: #C9D6E4; }
        .nav-list row:selected .nav-label { color: #ffffff; font-weight: 600; }

        .sidebar-foot { padding: 14px 16px 20px 16px; }
        /* Ko-fi en vidrio, con el violeta de la marca */
        .kofi-btn {
            background: linear-gradient(165deg,
                        rgba(168,139,255,0.22), rgba(201,123,238,0.10));
            color: #E4DBFF; font-weight: 700; font-size: 13px;
            border-radius: 13px; padding: 11px 14px;
            border: 1px solid rgba(168,139,255,0.40);
            box-shadow: 0 8px 24px rgba(138,124,255,0.18),
                        inset 0 1px 0 rgba(255,255,255,0.16);
        }
        .kofi-btn:hover {
            background: linear-gradient(165deg,
                        rgba(168,139,255,0.32), rgba(201,123,238,0.16));
            color: #F3EEFF;
        }
        .lang-btn {
            background: rgba(255,255,255,0.05); color: #8FA3B8;
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 9px; font-size: 11px; font-weight: 700;
            padding: 5px 14px; min-height: 0;
        }
        .lang-btn:checked {
            background: rgba(124,140,248,0.22); color: #ffffff;
            border-color: rgba(124,140,248,0.45);
        }

        /* ---------- degradados por módulo ---------- */
        /* atmósfera propia por módulo: dos focos de luz superpuestos */
        .grad-smart {
            background:
              radial-gradient(760px 520px at 78% 82%, rgba(201,123,238,0.16) 0%, rgba(0,0,0,0) 70%),
              radial-gradient(1180px 760px at 50% -6%, #3B2A78 0%, #191636 34%, #0A0D14 72%);
        }
        .grad-proc {
            background:
              radial-gradient(700px 480px at 82% 78%, rgba(91,168,245,0.13) 0%, rgba(0,0,0,0) 70%),
              radial-gradient(1180px 760px at 14% -10%, #1B4E7C 0%, #10273F 36%, #0A0D14 72%);
        }
        .grad-cleanup {
            background:
              radial-gradient(700px 480px at 82% 78%, rgba(63,217,176,0.13) 0%, rgba(0,0,0,0) 70%),
              radial-gradient(1180px 760px at 14% -10%, #14615A 0%, #0D3038 36%, #0A0D14 72%);
        }
        .grad-perf {
            background:
              radial-gradient(700px 480px at 82% 78%, rgba(255,178,89,0.12) 0%, rgba(0,0,0,0) 70%),
              radial-gradient(1180px 760px at 14% -10%, #6E4417 0%, #35220F 36%, #0A0D14 72%);
        }
        .grad-apps {
            background:
              radial-gradient(700px 480px at 82% 78%, rgba(91,168,245,0.13) 0%, rgba(0,0,0,0) 70%),
              radial-gradient(1180px 760px at 14% -10%, #17497C 0%, #10253F 36%, #0A0D14 72%);
        }
        .grad-privacy {
            background:
              radial-gradient(700px 480px at 82% 78%, rgba(242,123,200,0.14) 0%, rgba(0,0,0,0) 70%),
              radial-gradient(1180px 760px at 14% -10%, #66246E 0%, #331436 36%, #0A0D14 72%);
        }
        .grad-space {
            background:
              radial-gradient(700px 480px at 82% 78%, rgba(128,147,247,0.14) 0%, rgba(0,0,0,0) 70%),
              radial-gradient(1180px 760px at 14% -10%, #283A86 0%, #161C3E 36%, #0A0D14 72%);
        }
        .grad-health {
            background:
              radial-gradient(700px 480px at 82% 78%, rgba(79,217,138,0.13) 0%, rgba(0,0,0,0) 70%),
              radial-gradient(1180px 760px at 14% -10%, #1A5E3F 0%, #102D22 36%, #0A0D14 72%);
        }
        scrolledwindow, viewport { background: transparent; }

        /* ---------- páginas ---------- */
        .page-head { margin-bottom: 4px; }
        .page-title {
            font-size: 30px; font-weight: 800; color: #ffffff; letter-spacing: -0.4px;
        }
        .page-desc { font-size: 14px; color: #92A4B8; }
        .section-title {
            font-size: 12px; font-weight: 700; letter-spacing: 0.09em;
            text-transform: uppercase; color: #8794A8; margin-top: 10px;
        }
        .section-sub { font-size: 13px; color: #7E8EA1; }
        .safe-note { font-size: 12px; color: #66768A; margin-top: 4px; }

        /* --- vidrio: capa translúcida + brillo arriba + sombra profunda --- */
        .card {
            background: linear-gradient(165deg,
                        rgba(255,255,255,0.085) 0%,
                        rgba(255,255,255,0.040) 42%,
                        rgba(255,255,255,0.022) 100%);
            border: 1px solid rgba(255,255,255,0.085);
            border-radius: 20px; padding: 7px;
            box-shadow: 0 14px 40px rgba(0,0,0,0.42),
                        inset 0 1px 0 rgba(255,255,255,0.13);
        }

        /* ---------- filas de tarea ---------- */
        .task-row { padding: 15px 16px; border-radius: 14px; }
        .task-row:hover { background: rgba(255,255,255,0.03); }
        .task-icon { font-size: 19px; min-width: 26px; }
        .task-title { font-size: 14.5px; font-weight: 600; color: #EAF1F8; }
        .task-desc { font-size: 12.5px; color: #7E8EA1; }
        .task-size { font-size: 13.5px; font-weight: 700; color: #7C8CF8; }
        .task-check { min-width: 20px; min-height: 20px; }

        .item-row { padding: 13px 16px; border-radius: 12px; }
        .item-row:hover { background: rgba(255,255,255,0.03); }
        .item-title { font-size: 14px; color: #E7EFF7; }
        .item-sub { font-size: 12px; color: #74849A; }

        /* procesos en vivo */
        .proc-dot { border-radius: 999px; }
        .proc-dot.verde { background-color: #4FD98A; box-shadow: 0 0 8px rgba(79,217,138,.5); }
        .proc-dot.gris  { background-color: #55637A; }
        .proc-metric {
            font-family: monospace; font-size: 13px; font-weight: 600;
            color: #9FB0C4;
        }

        .total-label { font-size: 15px; font-weight: 700; color: #ffffff; }

        /* ---------- botones ---------- */
        .cta {
            background: linear-gradient(120deg, #8A7CFF 0%, #A88BFF 48%, #C97BEE 100%);
            color: #ffffff; font-weight: 700; font-size: 14px;
            padding: 12px 28px; border-radius: 999px; border: none;
            box-shadow: 0 10px 30px rgba(138,124,255,0.40),
                        inset 0 1px 0 rgba(255,255,255,0.28);
        }
        .cta:hover { filter: brightness(1.10); }
        .cta:active { filter: brightness(0.94); }
        .cta:disabled {
            background: rgba(255,255,255,0.06); color: #5A6A7E;
            box-shadow: none;
        }
        .soul-btn {
            background: linear-gradient(165deg,
                        rgba(255,255,255,0.14), rgba(255,255,255,0.06));
            color: #DCE7F3;
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 999px; padding: 8px 19px; font-size: 12.5px;
            font-weight: 600; min-height: 0;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.12);
        }
        .soul-btn:hover { background: rgba(255,255,255,0.18); }
        button.destructive-action {
            border-radius: 999px; padding: 7px 18px; font-size: 12.5px;
            font-weight: 600; min-height: 0;
        }

        /* ---------- escaneo inteligente ---------- */
        .hero-title {
            font-size: 42px; font-weight: 800; color: #ffffff; letter-spacing: -1px;
        }
        .hero-desc { font-size: 15px; color: #96A6BC; }
        .hero-state { font-size: 15px; font-weight: 600; color: #B9C6D8; margin-top: 6px; }
        .tile {
            background: linear-gradient(165deg,
                        rgba(255,255,255,0.10) 0%,
                        rgba(255,255,255,0.045) 100%);
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 18px; padding: 18px 20px; min-width: 152px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.34),
                        inset 0 1px 0 rgba(255,255,255,0.14);
        }
        .tile-icon { font-size: 21px; }
        .tile-name { font-size: 12.5px; color: #B7C6D8; }
        .tile-size { font-size: 15px; font-weight: 800; color: #ffffff; }

        /* ---------- métricas ---------- */
        .metric-value { font-size: 30px; font-weight: 800; color: #ffffff; }
        .metric-bar, .space-bar { min-height: 7px; }
        .metric-bar trough, .space-bar trough {
            min-height: 7px; border-radius: 6px; background: rgba(255,255,255,0.07);
        }
        .metric-bar progress, .space-bar progress {
            min-height: 7px; border-radius: 6px;
            background: linear-gradient(90deg, #7C8CF8, #A46BF5);
        }
        .metric-bar.verde progress    { background: linear-gradient(90deg, #35D39A, #2BB3C0); }
        .metric-bar.amarillo progress { background: linear-gradient(90deg, #F7C948, #F79448); }
        .metric-bar.rojo progress     { background: linear-gradient(90deg, #FF6B6B, #FF4D8D); }

        /* barra de título integrada con el fondo del módulo */
        headerbar, .flat-header {
            background: transparent; box-shadow: none;
            border: none; min-height: 42px;
        }
        .flat-header windowcontrols button {
            background: rgba(255,255,255,0.07);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 999px; margin: 0 2px; min-width: 26px; min-height: 26px;
        }
        .flat-header windowcontrols button:hover { background: rgba(255,255,255,0.16); }
        .flat-header windowcontrols button.close:hover {
            background: rgba(255,90,90,0.75);
        }

        /* ---------- modal de donacion ---------- */
        .donate-dialog {
            background: linear-gradient(165deg, #201A3C 0%, #140F28 55%, #0B0714 100%);
            border: 1px solid rgba(168,139,255,0.22);
            box-shadow: 0 30px 80px rgba(0,0,0,0.55),
                        inset 0 1px 0 rgba(255,255,255,0.10);
        }
        .donate-head { padding: 20px 30px 4px 30px; }
        .donate-halo {
            border-radius: 999px;
            background: radial-gradient(circle, rgba(168,139,255,0.35) 0%, rgba(201,123,238,0.12) 58%, rgba(0,0,0,0) 75%);
        }
        .donate-title {
            font-size: 21px; font-weight: 800; color: #ffffff;
            letter-spacing: -0.2px; margin-top: 4px;
        }
        .donate-body { font-size: 14px; color: #B7C6D8; line-height: 1.5; }
        .donate-brand {
            font-family: monospace; font-size: 10.5px; font-weight: 700;
            letter-spacing: 0.12em; text-transform: uppercase; color: #7C6EFF;
            margin-top: 6px;
        }
        .donate-dialog button.suggested-action {
            background: linear-gradient(120deg, #8A7CFF 0%, #A88BFF 48%, #C97BEE 100%);
            color: #14102A; font-weight: 800;
            box-shadow: 0 8px 22px rgba(138,124,255,0.35);
        }
        .donate-dialog button.suggested-action:hover { filter: brightness(1.08); }
        .donate-code-box {
            background: rgba(0,0,0,0.35);
            border: 1px dashed rgba(168,139,255,0.45);
            border-radius: 12px; padding: 10px 14px; margin-top: 4px;
        }
        .donate-code {
            font-family: monospace; font-size: 17px; font-weight: 700;
            color: #C9BBFF; letter-spacing: 0.06em;
        }
        .donate-instructions { font-size: 12px; color: #8394A8; margin-top: -4px; }
        .donate-mockup { margin-top: 6px; }
        .donate-mockup-label {
            font-size: 11px; color: #7A8AA0; margin-bottom: 2px;
        }
        .donate-mockup-field {
            background: #ffffff; border: 1px solid #d5dbe3; border-radius: 8px;
            padding: 12px 14px; min-height: 20px;
        }
        .donate-mockup-field .donate-code {
            color: #1a1a1a; font-size: 15px; font-weight: 700;
        }
        .donate-warning {
            font-size: 12.5px; color: #FFC876; margin-top: 10px;
            padding: 10px 14px; border-radius: 10px;
            background: rgba(255,178,89,0.10);
            border: 1px solid rgba(255,178,89,0.25);
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


class SoulApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="studio.vezzu.SOul")

    def do_activate(self):
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        Ventana(self).present()


def main():
    return SoulApp().run(None)
