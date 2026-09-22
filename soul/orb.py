"""El botón de escaneo de SOul, dibujado a mano con Cairo.

No es un botón normal con bordes redondeados: es una esfera de vidrio con
resplandor exterior, reflejo superior y un anillo que gira mientras
escanea. Se dibuja pixel a pixel para que se vea premium a cualquier
tamaño y en cualquier tema.
"""
import math

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gdk, Pango, PangoCairo  # noqa: E402

VIOLETA = (0.66, 0.55, 1.00)
MAGENTA = (0.83, 0.48, 0.96)


class Orbe(Gtk.DrawingArea):
    """Esfera interactiva. Emite 'clicked' al pulsarla."""

    __gsignals__ = {
        "clicked": (__import__("gi").repository.GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, tamano=236):
        super().__init__()
        self.set_content_width(tamano)
        self.set_content_height(tamano)
        self.set_halign(Gtk.Align.CENTER)
        self.tamano = tamano
        self.etiqueta = ""
        self.girando = False
        self.hover = False
        self.presionado = False
        self._angulo = 0.0
        self._pulso = 0.0
        self.set_draw_func(self._dibujar)

        clic = Gtk.GestureClick()
        clic.connect("pressed", self._presion)
        clic.connect("released", self._soltar)
        self.add_controller(clic)

        motion = Gtk.EventControllerMotion()
        motion.connect("enter", lambda *_: self._set_hover(True))
        motion.connect("leave", lambda *_: self._set_hover(False))
        self.add_controller(motion)

        self.set_cursor(Gdk.Cursor.new_from_name("pointer", None))
        GLib.timeout_add(16, self._tick)

    # --- interacción
    def _set_hover(self, valor):
        self.hover = valor
        self.queue_draw()

    def _presion(self, *_):
        self.presionado = True
        self.queue_draw()

    def _soltar(self, *_):
        if self.presionado:
            self.presionado = False
            self.queue_draw()
            self.emit("clicked")

    def _tick(self):
        if self.girando:
            self._angulo = (self._angulo + 0.055) % (math.pi * 2)
            self.queue_draw()
        else:
            self._pulso = (self._pulso + 0.012) % 1.0
            if self.hover or self._pulso < 0.06:
                self.queue_draw()
        return True

    def set_texto(self, texto):
        self.etiqueta = texto
        self.queue_draw()

    def set_girando(self, valor):
        self.girando = valor
        self.queue_draw()

    # --- dibujo
    def _dibujar(self, _area, cr, ancho, alto):
        cx, cy = ancho / 2, alto / 2
        r = min(ancho, alto) / 2 - 22
        escala = 1.0
        if self.presionado:
            escala = 0.965
        elif self.hover:
            escala = 1.025
        r *= escala

        # 1) resplandor exterior: empieza justo en el borde y se desvanece
        #    muy suave, si no queda un aro oscuro alrededor de la esfera.
        brillo = 0.42 + (0.14 if self.hover else 0.0) + math.sin(self._pulso * math.pi * 2) * 0.06
        alcance = r + 46
        halo = cairo_radial(cr, cx, cy, r * 0.96, alcance)
        halo.add_color_stop_rgba(0.00, *VIOLETA, brillo * 0.55)
        halo.add_color_stop_rgba(0.30, *MAGENTA, brillo * 0.26)
        halo.add_color_stop_rgba(0.62, *MAGENTA, brillo * 0.09)
        halo.add_color_stop_rgba(1.00, *MAGENTA, 0.0)
        cr.set_source(halo)
        cr.arc(cx, cy, alcance, 0, math.pi * 2)
        cr.fill()

        # 2) cuerpo de la esfera, con degradado diagonal
        cuerpo = cairo_lineal(cr, cx - r, cy - r, cx + r, cy + r)
        cuerpo.add_color_stop_rgba(0.0, 0.58, 0.50, 1.00, 1.0)
        cuerpo.add_color_stop_rgba(0.55, 0.64, 0.42, 0.96, 1.0)
        cuerpo.add_color_stop_rgba(1.0, 0.45, 0.30, 0.78, 1.0)
        cr.set_source(cuerpo)
        cr.arc(cx, cy, r, 0, math.pi * 2)
        cr.fill()

        # 3) reflejo de vidrio arriba
        reflejo = cairo_radial(cr, cx - r * 0.28, cy - r * 0.52, 2, r * 1.05)
        reflejo.add_color_stop_rgba(0, 1, 1, 1, 0.42)
        reflejo.add_color_stop_rgba(0.42, 1, 1, 1, 0.09)
        reflejo.add_color_stop_rgba(1, 1, 1, 1, 0.0)
        cr.set_source(reflejo)
        cr.arc(cx, cy, r, 0, math.pi * 2)
        cr.fill()

        # 4) sombra interior abajo, para dar volumen
        sombra = cairo_radial(cr, cx, cy + r * 0.62, r * 0.25, r * 1.1)
        sombra.add_color_stop_rgba(0, 0, 0, 0.15, 0.30)
        sombra.add_color_stop_rgba(1, 0, 0, 0, 0.0)
        cr.set_source(sombra)
        cr.arc(cx, cy, r, 0, math.pi * 2)
        cr.fill()

        # 5) borde fino claro
        cr.set_line_width(1.2)
        cr.set_source_rgba(1, 1, 1, 0.22)
        cr.arc(cx, cy, r - 0.6, 0, math.pi * 2)
        cr.stroke()

        # 6) anillo exterior: gira al escanear, sutil si está en reposo
        rr = r + 14
        cr.set_line_cap(1)  # redondeado
        if self.girando:
            cr.set_line_width(1.1)
            cr.set_source_rgba(*VIOLETA, 0.16)
            cr.arc(cx, cy, rr, 0, math.pi * 2)
            cr.stroke()
            cr.set_line_width(2.6)
            for i in range(3):
                inicio = self._angulo + i * (math.pi * 2 / 3)
                cr.set_source_rgba(*VIOLETA, 0.92 - i * 0.26)
                cr.arc(cx, cy, rr, inicio, inicio + 0.80)
                cr.stroke()
        else:
            cr.set_line_width(1.3)
            cr.set_source_rgba(*VIOLETA, 0.30 if self.hover else 0.18)
            cr.arc(cx, cy, rr, 0, math.pi * 2)
            cr.stroke()

        # 7) texto centrado
        if self.etiqueta:
            layout = PangoCairo.create_layout(cr)
            desc = Pango.FontDescription("Sans Bold 17")
            layout.set_font_description(desc)
            layout.set_text(self.etiqueta, -1)
            tw, th = layout.get_pixel_size()
            cr.set_source_rgba(0, 0, 0, 0.22)
            cr.move_to(cx - tw / 2, cy - th / 2 + 1.2)
            PangoCairo.show_layout(cr, layout)
            cr.set_source_rgba(1, 1, 1, 0.98)
            cr.move_to(cx - tw / 2, cy - th / 2)
            PangoCairo.show_layout(cr, layout)


def cairo_radial(cr, cx, cy, r0, r1):
    import cairo
    return cairo.RadialGradient(cx, cy, r0, cx, cy, r1)


def cairo_lineal(cr, x0, y0, x1, y1):
    import cairo
    return cairo.LinearGradient(x0, y0, x1, y1)
