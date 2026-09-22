"""Motor de SOul: escaneo y limpieza del sistema.

Reglas de seguridad que se respetan en todo este archivo:

1. Solo se tocan rutas de una lista blanca conocida (cachés, papelera,
   miniaturas, datos de navegador). Nunca documentos, fotos ni música.
2. Nada se borra sin que la interfaz pida confirmación antes.
3. Las operaciones que necesitan permisos de administrador NO ejecutan
   comandos libres: pasan por un script fijo propiedad de root con una
   lista cerrada de subcomandos.
4. Los procesos del sistema y del escritorio nunca se pueden cerrar:
   doble filtro por nombre conocido y por usuario propietario.
"""
import os
import re
import shutil
import subprocess
import time

import psutil

HOME = os.path.expanduser("~")
AYUDANTE = "/usr/local/bin/soul-mantenimiento.sh"
# copia del ayudante que viaja junto al código (repo o AppImage). Solo se
# usa para instalarlo la primera vez, si todavía no está en el sistema.
AYUDANTE_ORIGEN = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "packaging", "soul-mantenimiento.sh")

# --- procesos que nunca se listan como "cerrables" -------------------
PROTEGIDOS = {
    "plasmashell", "kwin_wayland", "kwin_wayland_wrapper", "kded6",
    "kglobalacceld", "ksmserver", "kwalletd6", "sddm", "sddm-greeter",
    "Xwayland", "xwaylandvideobridge", "dbus-broker", "dbus-daemon",
    "systemd", "systemd-logind", "systemd-journald", "systemd-udevd",
    "pipewire", "pipewire-pulse", "wireplumber", "NetworkManager",
    "polkitd", "udisksd", "upowerd", "gnome-shell", "mutter", "gdm",
    "gdm-session-worker", "Xorg", "DiscoverNotifier", "plasma-keyboard",
    "xdg-desktop-portal", "xdg-desktop-por", "akonadi_control",
    "baloo_file", "baloo_file_extractor", "init",
    "polkit-kde-authentication-agent-1", "kiod6", "kalendarac", "korgac",
    "kactivitymanagerd", "kscreenlocker_greet", "drkonqi", "kaccess",
    "org_kde_powerdevil", "kioworker", "xdg-document-portal",
    "xdg-permission-store", "at-spi2-registryd", "at-spi-bus-launcher",
    "gvfsd", "gvfsd-trash", "gvfs-udisks2-volume-monitor", "ksplashqml",
    "startplasma-wayland", "python3", "soul", "app.py",
}

NAVEGADORES = {"firefox", "chrome", "chromium", "brave", "vivaldi", "opera"}


# --- utilidades ------------------------------------------------------

def fmt_size(b):
    if b is None:
        return ""
    for unidad, div in (("TB", 1024 ** 4), ("GB", 1024 ** 3), ("MB", 1024 ** 2), ("KB", 1024)):
        if b >= div:
            valor = b / div
            return f"{valor:.1f} {unidad}" if valor < 100 else f"{valor:.0f} {unidad}"
    return f"{b} B"


def dir_size(ruta, limite_seg=8):
    """Tamaño real de una carpeta. Se rinde tras unos segundos para no colgarse."""
    if not ruta or not os.path.isdir(ruta):
        return 0
    total = 0
    inicio = time.time()
    for raiz, dirs, archivos in os.walk(ruta, onerror=lambda e: None):
        if time.time() - inicio > limite_seg:
            break
        for a in archivos:
            try:
                st = os.lstat(os.path.join(raiz, a))
                if not os.path.islink(os.path.join(raiz, a)):
                    total += st.st_size
            except OSError:
                continue
    return total


def _borrar_contenido(ruta):
    """Borra lo que hay DENTRO de una carpeta, nunca la carpeta en sí."""
    if not os.path.isdir(ruta):
        return
    for nombre in os.listdir(ruta):
        objetivo = os.path.join(ruta, nombre)
        try:
            if os.path.isdir(objetivo) and not os.path.islink(objetivo):
                shutil.rmtree(objetivo, ignore_errors=True)
            else:
                os.remove(objetivo)
        except OSError:
            continue


def _root(subcomando):
    """Ejecuta una de las tareas fijas del ayudante con permisos de root."""
    subprocess.run(
        ["pkexec", AYUDANTE, subcomando],
        check=True, capture_output=True, text=True, timeout=300,
    )


POLITICA = "/usr/share/polkit-1/actions/studio.vezzu.soul.policy"

# ====================================================================
#  DONACION — codigo por instalacion + verificacion contra un servidor
#  propio (ver server/worker.js). Sin esto, "ya done" era una casilla
#  que cualquiera marcaba sin pagar. Con esto, solo se marca cuando ese
#  codigo exacto aparecio de verdad en un pago de Ko-fi.
#
#  Limite real, dicho con honestidad: esto sube el costo de mentir (hay
#  que editar el archivo local a mano), pero como el codigo es Python
#  abierto corriendo en la maquina de cada quien, nada de esto puede ser
#  IMPOSIBLE de saltar. Eso no existe para software de escritorio.
# ====================================================================
_ARCHIVO_CODIGO = os.path.join(HOME, ".local", "share", "soul", "codigo_donacion")
_ARCHIVO_DONADO = os.path.join(HOME, ".local", "share", "soul", "donado")
_ARCHIVO_APERTURAS = os.path.join(HOME, ".local", "share", "soul", "aperturas")
_ALFABETO_CODIGO = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"  # sin 0/O/1/I/L
SERVIDOR_DONACION = "https://soul-donaciones.vezzulab.workers.dev"


def contar_apertura():
    """Suma uno al contador de veces que se abrio SOul y devuelve el
    total (incluida esta vez). En la primera apertura de todas no se
    pide donacion: la persona merece usarla sin interrupciones antes de
    que le pidamos algo. Desde la segunda apertura en adelante, si."""
    n = 0
    try:
        with open(_ARCHIVO_APERTURAS) as f:
            n = int(f.read().strip() or "0")
    except (OSError, ValueError):
        n = 0
    n += 1
    try:
        os.makedirs(os.path.dirname(_ARCHIVO_APERTURAS), exist_ok=True)
        with open(_ARCHIVO_APERTURAS, "w") as f:
            f.write(str(n))
    except OSError:
        pass
    return n


def codigo_donacion():
    """Codigo unico de esta instalacion. Se genera una sola vez y se
    reusa siempre — no hay forma en la interfaz de escribir uno distinto
    a mano, a proposito: asi un codigo ajeno publicado en un foro no le
    sirve a nadie mas, porque ningun SOul tiene donde pegarlo."""
    if os.path.isfile(_ARCHIVO_CODIGO):
        with open(_ARCHIVO_CODIGO) as f:
            existente = f.read().strip()
        if existente:
            return existente
    import random
    codigo = "SOUL-" + "".join(random.choices(_ALFABETO_CODIGO, k=8))
    try:
        os.makedirs(os.path.dirname(_ARCHIVO_CODIGO), exist_ok=True)
        with open(_ARCHIVO_CODIGO, "w") as f:
            f.write(codigo)
    except OSError:
        pass
    return codigo


def ya_dono():
    return os.path.isfile(_ARCHIVO_DONADO)


def verificar_donacion():
    """Pregunta al servidor si el codigo de esta instalacion ya aparecio
    en un pago real. Se llama desde un hilo aparte: es una peticion de
    red, no debe congelar la interfaz."""
    import json
    import urllib.request
    codigo = codigo_donacion()
    try:
        url = f"{SERVIDOR_DONACION}/verificar?codigo={codigo}"
        with urllib.request.urlopen(url, timeout=8) as resp:
            datos = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return False  # sin internet o el servidor no respondio: no se asume nada
    if datos.get("donado"):
        try:
            os.makedirs(os.path.dirname(_ARCHIVO_DONADO), exist_ok=True)
            open(_ARCHIVO_DONADO, "w").close()
        except OSError:
            pass
        return True
    return False


def integrar_appimage():
    """Copia el .desktop y el icono del AppImage a las carpetas propias
    del usuario (sin pedir permisos: son solo suyas). Sin esto, la barra
    de tareas y el menú de aplicaciones no saben qué icono mostrar,
    porque el AppImage no está "instalado" en ningún lado que el
    escritorio conozca.

    Se repite en cada arranque a propósito, no solo la primera vez: son
    dos archivos chicos, y así una actualización del icono se refleja
    sola en vez de quedar pegada a la versión con la que se integró la
    primera vez."""
    appdir = os.environ.get("APPDIR")
    appimage = os.environ.get("APPIMAGE")
    if not appdir or not appimage:
        return
    try:
        icon_origen = os.path.join(
            appdir, "usr", "share", "icons", "hicolor", "scalable", "apps",
            "studio.vezzu.SOul.svg")
        icon_destino_dir = os.path.join(
            HOME, ".local", "share", "icons", "hicolor", "scalable", "apps")
        os.makedirs(icon_destino_dir, exist_ok=True)
        if os.path.isfile(icon_origen):
            shutil.copyfile(
                icon_origen,
                os.path.join(icon_destino_dir, "studio.vezzu.SOul.svg"))

        apps_dir = os.path.join(HOME, ".local", "share", "applications")
        os.makedirs(apps_dir, exist_ok=True)
        with open(os.path.join(apps_dir, "studio.vezzu.SOul.desktop"), "w") as f:
            f.write(
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=SOul\n"
                "GenericName=System care\n"
                "Comment=SO + alma: el alma de tu sistema, en simple\n"
                f"Exec={appimage}\n"
                "Icon=studio.vezzu.SOul\n"
                "Terminal=false\n"
                "Categories=System;Monitor;Utility;\n"
            )

        subprocess.run(["update-desktop-database", apps_dir],
                        capture_output=True, timeout=10)
    except OSError:
        pass


def polkit_listo():
    """¿Ya está puesta la política que evita pedir la contraseña siempre?"""
    return os.path.isfile(POLITICA)


def reiniciar_polkit():
    """Quita la política instalada para que SOul vuelva a ofrecer el
    permiso desde cero, como si fuera la primera vez. Pide contraseña
    una vez (un solo comando fijo, sin datos variables)."""
    try:
        subprocess.run(["pkexec", "rm", "-f", POLITICA],
                        check=True, capture_output=True, text=True, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return False
    return not os.path.isfile(POLITICA)


def instalar_polkit(origen):
    """Pide la contraseña UNA vez y deja el permiso puesto para siempre.

    Si el ayudante todavía no está instalado en el sistema (caso del
    AppImage, que no pasa por install.sh), se instala primero desde la
    copia que viaja junto al código. Es la misma autorización de pkexec,
    solo que en dos pasos: primero el ayudante, luego su política.
    """
    if not os.path.isfile(origen):
        return False
    if not os.path.isfile(AYUDANTE):
        if not os.path.isfile(AYUDANTE_ORIGEN):
            return False
        subprocess.run(
            ["pkexec", "install", "-m", "0755", "-o", "root", "-g", "root",
             AYUDANTE_ORIGEN, AYUDANTE],
            check=True, capture_output=True, text=True, timeout=120,
        )
    subprocess.run(
        ["pkexec", AYUDANTE, "install-policy", origen],
        check=True, capture_output=True, text=True, timeout=120,
    )
    return polkit_listo()


def proceso_corriendo(nombres):
    """¿Hay algún proceso con estos nombres corriendo ahora?"""
    for p in psutil.process_iter(["name"]):
        try:
            n = (p.info["name"] or "").lower()
            if any(x in n for x in nombres):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


# --- perfiles de navegador ------------------------------------------

def _perfiles_firefox():
    base = os.path.join(HOME, ".mozilla", "firefox")
    if not os.path.isdir(base):
        return []
    return [
        os.path.join(base, d) for d in os.listdir(base)
        if os.path.isdir(os.path.join(base, d)) and (".default" in d or d.endswith(".dev-edition-default"))
    ]


def _cache_firefox():
    base = os.path.join(HOME, ".cache", "mozilla", "firefox")
    if not os.path.isdir(base):
        return []
    return [os.path.join(base, d) for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]


def _chromium_dirs():
    rutas = []
    for conf, cache in (
        (".config/google-chrome", ".cache/google-chrome"),
        (".config/chromium", ".cache/chromium"),
        (".config/BraveSoftware/Brave-Browser", ".cache/BraveSoftware/Brave-Browser"),
    ):
        c = os.path.join(HOME, conf)
        k = os.path.join(HOME, cache)
        if os.path.isdir(c):
            rutas.append((c, k))
    return rutas


# ====================================================================
#  LIMPIEZA
# ====================================================================

def _scan_cache():
    ruta = os.path.join(HOME, ".cache")
    total = dir_size(ruta)
    # las miniaturas se ofrecen aparte, no las contamos dos veces
    return max(0, total - dir_size(os.path.join(ruta, "thumbnails")))


def _clean_cache():
    ruta = os.path.join(HOME, ".cache")
    if not os.path.isdir(ruta):
        return
    for nombre in os.listdir(ruta):
        if nombre == "thumbnails":
            continue
        objetivo = os.path.join(ruta, nombre)
        try:
            if os.path.isdir(objetivo) and not os.path.islink(objetivo):
                shutil.rmtree(objetivo, ignore_errors=True)
            else:
                os.remove(objetivo)
        except OSError:
            continue


def _scan_journal():
    try:
        out = subprocess.run(["journalctl", "--disk-usage"],
                             capture_output=True, text=True, timeout=15).stdout
        m = re.search(r"take up ([\d.]+)([KMGT])", out)
        if not m:
            return 0
        val, uni = float(m.group(1)), m.group(2)
        mult = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3, "T": 1024 ** 4}[uni]
        return int(val * mult)
    except Exception:
        return 0


def _cache_flatpak_apps():
    """Cada app Flatpak guarda su propia caché en ~/.var/app/<id>/cache."""
    base = os.path.join(HOME, ".var", "app")
    if not os.path.isdir(base):
        return []
    rutas = []
    for app in os.listdir(base):
        ruta = os.path.join(base, app, "cache")
        if os.path.isdir(ruta):
            rutas.append(ruta)
    return rutas


# cachés de herramientas de desarrollo: se regeneran descargando de nuevo
CACHES_DEV = [
    os.path.join(HOME, ".npm", "_cacache"),
    os.path.join(HOME, ".cache", "pip"),
    os.path.join(HOME, ".cache", "yarn"),
    os.path.join(HOME, ".cache", "go-build"),
    os.path.join(HOME, ".cargo", "registry", "cache"),
    os.path.join(HOME, ".gradle", "caches"),
    os.path.join(HOME, ".cache", "composer"),
]


def _scan_huerfanos():
    """Cuenta paquetes que ya nadie necesita (según el propio dnf)."""
    try:
        out = subprocess.run(["dnf", "repoquery", "--unneeded", "-q"],
                             capture_output=True, text=True, timeout=90).stdout
        return len([l for l in out.splitlines() if l.strip()])
    except Exception:
        return 0


TAREAS_LIMPIEZA = [
    {
        "id": "cache", "icono": "cache", "titulo": "cleanup.cache", "desc": "cleanup.cache.desc",
        "scan": _scan_cache, "clean": _clean_cache, "root": False,
    },
    {
        "id": "thumbs", "icono": "thumbs", "titulo": "cleanup.thumbs", "desc": "cleanup.thumbs.desc",
        "scan": lambda: dir_size(os.path.join(HOME, ".cache", "thumbnails")),
        "clean": lambda: _borrar_contenido(os.path.join(HOME, ".cache", "thumbnails")),
        "root": False,
    },
    {
        "id": "trash", "icono": "trash", "titulo": "cleanup.trash", "desc": "cleanup.trash.desc",
        "scan": lambda: dir_size(os.path.join(HOME, ".local", "share", "Trash")),
        "clean": lambda: [
            _borrar_contenido(os.path.join(HOME, ".local", "share", "Trash", s))
            for s in ("files", "info", "expunged")
        ],
        "root": False,
    },
    {
        "id": "packages", "icono": "packages", "titulo": "cleanup.packages", "desc": "cleanup.packages.desc",
        "scan": lambda: dir_size("/var/cache/libdnf5") + dir_size("/var/cache/dnf"),
        "clean": lambda: _root("dnf-cache"), "root": True,
    },
    {
        "id": "logs", "icono": "logs", "titulo": "cleanup.logs", "desc": "cleanup.logs.desc",
        "scan": _scan_journal, "clean": lambda: _root("journal"), "root": True,
    },
    {
        "id": "flatpak", "icono": "flatpak", "titulo": "cleanup.flatpak", "desc": "cleanup.flatpak.desc",
        "scan": lambda: None, "clean": lambda: _root("flatpak-unused"), "root": True,
    },
    {
        "id": "fpcache", "icono": "cache", "titulo": "cleanup.fpcache", "desc": "cleanup.fpcache.desc",
        "scan": lambda: sum(dir_size(r) for r in _cache_flatpak_apps()),
        "clean": lambda: [_borrar_contenido(r) for r in _cache_flatpak_apps()],
        "root": False,
    },
    {
        "id": "coredumps", "icono": "crash", "titulo": "cleanup.coredumps", "desc": "cleanup.coredumps.desc",
        "scan": lambda: dir_size("/var/lib/systemd/coredump"),
        "clean": lambda: _root("coredumps"), "root": True,
    },
    {
        "id": "devcache", "icono": "dev", "titulo": "cleanup.devcache", "desc": "cleanup.devcache.desc",
        "scan": lambda: sum(dir_size(r) for r in CACHES_DEV),
        "clean": lambda: [_borrar_contenido(r) for r in CACHES_DEV],
        "root": False,
    },
    {
        "id": "huerfanos", "icono": "packages", "titulo": "cleanup.orphans", "desc": "cleanup.orphans.desc",
        "scan": lambda: None, "clean": lambda: _root("autoremove"),
        "root": True, "peligroso": True,  # no marcado por defecto: conviene revisarlo
    },
]


# ====================================================================
#  PRIVACIDAD
# ====================================================================

def _scan_browser_cache():
    total = sum(dir_size(p) for p in _cache_firefox())
    for _conf, cache in _chromium_dirs():
        total += dir_size(cache)
    return total


def _clean_browser_cache():
    for p in _cache_firefox():
        _borrar_contenido(p)
    for _conf, cache in _chromium_dirs():
        _borrar_contenido(cache)


def _scan_cookies():
    total = 0
    for perfil in _perfiles_firefox():
        for f in ("cookies.sqlite", "cookies.sqlite-wal", "sessionstore.jsonlz4"):
            ruta = os.path.join(perfil, f)
            if os.path.isfile(ruta):
                total += os.path.getsize(ruta)
    for conf, _cache in _chromium_dirs():
        for f in ("Default/Cookies", "Default/Network/Cookies"):
            ruta = os.path.join(conf, f)
            if os.path.isfile(ruta):
                total += os.path.getsize(ruta)
    return total


def _clean_cookies():
    # nunca tocar los archivos con el navegador abierto: se corrompen
    if proceso_corriendo(NAVEGADORES):
        raise RuntimeError("browser_open")
    for perfil in _perfiles_firefox():
        for f in ("cookies.sqlite", "cookies.sqlite-wal", "cookies.sqlite-shm",
                  "sessionstore.jsonlz4"):
            try:
                os.remove(os.path.join(perfil, f))
            except OSError:
                pass
    for conf, _cache in _chromium_dirs():
        for f in ("Default/Cookies", "Default/Cookies-journal", "Default/Network/Cookies"):
            try:
                os.remove(os.path.join(conf, f))
            except OSError:
                pass


def _archivo_size(ruta):
    try:
        return os.path.getsize(ruta)
    except OSError:
        return 0


def _scan_recent():
    return _archivo_size(os.path.join(HOME, ".local", "share", "recently-used.xbel"))


def _clean_recent():
    for f in ("recently-used.xbel", "recently-used.xbel.bak"):
        try:
            os.remove(os.path.join(HOME, ".local", "share", f))
        except OSError:
            pass
    _borrar_contenido(os.path.join(HOME, ".local", "share", "RecentDocuments"))


def _scan_shell():
    return sum(_archivo_size(os.path.join(HOME, f))
               for f in (".bash_history", ".zsh_history", ".python_history"))


def _clean_shell():
    for f in (".bash_history", ".zsh_history", ".python_history"):
        ruta = os.path.join(HOME, f)
        try:
            if os.path.isfile(ruta):
                open(ruta, "w").close()
        except OSError:
            pass


TAREAS_PRIVACIDAD = [
    {
        "id": "bcache", "icono": "browser", "titulo": "privacy.browser_cache",
        "desc": "privacy.browser_cache.desc",
        "scan": _scan_browser_cache, "clean": _clean_browser_cache, "root": False,
    },
    {
        "id": "cookies", "icono": "cookies", "titulo": "privacy.cookies", "desc": "privacy.cookies.desc",
        "scan": _scan_cookies, "clean": _clean_cookies, "root": False, "peligroso": True,
    },
    {
        "id": "recent", "icono": "recent", "titulo": "privacy.recent", "desc": "privacy.recent.desc",
        "scan": _scan_recent, "clean": _clean_recent, "root": False,
    },
    {
        "id": "shell", "icono": "shell", "titulo": "privacy.shell", "desc": "privacy.shell.desc",
        "scan": _scan_shell, "clean": _clean_shell, "root": False,
    },
]


# ====================================================================
#  RENDIMIENTO
# ====================================================================

# ====================================================================
#  PROCESOS EN VIVO — el reemplazo real de htop
# ====================================================================
# Traduce nombres de proceso crudos a algo que alguien sin conocimientos
# de tecnología reconoce. Es la pieza central de SOul: donde htop muestra
# "code", "Isolated Web Co", "soffice.bin", aquí se explica qué es.

NOMBRES_AMIGABLES = {
    "firefox": ("Firefox", "Navegador web"),
    "firefox-esr": ("Firefox", "Navegador web"),
    "chrome": ("Google Chrome", "Navegador web"),
    "chromium": ("Chromium", "Navegador web"),
    "brave": ("Brave", "Navegador web"),
    "vivaldi-bin": ("Vivaldi", "Navegador web"),
    "opera": ("Opera", "Navegador web"),
    "code": ("Visual Studio Code", "Editor de código"),
    "codium": ("VSCodium", "Editor de código"),
    "soffice.bin": ("LibreOffice", "Suite de oficina"),
    "thunderbird": ("Thunderbird", "Correo electrónico"),
    "discord": ("Discord", "Chat de voz y texto"),
    "Discord": ("Discord", "Chat de voz y texto"),
    "spotify": ("Spotify", "Música"),
    "steam": ("Steam", "Tienda y lanzador de juegos"),
    "steamwebhelper": ("Steam", "Ayudante interno de Steam"),
    "gimp": ("GIMP", "Editor de imágenes"),
    "inkscape": ("Inkscape", "Editor de gráficos vectoriales"),
    "blender": ("Blender", "Edición 3D"),
    "obs": ("OBS Studio", "Grabación y transmisión de pantalla"),
    "telegram-desktop": ("Telegram", "Mensajería"),
    "slack": ("Slack", "Chat de trabajo"),
    "zoom": ("Zoom", "Videollamadas"),
    "vlc": ("VLC", "Reproductor multimedia"),
    "mpv": ("mpv", "Reproductor multimedia"),
    "easyeffects": ("Easy Effects", "Ecualizador de audio del sistema"),
    "gnome-terminal-server": ("Terminal", "Línea de comandos"),
    "konsole": ("Konsole", "Línea de comandos"),
    "dolphin": ("Dolphin", "Explorador de archivos"),
    "nautilus": ("Archivos", "Explorador de archivos"),
    "claude": ("Claude Code", "Asistente de IA en la terminal"),
    "docker": ("Docker", "Contenedores de desarrollo"),
    "dockerd": ("Docker", "Servicio de contenedores"),
    "VirtualBox": ("VirtualBox", "Máquinas virtuales"),
    "juke": ("Juke", "Reproductor de música"),
    "soul": ("SOul", "Esta misma app"),
    "gnome-boxes": ("Boxes", "Máquinas virtuales"),
    "code-insiders": ("VS Code Insiders", "Editor de código"),
    "signal-desktop": ("Signal", "Mensajería"),
    "whatsapp-for-linux": ("WhatsApp", "Mensajería"),
}

# nombres que aparecen en htop pero son piezas internas de otra app,
# no procesos que alguien "abrió" — se agrupan bajo el nombre de la app
PERTENECE_A = {
    "Isolated Web Co": "firefox", "Web Content": "firefox",
    "Privileged Cont": "firefox", "RDD Process": "firefox",
    "crashpad_handle": None, "Utility Process": None,
}


def _nombre_amigable(nombre_crudo, cmdline):
    """(nombre a mostrar, descripción de una línea, es_reconocido)"""
    if nombre_crudo in NOMBRES_AMIGABLES:
        n, d = NOMBRES_AMIGABLES[nombre_crudo]
        return n, d, True
    # procesos hijos de Electron/Chromium con nombres genéricos: buscar
    # el ejecutable real en la línea de comandos
    texto = " ".join(cmdline[:2]) if cmdline else ""
    for clave, (n, d) in NOMBRES_AMIGABLES.items():
        if clave and clave in texto:
            return n, f"{d} · proceso auxiliar", True
    return nombre_crudo, None, False


_CACHE_CPU = {}  # pid -> psutil.Process, con medición previa ya tomada


def _cpu_real(pid):
    """% de CPU real desde la última lectura, no desde que arrancó el
    proceso (que es lo que da un Process() nuevo cada vez y por eso
    siempre marca 0%). Igual que hace htop: hace falta un objeto que
    persista entre lecturas."""
    p = _CACHE_CPU.get(pid)
    if p is None:
        try:
            p = psutil.Process(pid)
            p.cpu_percent(None)  # primera llamada: fija la base, no es real
            _CACHE_CPU[pid] = p
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0.0
        return 0.0
    try:
        return p.cpu_percent(None)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        _CACHE_CPU.pop(pid, None)
        return 0.0


def procesos_vivos(limite=40):
    """Todos los procesos de tu sesión, traducidos. Base de la vista
    'Procesos en vivo': el reemplazo directo de la tabla de htop."""
    try:
        mi_usuario = psutil.Process().username()
    except Exception:
        mi_usuario = None

    vistos = set()
    filas = []
    for p in psutil.process_iter(["pid", "name", "username", "memory_info", "cmdline"]):
        try:
            if mi_usuario and p.info["username"] != mi_usuario:
                continue
            nombre_crudo = p.info["name"] or "?"
            if nombre_crudo in PROTEGIDOS:
                continue
            mi = p.info["memory_info"]
            mb = (mi.rss / (1024 * 1024)) if mi else 0
            if mb < 8:  # procesos minúsculos no aportan nada al usuario
                continue
            pid = p.info["pid"]
            vistos.add(pid)
            amigable, desc, reconocido = _nombre_amigable(nombre_crudo, p.info.get("cmdline") or [])
            filas.append({
                "pid": pid,
                "nombre_crudo": nombre_crudo,
                "nombre": amigable,
                "desc": desc,
                "reconocido": reconocido,
                "mb": mb,
                "cpu": _cpu_real(pid),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # limpiar del cache los procesos que ya no existen
    for pid in list(_CACHE_CPU):
        if pid not in vistos:
            _CACHE_CPU.pop(pid, None)

    # agrupar por nombre amigable (Firefox con 12 procesos hijos = 1 fila)
    agrupado = {}
    for f in filas:
        clave = f["nombre"]
        if clave not in agrupado:
            agrupado[clave] = {"nombre": clave, "desc": f["desc"], "reconocido": f["reconocido"],
                               "mb": 0.0, "cpu": 0.0, "pids": [], "procesos": 0}
        g = agrupado[clave]
        g["mb"] += f["mb"]
        g["cpu"] += f["cpu"]
        g["pids"].append(f["pid"])
        g["procesos"] += 1

    orden = sorted(agrupado.values(), key=lambda x: -(x["mb"] + x["cpu"] * 15))
    return orden[:limite]


def apps_pesadas(limite=8):
    """Procesos agrupados por nombre amigable (los mismos que junta
    'Procesos en vivo': Firefox con sus procesos hijos cuenta como una
    sola app, no como cuatro filas sueltas). Doble filtro: lista y
    usuario."""
    try:
        mi_usuario = psutil.Process().username()
    except Exception:
        mi_usuario = None
    agrupado = {}
    for p in psutil.process_iter(["pid", "name", "memory_info", "username", "cmdline"]):
        try:
            if mi_usuario and p.info["username"] != mi_usuario:
                continue
            nombre_crudo = p.info["name"] or "?"
            if nombre_crudo in PROTEGIDOS:
                continue
            amigable, _desc, _reconocido = _nombre_amigable(
                nombre_crudo, p.info.get("cmdline") or [])
            mi = p.info["memory_info"]
            agrupado.setdefault(amigable, {"bytes": 0, "pids": []})
            agrupado[amigable]["bytes"] += mi.rss if mi else 0
            agrupado[amigable]["pids"].append(p.info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    orden = sorted(agrupado.items(), key=lambda x: -x[1]["bytes"])
    return [(n, d["bytes"], d["pids"]) for n, d in orden[:limite] if d["bytes"] > 30 * 1024 ** 2]


def cerrar_app(pids):
    cerrados = 0
    for pid in pids:
        try:
            psutil.Process(pid).terminate()
            cerrados += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return cerrados


def autostart_items():
    """Programas que arrancan solos (carpeta autostart del usuario)."""
    items = []
    carpeta = os.path.join(HOME, ".config", "autostart")
    if not os.path.isdir(carpeta):
        return items
    for f in sorted(os.listdir(carpeta)):
        if not f.endswith(".desktop"):
            continue
        ruta = os.path.join(carpeta, f)
        nombre, activo = f[:-8], True
        try:
            with open(ruta, "r", errors="ignore") as fh:
                for linea in fh:
                    if linea.startswith("Name=") and nombre == f[:-8]:
                        nombre = linea.split("=", 1)[1].strip()
                    if linea.strip() in ("Hidden=true", "X-GNOME-Autostart-enabled=false"):
                        activo = False
        except OSError:
            continue
        items.append({"nombre": nombre, "ruta": ruta, "activo": activo})
    return items


def toggle_autostart(ruta, activar):
    """Activa o desactiva un programa de arranque, sin borrar el archivo."""
    try:
        with open(ruta, "r", errors="ignore") as fh:
            lineas = [l for l in fh if l.strip() not in ("Hidden=true", "Hidden=false")]
        if not activar:
            lineas.append("Hidden=true\n")
        with open(ruta, "w") as fh:
            fh.writelines(lineas)
        return True
    except OSError:
        return False


def servicios_fallidos():
    try:
        out = subprocess.run(
            ["systemctl", "--user", "list-units", "--state=failed", "--no-legend", "--plain"],
            capture_output=True, text=True, timeout=15).stdout
        out2 = subprocess.run(
            ["systemctl", "list-units", "--state=failed", "--no-legend", "--plain"],
            capture_output=True, text=True, timeout=15).stdout
        nombres = []
        for linea in (out + out2).splitlines():
            partes = linea.split()
            if partes and partes[0].endswith((".service", ".timer", ".mount")):
                nombres.append(partes[0])
        return nombres
    except Exception:
        return []


# ====================================================================
#  APLICACIONES
# ====================================================================

def apps_instaladas(limite=200):
    """Apps con icono en el menú (lo que el usuario reconoce como programa)."""
    vistos, apps = set(), []
    dirs = [
        "/usr/share/applications",
        "/var/lib/flatpak/exports/share/applications",
        os.path.join(HOME, ".local/share/applications"),
        os.path.join(HOME, ".local/share/flatpak/exports/share/applications"),
    ]
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith(".desktop"):
                continue
            ruta = os.path.join(d, f)
            nombre, oculto, nodisplay = None, False, False
            try:
                with open(ruta, "r", errors="ignore") as fh:
                    for linea in fh:
                        s = linea.strip()
                        if s.startswith("Name=") and nombre is None:
                            nombre = s.split("=", 1)[1]
                        elif s == "NoDisplay=true":
                            nodisplay = True
                        elif s == "Hidden=true":
                            oculto = True
            except OSError:
                continue
            if not nombre or oculto or nodisplay or nombre in vistos:
                continue
            vistos.add(nombre)
            es_flatpak = "flatpak" in d
            apps.append({"nombre": nombre, "id": f[:-8], "flatpak": es_flatpak})
            if len(apps) >= limite:
                return apps
    return apps


_ID_VALIDO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{1,127}$")


def desinstalar_app(app):
    """Desinstala SOLO apps Flatpak.

    Las de Fedora (dnf) se dejan fuera a propósito: quitar un paquete del
    sistema puede arrastrar dependencias y dejar el equipo inservible, y
    eso no se puede decidir desde un botón sin mostrar el árbol completo.
    """
    if not app.get("flatpak"):
        return False
    app_id = app.get("id", "")
    if not _ID_VALIDO.match(app_id):
        return False
    subprocess.run(
        ["pkexec", AYUDANTE, "flatpak-remove", app_id],
        check=True, capture_output=True, text=True, timeout=300,
    )
    return True


def buscar_actualizaciones():
    """Cuenta actualizaciones pendientes. Solo consulta, no instala nada."""
    resultado = {"dnf": 0, "flatpak": 0}
    try:
        p = subprocess.run(["dnf", "check-update", "-q"],
                           capture_output=True, text=True, timeout=120)
        resultado["dnf"] = len([
            l for l in p.stdout.splitlines()
            if l.strip() and not l.startswith(("Last metadata", "Obsoleting", " "))
        ])
    except Exception:
        pass
    try:
        p = subprocess.run(["flatpak", "remote-ls", "--updates"],
                           capture_output=True, text=True, timeout=120)
        resultado["flatpak"] = len([l for l in p.stdout.splitlines() if l.strip()])
    except Exception:
        pass
    return resultado


# ====================================================================
#  ESPACIO
# ====================================================================

CARPETAS_HOME = [
    "Descargas", "Downloads", "Documentos", "Documents", "Imágenes", "Pictures",
    "Vídeos", "Videos", "Música", "Music", "Escritorio", "Desktop",
    ".cache", ".local", ".config", ".var", "dev", "Proyectos", "Projects",
]


def carpetas_grandes(limite=10):
    resultados = []
    try:
        entradas = os.listdir(HOME)
    except OSError:
        return resultados
    for nombre in entradas:
        ruta = os.path.join(HOME, nombre)
        if not os.path.isdir(ruta) or os.path.islink(ruta):
            continue
        tam = dir_size(ruta, limite_seg=4)
        if tam > 50 * 1024 ** 2:
            resultados.append((nombre, tam, ruta))
    resultados.sort(key=lambda x: -x[1])
    return resultados[:limite]


def archivos_grandes(minimo_mb=200, limite=15):
    resultados = []
    inicio = time.time()
    saltar = {".cache", ".local/share/Trash", "node_modules", ".git", ".var"}
    for raiz, dirs, archivos in os.walk(HOME, onerror=lambda e: None):
        if time.time() - inicio > 12:
            break
        dirs[:] = [d for d in dirs if d not in saltar and not d.startswith(".cache")]
        for a in archivos:
            ruta = os.path.join(raiz, a)
            try:
                if os.path.islink(ruta):
                    continue
                tam = os.path.getsize(ruta)
                if tam >= minimo_mb * 1024 ** 2:
                    resultados.append((a, tam, ruta))
            except OSError:
                continue
    resultados.sort(key=lambda x: -x[1])
    return resultados[:limite]


# ====================================================================
#  SALUD
# ====================================================================

def salud():
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")
    bat = psutil.sensors_battery()
    datos = {
        "mem_pct": mem.percent, "mem_used": mem.used, "mem_total": mem.total,
        "swap_used": swap.used,
        "cpu_pct": psutil.cpu_percent(interval=0.2),
        "disk_pct": disk.percent, "disk_free": disk.free, "disk_total": disk.total,
        "uptime": time.time() - psutil.boot_time(),
        "bateria": None, "temp": None, "bat_salud": None,
    }
    if bat is not None:
        datos["bateria"] = {"pct": round(bat.percent), "cargando": bat.power_plugged}
        datos["bat_salud"] = salud_bateria()
    try:
        temps = psutil.sensors_temperatures()
        for clave in ("k10temp", "coretemp", "acpitz", "zenpower"):
            if clave in temps and temps[clave]:
                datos["temp"] = round(temps[clave][0].current)
                break
    except Exception:
        pass
    return datos


def salud_bateria():
    """Capacidad actual frente a la de fábrica, si el firmware la reporta bien."""
    base = "/sys/class/power_supply"
    if not os.path.isdir(base):
        return None
    for bat in os.listdir(base):
        d = os.path.join(base, bat)
        try:
            with open(os.path.join(d, "type")) as f:
                if f.read().strip() != "Battery":
                    continue
            full = design = None
            for nom, key in (("charge_full", "full"), ("energy_full", "full"),
                             ("charge_full_design", "design"), ("energy_full_design", "design")):
                ruta = os.path.join(d, nom)
                if os.path.isfile(ruta):
                    with open(ruta) as f:
                        val = int(f.read().strip())
                    if key == "full" and full is None:
                        full = val
                    elif key == "design" and design is None:
                        design = val
            if full and design and design > 0:
                pct = round(full / design * 100)
                # muchos equipos reportan ambos iguales aunque este gastada:
                # en ese caso el dato no sirve, mejor no mostrar nada.
                return None if pct >= 100 else pct
        except (OSError, ValueError):
            continue
    return None


# ====================================================================
#  REGISTRO DE PROBLEMAS — el mismo journalctl que usa un ingeniero,
#  pero traducido. Si no se reconoce el patrón, NO se muestra: es mejor
#  callar que enseñar una línea en inglés técnico que asusta sin motivo.
# ====================================================================

def _programa_amigable(ruta_o_nombre):
    base = os.path.basename(ruta_o_nombre)
    if base in NOMBRES_AMIGABLES:
        return NOMBRES_AMIGABLES[base][0]
    return base


def _crashes_recientes(dias=3):
    """Programas que se cerraron de golpe (coredumpctl), agrupados."""
    try:
        out = subprocess.run(
            ["coredumpctl", "list", "--no-pager", "--since", f"-{dias} days"],
            capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return []
    agrupado = {}
    for linea in out.splitlines():
        partes = linea.split()
        if len(partes) < 9 or partes[0] == "TIME":
            continue
        # TIME(4) PID UID GID SIG PRESENT EXE SIZE  -> exe es el penultimo o antepenultimo
        exe = None
        for campo in partes:
            if campo.startswith("/"):
                exe = campo
        if not exe:
            continue
        nombre = _programa_amigable(exe)
        cuando = " ".join(partes[0:4])
        agrupado.setdefault(nombre, {"nombre": nombre, "veces": 0, "ultima": cuando})
        agrupado[nombre]["veces"] += 1
        agrupado[nombre]["ultima"] = cuando
    return list(agrupado.values())


def _quedo_sin_memoria(dias=3):
    try:
        out = subprocess.run(
            ["journalctl", "-p", "4", f"--since=-{dias}days", "--no-pager",
             "-g", "Out of memory|oom-kill|Killed process"],
            capture_output=True, text=True, timeout=20).stdout
        return len([l for l in out.splitlines() if "Killed process" in l or "Out of memory" in l])
    except Exception:
        return 0


def _errores_disco_recientes(dias=3):
    """OJO: 'ata1: failed stop FIS RX' y 'SATA link down' son ruido
    inofensivo de un puerto SATA fantasma en varios portatiles (sin disco
    fisico ahi, todo NVMe) — sale en CADA suspension/despertar y no es un
    problema real. Se excluye a proposito para no dar una falsa alarma de
    'tu disco esta fallando' que no tiene nada que ver con el disco real."""
    try:
        out = subprocess.run(
            ["journalctl", "-p", "3", f"--since=-{dias}days", "--no-pager",
             "-g", "I/O error|ata[0-9]+.*(error|failed)|corrupt"],
            capture_output=True, text=True, timeout=20).stdout
        lineas = [l for l in out.splitlines() if l.strip() and not l.startswith("--")]
        lineas = [l for l in lineas if "failed stop FIS RX" not in l and "SATA link down" not in l]
        return len(lineas)
    except Exception:
        return 0


def registro_problemas(dias=3):
    """Version 'para cavernicolas' del log del sistema. Cada item ya
    viene en frases hechas por el llamador (i18n), esto solo junta los
    datos y clasifica severidad."""
    items = []

    for c in _crashes_recientes(dias):
        items.append({
            "tipo": "crash", "severidad": "amarillo",
            "programa": c["nombre"], "veces": c["veces"], "cuando": c["ultima"],
        })

    for s in servicios_fallidos():
        items.append({"tipo": "service", "severidad": "amarillo", "programa": s})

    n_oom = _quedo_sin_memoria(dias)
    if n_oom:
        items.append({"tipo": "oom", "severidad": "rojo", "veces": n_oom})

    n_disco = _errores_disco_recientes(dias)
    if n_disco:
        items.append({"tipo": "disk", "severidad": "rojo", "veces": n_disco})

    orden = {"rojo": 0, "amarillo": 1}
    items.sort(key=lambda x: orden.get(x["severidad"], 2))
    return items


# ====================================================================
#  SALUD DEL DISCO (SMART + errores del sistema de archivos)
# ====================================================================

def _disco_principal():
    """El disco donde vive la raíz del sistema, p.ej. /dev/nvme0n1."""
    try:
        out = subprocess.run(["findmnt", "-no", "SOURCE", "/"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        part = out.split("[")[0].strip()
        base = os.path.basename(part)
        m = re.match(r"^(nvme\d+n\d+|mmcblk\d+)p?\d*$", base)
        if m:
            return "/dev/" + m.group(1)
        m = re.match(r"^(sd[a-z]+|hd[a-z]+)\d*$", base)
        if m:
            return "/dev/" + m.group(1)
    except Exception:
        pass
    return None


def errores_filesystem():
    """Contadores de error de Btrfs. Se leen sin permisos de administrador."""
    try:
        out = subprocess.run(["btrfs", "device", "stats", "/"],
                             capture_output=True, text=True, timeout=15).stdout
        total = 0
        detalle = {}
        for linea in out.splitlines():
            m = re.search(r"\.(\w+)\s+(\d+)$", linea.strip())
            if m:
                tipo, valor = m.group(1), int(m.group(2))
                detalle[tipo] = detalle.get(tipo, 0) + valor
                total += valor
        return {"total": total, "detalle": detalle, "tipo": "btrfs"}
    except Exception:
        return None


def smart():
    """Estado SMART del disco. Usa el ayudante, así que con la política
    instalada no pide contraseña."""
    dev = _disco_principal()
    if not dev:
        return None
    try:
        p = subprocess.run(["pkexec", AYUDANTE, "smart", dev],
                           capture_output=True, text=True, timeout=60)
        if not p.stdout.strip():
            return None
        import json
        d = json.loads(p.stdout)
    except Exception:
        return None

    salud = d.get("smart_status", {}).get("passed")
    res = {
        "dispositivo": dev,
        "modelo": d.get("model_name"),
        "aprobado": salud,
        "desgaste": None,
        "repuesto": None,
        "temp": None,
        "horas": None,
        "errores": None,
        "aviso_critico": None,
    }
    nv = d.get("nvme_smart_health_information_log")
    if nv:
        res["desgaste"] = nv.get("percentage_used")
        res["repuesto"] = nv.get("available_spare")
        res["temp"] = nv.get("temperature")
        res["horas"] = nv.get("power_on_hours")
        res["errores"] = nv.get("media_errors")
        res["aviso_critico"] = nv.get("critical_warning")
    else:
        res["horas"] = (d.get("power_on_time") or {}).get("hours")
        res["temp"] = (d.get("temperature") or {}).get("current")
        for a in (d.get("ata_smart_attributes", {}) or {}).get("table", []) or []:
            if a.get("name") in ("Percentage_Used_Endurance_Indicator", "Wear_Leveling_Count"):
                res["desgaste"] = a.get("value")
            if a.get("name") == "Reallocated_Sector_Ct":
                res["errores"] = (a.get("raw") or {}).get("value")
    return res


def fmt_uptime(segundos, idioma="es"):
    dias = int(segundos // 86400)
    horas = int((segundos % 86400) // 3600)
    mins = int((segundos % 3600) // 60)
    if idioma == "es":
        if dias:
            return f"{dias} día{'s' if dias != 1 else ''}, {horas} h"
        return f"{horas} h {mins} min" if horas else f"{mins} min"
    if dias:
        return f"{dias} day{'s' if dias != 1 else ''}, {horas} h"
    return f"{horas} h {mins} min" if horas else f"{mins} min"
