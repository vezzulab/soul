"""Buscar y aplicar actualizaciones de SOul contra los Releases de GitHub.

Privacidad: la comprobación es un único GET HTTPS a api.github.com al
arrancar y cada 6 horas mientras la app sigue abierta. Lo único que se
envía es el nombre y la versión del programa en el User-Agent.
"""
import hashlib
import json
import os
import re
import urllib.request

from . import __version__

HOME = os.path.expanduser("~")
API_ULTIMO = "https://api.github.com/repos/vezzulab/soul/releases/latest"
ARCHIVO_OMITIDA = os.path.join(HOME, ".local", "share", "soul", "version_omitida")
ARCHIVO_SIN_AUTO = os.path.join(HOME, ".local", "share", "soul", "sin_autoactualizar")
ARCHIVO_HASH_INSTALADO = os.path.join(HOME, ".local", "share", "soul", "sha256_instalado")
NOMBRE_ASSET = "SOul-x86_64.AppImage"


def autoactualizar_activado():
    return not os.path.isfile(ARCHIVO_SIN_AUTO)


def set_autoactualizar(activo):
    """Enciende o apaga la busqueda automatica de actualizaciones.
    Apagarlo no borra nada que ya se haya descargado, solo deja de
    preguntar al arrancar y cada 6 horas."""
    try:
        if activo:
            if os.path.isfile(ARCHIVO_SIN_AUTO):
                os.remove(ARCHIVO_SIN_AUTO)
        else:
            os.makedirs(os.path.dirname(ARCHIVO_SIN_AUTO), exist_ok=True)
            open(ARCHIVO_SIN_AUTO, "w").close()
    except OSError:
        pass


def version_actual():
    return __version__


def parsear_version(texto):
    """"v1.2.3" -> (1, 2, 3). None si no parece una version."""
    m = re.match(r"^\s*v?(\d+(?:\.\d+){0,3})", texto or "")
    if not m:
        return None
    return tuple(int(p) for p in m.group(1).split("."))


def es_mas_nueva(candidata, actual=None):
    actual = actual or __version__
    nueva, vieja = parsear_version(candidata), parsear_version(actual)
    if nueva is None or vieja is None:
        return False
    ancho = max(len(nueva), len(vieja))
    nueva += (0,) * (ancho - len(nueva))
    vieja += (0,) * (ancho - len(vieja))
    return nueva > vieja


def version_omitida():
    try:
        with open(ARCHIVO_OMITIDA) as f:
            return f.read().strip()
    except OSError:
        return ""


def omitir_version(clave):
    try:
        os.makedirs(os.path.dirname(ARCHIVO_OMITIDA), exist_ok=True)
        with open(ARCHIVO_OMITIDA, "w") as f:
            f.write(clave)
    except OSError:
        pass


def _sha256_archivo(ruta):
    """SHA-256 del archivo entero, leido en trozos para no cargarlo todo
    en memoria (el AppImage pesa unos 30MB)."""
    digest = hashlib.sha256()
    with open(ruta, "rb") as f:
        for trozo in iter(lambda: f.read(1 << 20), b""):
            digest.update(trozo)
    return digest.hexdigest()


def hash_instalado():
    """El sha256 de la version instalada ahora mismo. Es la fuente real
    de si hay algo nuevo — no un numero de version que hay que acordarse
    de subir cada vez: si se vuelve a publicar el mismo tag con un
    archivo distinto, esto igual lo detecta.

    Se calcula una sola vez (al primer arranque tras instalar) y se
    guarda; despues solo se actualiza cuando SOul se actualiza a si
    mismo. Si no corre como AppImage, no hay nada que hashear."""
    try:
        with open(ARCHIVO_HASH_INSTALADO) as f:
            guardado = f.read().strip()
            if guardado:
                return guardado
    except OSError:
        pass

    ruta = appimage_actual()
    if not ruta:
        return ""
    try:
        h = _sha256_archivo(ruta)
        os.makedirs(os.path.dirname(ARCHIVO_HASH_INSTALADO), exist_ok=True)
        with open(ARCHIVO_HASH_INSTALADO, "w") as f:
            f.write(h)
        return h
    except OSError:
        return ""


def _marcar_hash_instalado(h):
    try:
        os.makedirs(os.path.dirname(ARCHIVO_HASH_INSTALADO), exist_ok=True)
        with open(ARCHIVO_HASH_INSTALADO, "w") as f:
            f.write(h)
    except OSError:
        pass


def buscar_actualizacion():
    """Consulta el ultimo release. Se llama desde un hilo aparte: es red,
    no debe congelar la interfaz. None si no hay internet, no hay
    releases, o el archivo publicado es exactamente el que ya se tiene
    instalado (mismo sha256, sin importar el numero de version)."""
    try:
        req = urllib.request.Request(
            API_ULTIMO,
            headers={"Accept": "application/vnd.github+json",
                     "User-Agent": f"SOul/{__version__}"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            datos = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    if not isinstance(datos, dict) or datos.get("draft") or datos.get("prerelease"):
        return None
    tag = str(datos.get("tag_name") or "")
    version = parsear_version(tag)
    if version is None:
        return None

    url_asset = ""
    tamano_asset = 0
    sha_asset = ""
    for asset in datos.get("assets") or []:
        if asset.get("name") == NOMBRE_ASSET:
            url_asset = str(asset.get("browser_download_url") or "")
            tamano_asset = int(asset.get("size") or 0)
            digest = str(asset.get("digest") or "")
            if digest.startswith("sha256:"):
                sha_asset = digest[7:].lower()

    instalado = hash_instalado()
    # si tenemos ambos hashes y coinciden, es exactamente lo que ya hay
    # instalado: no hay nada que ofrecer, sin importar tags ni numeros
    if sha_asset and instalado and sha_asset == instalado:
        return None
    # sin hash de ninguno de los dos lados (p. ej. corriendo desde
    # codigo fuente), se cae al numero de version como antes
    if not sha_asset or not instalado:
        if not es_mas_nueva(".".join(map(str, version))):
            return None

    return {
        "version": ".".join(map(str, version)),
        "notas": str(datos.get("body") or "").strip(),
        "url_pagina": str(datos.get("html_url") or
                          "https://github.com/vezzulab/soul/releases"),
        "url_asset": url_asset,
        "tamano_asset": tamano_asset,
        "sha_asset": sha_asset,
    }


def appimage_actual():
    """Ruta del AppImage desde el que corre SOul ahora mismo, o None si
    no corre como AppImage (p. ej. desde el código fuente)."""
    ruta = os.environ.get("APPIMAGE")
    return ruta if ruta and os.path.isfile(ruta) else None


def puede_autoactualizarse():
    """¿SOul puede reemplazarse a si mismo? Solo si corre como AppImage
    y el archivo y su carpeta son escribibles por este usuario."""
    ruta = appimage_actual()
    if not ruta:
        return False
    return os.access(ruta, os.W_OK) and os.access(os.path.dirname(ruta), os.W_OK)


class DescargaCancelada(Exception):
    pass


def descargar_actualizacion(url_asset, progreso=None, cancelado=None):
    """Descarga el AppImage nuevo junto al actual (para que el reemplazo
    sea un simple renombrado) y devuelve la ruta temporal. progreso(pct)
    se llama con el porcentaje descargado, si se da. cancelado, si se
    da, es una funcion sin argumentos: si devuelve True en cualquier
    momento, se corta la descarga y se limpia el archivo parcial."""
    destino_final = appimage_actual()
    carpeta = os.path.dirname(destino_final)
    parcial = os.path.join(carpeta, ".SOul-actualizacion.part")

    req = urllib.request.Request(
        url_asset, headers={"User-Agent": f"SOul/{__version__}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            hecho = 0
            ultimo = -1
            with open(parcial, "wb") as out:
                while True:
                    if cancelado and cancelado():
                        raise DescargaCancelada()
                    trozo = resp.read(1 << 16)
                    if not trozo:
                        break
                    out.write(trozo)
                    hecho += len(trozo)
                    if progreso and total:
                        pct = int(hecho * 100 / total)
                        if pct != ultimo:
                            ultimo = pct
                            progreso(pct)
        os.chmod(parcial, 0o755)
        return parcial
    except BaseException:
        try:
            os.remove(parcial)
        except OSError:
            pass
        raise


def instalar_actualizacion(descargado):
    """Reemplaza el AppImage actual por el descargado. Un AppImage que ya
    esta corriendo se queda valido: mantiene abierto su inodo viejo, asi
    que esto no rompe la instancia que sigue abierta ahora mismo."""
    destino = appimage_actual()
    h = _sha256_archivo(descargado)
    os.replace(descargado, destino)
    _marcar_hash_instalado(h)
