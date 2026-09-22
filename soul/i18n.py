"""Traducciones / Translations. Español e inglés, sin dependencias externas."""
import locale
import os

_IDIOMA = None
_ARCHIVO_IDIOMA = os.path.join(os.path.expanduser("~"), ".local", "share", "soul", "idioma")

STRINGS = {
    # --- general ---
    "app.name": ("SOul", "SOul"),
    "app.subtitle": ("Cuidado completo para tu Linux", "Complete care for your Linux"),

    # --- navegación ---
    "nav.smart": ("Escaneo inteligente", "Smart Scan"),
    "nav.cleanup": ("Limpieza", "Cleanup"),
    "nav.processes": ("Procesos en vivo", "Live Processes"),
    "nav.performance": ("Rendimiento", "Performance"),
    "nav.apps": ("Aplicaciones", "Applications"),
    "nav.privacy": ("Privacidad", "Privacy"),
    "nav.space": ("Mapa de espacio", "Space Lens"),
    "nav.health": ("Salud del equipo", "Health"),
    "nav.logs": ("Registro de problemas", "Problem log"),
    "nav.settings": ("Ajustes", "Settings"),

    # --- smart scan ---
    "smart.title": ("Escaneo inteligente", "Smart Scan"),
    "smart.desc": (
        "Un solo botón revisa todo: basura acumulada, rendimiento y privacidad.",
        "One button checks everything: accumulated junk, performance and privacy.",
    ),
    "smart.button": ("Escanear", "Scan"),
    "smart.scanning": ("Revisando tu sistema…", "Checking your system…"),
    "smart.done": ("Escaneo terminado", "Scan complete"),
    "smart.found": ("Encontré {size} para liberar", "Found {size} to free up"),
    "smart.nothing": ("Todo limpio, no hay nada que hacer", "All clean, nothing to do"),
    "smart.run": ("Limpiar todo", "Clean all"),
    "smart.cleaning": ("Limpiando…", "Cleaning…"),
    "smart.cleaned": ("Liberado: {size}", "Freed: {size}"),

    # --- limpieza ---
    "cleanup.title": ("Limpieza", "Cleanup"),
    "cleanup.desc": (
        "Archivos que se acumulan solos y no necesitas. Nada de esto son tus documentos ni tus fotos.",
        "Files that pile up on their own and you don't need. None of this is your documents or photos.",
    ),
    "cleanup.cache": ("Caché de aplicaciones", "Application cache"),
    "cleanup.cache.desc": (
        "Archivos temporales que las apps regeneran solas. Borrarlos no rompe nada.",
        "Temporary files apps regenerate on their own. Deleting them breaks nothing.",
    ),
    "cleanup.thumbs": ("Miniaturas de imágenes", "Image thumbnails"),
    "cleanup.thumbs.desc": (
        "Vistas previas de tus fotos y videos. Se vuelven a crear al abrir las carpetas.",
        "Previews of your photos and videos. They get recreated when you open folders.",
    ),
    "cleanup.trash": ("Papelera", "Trash"),
    "cleanup.trash.desc": (
        "Lo que ya borraste. Vaciarla lo elimina para siempre.",
        "What you already deleted. Emptying it removes it forever.",
    ),
    "cleanup.packages": ("Paquetes descargados", "Downloaded packages"),
    "cleanup.packages.desc": (
        "Copias de instalación ya usadas. No borra ningún programa instalado.",
        "Already-used install copies. It doesn't remove any installed program.",
    ),
    "cleanup.logs": ("Registros del sistema", "System logs"),
    "cleanup.logs.desc": (
        "Historial técnico interno. Se conservan las últimas 2 semanas.",
        "Internal technical history. The last 2 weeks are kept.",
    ),
    "cleanup.flatpak": ("Piezas de apps sin usar", "Unused app runtimes"),
    "cleanup.flatpak.desc": (
        "Componentes que ninguna app usa. Se vuelven a bajar solos si hacen falta.",
        "Components no app uses. They download again by themselves if needed.",
    ),

    "cleanup.fpcache": ("Caché de apps Flatpak", "Flatpak app cache"),
    "cleanup.fpcache.desc": (
        "Cada app Flatpak guarda su propia caché aparte. Se regenera sola.",
        "Each Flatpak app keeps its own separate cache. It regenerates by itself.",
    ),
    "cleanup.coredumps": ("Volcados de fallos", "Crash dumps"),
    "cleanup.coredumps.desc": (
        "Fotos internas de programas que se cerraron mal. Solo sirven para "
        "reportar errores a los desarrolladores.",
        "Internal snapshots of programs that crashed. They're only useful for "
        "reporting bugs to developers.",
    ),
    "cleanup.devcache": ("Caché de herramientas de desarrollo", "Developer tool cache"),
    "cleanup.devcache.desc": (
        "Paquetes descargados por npm, pip, cargo y similares. Se vuelven a bajar solos.",
        "Packages downloaded by npm, pip, cargo and friends. They download again by themselves.",
    ),
    "cleanup.orphans": ("Paquetes que ya nadie usa", "Packages nobody uses"),
    "cleanup.orphans.desc": (
        "Se instalaron como dependencia de algo que ya quitaste. Revísalo antes: "
        "en algún caso raro puedes querer conservar uno.",
        "They were installed as a dependency of something you already removed. "
        "Check first: in rare cases you may want to keep one.",
    ),

    # --- procesos en vivo ---
    "proc.title": ("Procesos en vivo", "Live Processes"),
    "proc.desc": (
        "Aquí ves exactamente lo que está haciendo tu computadora ahora mismo, "
        "traducido a palabras normales. Esto reemplaza a htop.",
        "Here's exactly what your computer is doing right now, translated into "
        "plain words. This replaces htop.",
    ),
    "proc.search": ("Buscar un programa…", "Search a program…"),
    "proc.background": ("Proceso en segundo plano", "Background process"),
    "proc.background.desc": (
        "No es una app que abriste tú. Suele ser una pieza interna del sistema o de otra app.",
        "Not an app you opened. Usually an internal piece of the system or another app.",
    ),
    "proc.instances": ("{n} procesos", "{n} processes"),
    "proc.empty": ("No hay nada pesado corriendo ahora mismo.", "Nothing heavy running right now."),
    "proc.legend_app": ("Aplicación reconocida", "Recognized application"),
    "proc.legend_bg": ("Segundo plano", "Background"),

    # --- rendimiento ---
    "perf.title": ("Rendimiento", "Performance"),
    "perf.desc": (
        "Qué está consumiendo tu equipo ahora mismo y qué arranca solo al encender.",
        "What's consuming your machine right now and what starts up on boot.",
    ),
    "perf.hogs": ("Apps que más consumen", "Heaviest apps"),
    "perf.autostart": ("Arrancan solas al encender", "Starts automatically at boot"),
    "perf.autostart.desc": (
        "Programas que se abren solos. Desactivar los que no uses hace que encienda más rápido.",
        "Programs that open by themselves. Disabling unused ones makes boot faster.",
    ),
    "perf.failed": ("Servicios con problemas", "Failed services"),
    "perf.failed.desc": (
        "Piezas del sistema que fallaron al arrancar.",
        "System pieces that failed to start.",
    ),
    "perf.close": ("Cerrar", "Close"),
    "perf.disable": ("Desactivar", "Disable"),
    "perf.enable": ("Activar", "Enable"),
    "perf.none_failed": ("Ningún servicio falló. Todo bien.", "No service failed. All good."),
    "perf.none_autostart": ("Nada arranca solo.", "Nothing starts automatically."),

    # --- aplicaciones ---
    "apps.title": ("Aplicaciones", "Applications"),
    "apps.desc": (
        "Lo que tienes instalado, y las actualizaciones disponibles.",
        "What you have installed, and available updates.",
    ),
    "apps.installed": ("Instaladas", "Installed"),
    "apps.updates": ("Actualizaciones disponibles", "Available updates"),
    "apps.uninstall": ("Desinstalar", "Uninstall"),
    "apps.update_all": ("Actualizar todo", "Update all"),
    "apps.no_updates": ("Todo está al día.", "Everything is up to date."),
    "apps.checking": ("Buscando actualizaciones…", "Checking for updates…"),

    # --- privacidad ---
    "privacy.title": ("Privacidad", "Privacy"),
    "privacy.desc": (
        "Rastros que deja tu uso diario. Borrarlos cierra sesiones abiertas en el navegador.",
        "Traces left by daily use. Clearing them signs you out of open browser sessions.",
    ),
    "privacy.browser_cache": ("Caché del navegador", "Browser cache"),
    "privacy.browser_cache.desc": (
        "Páginas guardadas para cargar más rápido. Borrarlo no cierra tus sesiones.",
        "Pages saved to load faster. Clearing it won't sign you out.",
    ),
    "privacy.cookies": ("Cookies y sesiones", "Cookies and sessions"),
    "privacy.cookies.desc": (
        "Ojo: borrarlas te saca de las cuentas donde estés conectado.",
        "Careful: clearing them signs you out of accounts you're logged into.",
    ),
    "privacy.recent": ("Archivos recientes", "Recent files"),
    "privacy.recent.desc": (
        "La lista de lo que abriste últimamente. No borra los archivos.",
        "The list of what you opened lately. It doesn't delete the files.",
    ),
    "privacy.shell": ("Historial de comandos", "Command history"),
    "privacy.shell.desc": (
        "Lo que escribiste en la terminal.",
        "What you typed in the terminal.",
    ),

    # --- espacio ---
    "space.title": ("Mapa de espacio", "Space Lens"),
    "space.desc": (
        "Dónde se está yendo tu disco. Las carpetas más grandes, de mayor a menor.",
        "Where your disk is going. The biggest folders, largest first.",
    ),
    "space.scan": ("Analizar carpeta personal", "Scan home folder"),
    "space.scanning": ("Midiendo carpetas…", "Measuring folders…"),
    "space.big_files": ("Archivos más grandes", "Largest files"),
    "space.open": ("Abrir", "Open"),

    # --- salud ---
    "health.title": ("Salud del equipo", "Health"),
    "health.desc": (
        "El estado real de tu hardware.",
        "The real state of your hardware.",
    ),
    "health.memory": ("Memoria", "Memory"),
    "health.cpu": ("Procesador", "Processor"),
    "health.disk": ("Disco", "Disk"),
    "health.battery": ("Batería", "Battery"),
    "health.temp": ("Temperatura", "Temperature"),
    "health.uptime": ("Encendida desde hace", "Powered on for"),

    # --- frases de estado ---
    "state.all_good": ("Todo tranquilo.", "All calm."),
    "state.tight": ("Todo funciona, pero con poco margen.", "Everything works, but with little headroom."),
    "state.limit": ("Está al límite en algo, por eso se siente lenta.", "Something is maxed out, that's why it feels slow."),
    "mem.plenty": ("Tiene espacio de sobra.", "Plenty of room."),
    "mem.filling": ("Se está llenando. Si algo va lento, cierra una app que no uses.",
                    "Filling up. If something feels slow, close an app you're not using."),
    "mem.full": ("Está casi llena. Por eso se siente lenta ahora mismo.",
                 "Nearly full. That's why it feels slow right now."),
    "mem.swap": (" Ya está usando el disco como memoria de repuesto, que es más lento.",
                 " It's already using the disk as backup memory, which is slower."),
    "cpu.idle": ("Casi sin esfuerzo.", "Barely working."),
    "cpu.busy": ("Trabajando a buen ritmo.", "Working at a good pace."),
    "cpu.hard": ("Esforzándose bastante ahora mismo.", "Working quite hard right now."),
    "disk.plenty": ("Con bastante espacio libre ({free}).", "Plenty of free space ({free})."),
    "disk.shrinking": ("El espacio se está reduciendo ({free} libres).", "Space is shrinking ({free} free)."),
    "disk.full": ("Casi sin espacio libre ({free}).", "Almost no free space ({free})."),
    "bat.charging": ("Cargando, va en {pct}%.", "Charging, at {pct}%."),
    "bat.discharging": ("Le queda {pct}% de carga.", "{pct}% charge left."),
    "bat.health": ("La pila llega al {pct}% de su capacidad original.",
                   "The battery reaches {pct}% of its original capacity."),

    # --- acciones comunes ---
    "action.clean": ("Limpiar", "Clean"),
    "action.cleaning": ("Limpiando…", "Cleaning…"),
    "action.cancel": ("Cancelar", "Cancel"),
    "action.confirm": ("Confirmar", "Confirm"),
    "action.rescan": ("Volver a revisar", "Rescan"),
    "action.select_all": ("Seleccionar todo", "Select all"),
    "action.clean_selected": ("Limpiar seleccionado", "Clean selected"),
    "action.done": ("Listo", "Done"),
    "action.already_clean": ("ya está limpio", "already clean"),
    "action.calculating": ("calculando…", "calculating…"),
    "action.needs_password": (" Te va a pedir tu contraseña.", " It will ask for your password."),
    "action.cancelled": ("Cancelado.", "Cancelled."),
    "action.failed": ("No se pudo completar.", "Couldn't complete."),

    # --- diálogos ---
    "dialog.close_app": ("¿Cerrar {name}?", "Close {name}?"),
    "dialog.close_app.body": (
        "Se van a cerrar todas sus ventanas. Guarda lo que estés haciendo ahí antes de continuar.",
        "All its windows will close. Save what you're doing there before continuing.",
    ),
    "dialog.clean": ("¿Limpiar {name}?", "Clean {name}?"),

    # --- donacion ---
    "donate.title": ("¿Te está sirviendo SOul?", "Is SOul working for you?"),
    "donate.body": (
        "Es gratis y va a seguir siéndolo. Lo hace el equipo de Vezzu Studio, "
        "sin financiamiento — si te resolvió algo, considera apoyar el trabajo.",
        "It's free and will stay free. Made by the Vezzu Studio team, with no "
        "funding — if it solved something for you, consider supporting the work.",
    ),
    "donate.kofi": ("Apoyar en Ko-fi", "Support on Ko-fi"),
    "donate.later": ("Ahora no", "Not now"),
    "donate.check": ("Ya doné, verificar", "I donated, verify"),
    "donate.copy": ("Copiar código", "Copy code"),
    "donate.instructions": (
        "Pon este código en el mensaje de tu donación en Ko-fi. Así SOul "
        "sabe que fuiste tú y deja de preguntarte.",
        "Put this code in your donation message on Ko-fi. That way SOul "
        "knows it was you and stops asking.",
    ),
    "donate.copied": ("Código copiado.", "Code copied."),
    "donate.copied_and_open": ("Código copiado. Pégalo en el mensaje de tu donación.",
                               "Code copied. Paste it in your donation message."),
    "donate.paste_title": ("Ya está copiado — ahora pégalo aquí",
                           "It's already copied — now paste it here"),
    "donate.paste_body": (
        "Al pagar en Ko-fi vas a ver un cuadro de texto opcional para dejar "
        "un mensaje. Es ese cuadro, el que se parece a esto. Puedes escribir "
        "lo que quieras ahí además, con tal de que el código quede incluido:",
        "When you pay on Ko-fi you'll see an optional text box to leave a "
        "message. That's the one, it looks like this. You can write "
        "whatever else you like in there too, as long as the code is included:",
    ),
    "donate.mockup_label": ("Leave a message (optional)", "Leave a message (optional)"),
    "donate.warning": (
        "Si donas sin poner el código, SOul no va a poder saber que fuiste tú, "
        "y este aviso te va a seguir apareciendo cada vez que abras la app.",
        "If you donate without including the code, SOul won't be able to tell "
        "it was you, and this reminder will keep showing up every time you "
        "open the app.",
    ),
    "donate.understood": ("Entendido", "Got it"),
    "donate.checking": ("Revisando…", "Checking…"),
    "donate.confirmed": ("¡Confirmado! Gracias de verdad. No te lo vuelvo a preguntar.",
                         "Confirmed! Thank you, truly. I won't ask again."),
    "donate.not_found": ("Todavía no veo esa donación. Los pagos pueden tardar "
                         "unos minutos en llegar — inténtalo de nuevo en un rato.",
                         "I don't see that donation yet. Payments can take a "
                         "few minutes to arrive — try again in a bit."),

    # --- actualizaciones ---
    "update.title": ("Actualización disponible", "Update available"),
    "update.question": ("Hay una versión nueva: {version}", "There's a new version: {version}"),
    "update.current": ("Tienes la {current}", "You have {current}"),
    "update.notes": ("Qué trae esta versión", "What's new in this version"),
    "update.no_notes": ("Sin notas de esta versión.", "No notes for this version."),
    "update.later": ("Luego", "Later"),
    "update.skip": ("No avisar de esta versión", "Don't ask about this version"),
    "update.install": ("Actualizar", "Update"),
    "update.open_page": ("Ver en GitHub", "View on GitHub"),
    "update.downloading": ("Descargando la versión {version}…", "Downloading version {version}…"),
    "update.installed": ("Listo. Cierra y vuelve a abrir SOul para usar la nueva versión.",
                         "Done. Close and reopen SOul to use the new version."),
    "update.failed": ("No se pudo descargar la actualización. Inténtalo de nuevo más tarde.",
                      "Couldn't download the update. Try again later."),
    "update.checking": ("Buscando actualizaciones…", "Checking for updates…"),

    # --- settings ---
    "settings.title": ("Ajustes", "Settings"),
    "settings.desc": ("Cómo se comporta SOul, y de qué versión estás.",
                      "How SOul behaves, and which version you're on."),
    "settings.general": ("General", "General"),
    "settings.language": ("Idioma", "Language"),
    "settings.notifications": ("Notificaciones", "Notifications"),
    "settings.notifications.desc": (
        "Avisos del sistema, como cuando el procesador o la memoria "
        "llevan un rato al límite.",
        "System alerts, like when the processor or memory have been "
        "maxed out for a while.",
    ),
    "settings.autostart": ("Iniciar con el sistema", "Start with the system"),
    "settings.autostart.desc": (
        "Abre SOul solo al encender el equipo (minimizado en la bandeja).",
        "Opens SOul automatically on startup (minimized to the tray).",
    ),
    "settings.updates": ("Actualizaciones", "Updates"),
    "settings.auto_update": ("Buscar actualizaciones automáticamente",
                             "Check for updates automatically"),
    "settings.auto_update.desc": (
        "Al abrir SOul y cada 6 horas mientras sigue abierta. Se puede "
        "buscar a mano en cualquier momento, esté encendido o no.",
        "On startup and every 6 hours while it stays open. You can always "
        "check by hand below, whether this is on or off.",
    ),
    "settings.check_now": ("Buscar ahora", "Check now"),
    "settings.check_now.btn": ("Revisar", "Check"),
    "settings.current_version": ("Versión instalada:", "Installed version:"),
    "settings.no_update": ("Ya tienes la última versión.", "You're already on the latest version."),
    "settings.permissions": ("Permisos", "Permissions"),
    "settings.reset_permission": ("Permiso de administrador", "Administrator permission"),
    "settings.reset_permission.desc": (
        "Quita el permiso instalado. La próxima limpieza que lo necesite "
        "volverá a pedir la contraseña, como en la primera vez.",
        "Removes the installed permission. The next cleanup that needs it "
        "will ask for the password again, like the first time.",
    ),
    "settings.reset_permission.btn": ("Reiniciar permiso", "Reset permission"),
    "settings.reset_permission.confirm": (
        "¿Quitar el permiso instalado? Vas a tener que autorizarlo de "
        "nuevo la próxima vez que haga falta.",
        "Remove the installed permission? You'll have to authorize it "
        "again the next time it's needed.",
    ),
    "settings.reset_permission.done": ("Permiso reiniciado.", "Permission reset."),
    "settings.about": ("Acerca de", "About"),
    "settings.version": ("Versión", "Version"),
    "settings.license": ("Licencia", "License"),
    "settings.open": ("Abrir", "Open"),

    # --- onboarding / permisos ---
    "onboard.title": ("Un permiso, una sola vez", "One permission, just once"),
    "onboard.body": (
        "Algunas limpiezas (caché de paquetes, registros del sistema, volcados "
        "de fallos) necesitan permiso de administrador. Si lo autorizas ahora, "
        "SOul no te volverá a pedir la contraseña nunca más.\n\n"
        "El permiso solo cubre el ayudante de SOul, que no acepta comandos "
        "libres: únicamente esas tareas fijas de limpieza y leer el estado del "
        "disco. Y solo aplica a tu sesión abierta delante del equipo.",
        "Some cleanups (package cache, system logs, crash dumps) need admin "
        "permission. If you authorize it now, SOul will never ask for your "
        "password again.\n\n"
        "The permission covers only SOul's helper, which accepts no free-form "
        "commands: just those fixed cleanup tasks and reading disk health. And "
        "it only applies to your session in front of the machine.",
    ),
    "onboard.yes": ("Autorizar una vez", "Authorize once"),
    "onboard.later": ("Ahora no", "Not now"),
    "onboard.done": ("Listo, no te la pediré más.", "Done, I won't ask again."),
    "onboard.failed": ("No se pudo activar. Seguirá pidiendo la contraseña.",
                       "Couldn't enable it. It will keep asking for the password."),

    # --- disco / SMART ---
    "disk.health": ("Estado del disco", "Disk health"),
    "disk.checking": ("Revisando el disco…", "Checking the disk…"),
    "disk.good": ("El disco está sano.", "The disk is healthy."),
    "disk.bad": ("El disco reporta un problema. Haz una copia de seguridad ya.",
                 "The disk reports a problem. Back up your data now."),
    "disk.wear": ("Desgaste", "Wear"),
    "disk.wear.desc": ("{pct}% de su vida útil consumida.", "{pct}% of its lifespan used."),
    "disk.spare": ("Repuesto disponible", "Available spare"),
    "disk.hours": ("Horas encendido", "Power-on hours"),
    "disk.errors": ("Errores de lectura/escritura", "Read/write errors"),
    "disk.no_errors": ("Ninguno. El sistema de archivos no ha detectado fallos.",
                       "None. The filesystem hasn't detected any faults."),
    "disk.some_errors": ("{n} detectados. Conviene hacer copia de seguridad.",
                         "{n} detected. Making a backup is advisable."),
    "disk.unavailable": ("No se pudo leer el estado SMART de este disco.",
                         "Couldn't read this disk's SMART status."),

    # --- registro de problemas ---
    "log.title": ("Registro de problemas", "Problem log"),
    "log.desc": (
        "Lo mismo que revisaría un técnico, pero traducido. Si algo no se "
        "entiende del todo, mejor no se muestra que asustar sin motivo.",
        "The same thing a technician would check, translated. If something "
        "isn't fully understood, it's better left out than shown to scare "
        "you for nothing.",
    ),
    "log.empty": ("No se detectó ningún problema en los últimos 3 días.",
                  "No problems detected in the last 3 days."),
    "log.live": ("Actividad en vivo", "Live activity"),
    "log.live.desc": (
        "Lo último que registró el sistema, tal cual, sin traducir. "
        "Para cuando quieres ver el detalle real, no solo el resumen.",
        "The system's most recent entries, as-is, untranslated. "
        "For when you want the real detail, not just the summary.",
    ),
    "log.copy": ("Copiar reporte", "Copy report"),
    "log.copied": ("Reporte copiado. Pégalo donde lo necesites.",
                   "Report copied. Paste it wherever you need it."),
    "log.crash": ("{app} se cerró de golpe {veces} vez", "{app} crashed {veces} time"),
    "log.crash_pl": ("{app} se cerró de golpe {veces} veces", "{app} crashed {veces} times"),
    "log.crash.desc": (
        "Se cerró solo, sin que lo cerraras tú. Si vuelve a pasar seguido, "
        "puede valer la pena reinstalarlo.",
        "It closed on its own, without you closing it. If it keeps "
        "happening, reinstalling it might help.",
    ),
    "log.service": ("Un servicio no arrancó bien: {s}", "A service failed to start: {s}"),
    "log.service.desc": (
        "Una pieza interna del sistema. No suele afectar tu uso normal.",
        "An internal system piece. It usually doesn't affect normal use.",
    ),
    "log.oom": ("Se quedó sin memoria {veces} vez y tuvo que cerrar algo",
               "It ran out of memory {veces} time and had to close something"),
    "log.oom_pl": ("Se quedó sin memoria {veces} veces y tuvo que cerrar algo",
                  "It ran out of memory {veces} times and had to close something"),
    "log.oom.desc": (
        "Pasa cuando hay demasiadas apps abiertas a la vez. Ampliar la "
        "memoria RAM lo evitaría.",
        "Happens when too many apps are open at once. More RAM would prevent it.",
    ),
    "log.disk": ("El disco reportó {veces} error", "The disk reported {veces} error"),
    "log.disk_pl": ("El disco reportó {veces} errores", "The disk reported {veces} errors"),
    "log.disk.desc": (
        "Puede ser una señal de que el disco está fallando. Haz una copia de seguridad.",
        "Could be a sign the disk is failing. Back up your data.",
    ),

    # --- cerrar ventana ---
    "close.title": ("¿Cerrar SOul?", "Close SOul?"),
    "close.body": (
        "Puedes dejarla corriendo en la barra de tareas, junto al reloj, "
        "para abrirla rápido cuando la necesites.",
        "You can leave it running in the system tray, next to the clock, "
        "to open it quickly when you need it.",
    ),
    "close.tray": ("Dejar en la barra", "Keep in tray"),
    "close.quit": ("Cerrar del todo", "Quit completely"),
    "tray.quit": ("Salir", "Quit"),

    # --- notificaciones ---
    "notif.cpu.title": ("El procesador está al límite", "Your processor is maxed out"),
    "notif.cpu.body": ("Lleva un rato al {pct}%. Revisa Rendimiento para ver qué lo está usando.",
                       "It's been at {pct}% for a while. Check Performance to see what's using it."),
    "notif.mem.title": ("La memoria se está llenando", "Memory is filling up"),
    "notif.mem.body": ("Está al {pct}%. Revisa Rendimiento para cerrar algo que no uses.",
                       "It's at {pct}%. Check Performance to close something you're not using."),

    # --- seguridad ---
    "safe.note": (
        "SOul nunca toca tus documentos, fotos, música ni programas instalados.",
        "SOul never touches your documents, photos, music or installed programs.",
    ),
}


def detectar_idioma():
    """Lee el idioma del sistema. 'es' por defecto si es español, si no 'en'."""
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(var, "")
        if val:
            if val.lower().startswith("es"):
                return "es"
            if val.lower().startswith(("en", "c", "posix")):
                return "en"
    try:
        cod = locale.getlocale()[0] or ""
        if cod.lower().startswith("es"):
            return "es"
    except Exception:
        pass
    return "en"


def set_idioma(idioma, guardar=True):
    """Cambia el idioma. Si 'guardar' es True (la persona lo eligio a
    mano en la barra lateral), queda fijo para siempre, sin importar el
    idioma del sistema — alguien que no entiende un idioma no deberia
    tener que volver a cambiarlo cada vez que abre la app."""
    global _IDIOMA
    _IDIOMA = idioma if idioma in ("es", "en") else "en"
    if guardar:
        try:
            os.makedirs(os.path.dirname(_ARCHIVO_IDIOMA), exist_ok=True)
            with open(_ARCHIVO_IDIOMA, "w") as f:
                f.write(_IDIOMA)
        except OSError:
            pass


def _idioma_guardado():
    try:
        with open(_ARCHIVO_IDIOMA) as f:
            val = f.read().strip()
        return val if val in ("es", "en") else None
    except OSError:
        return None


def get_idioma():
    global _IDIOMA
    if _IDIOMA is None:
        # la eleccion manual de la persona pesa mas que el idioma del
        # sistema: si ya lo cambio una vez, se respeta siempre
        _IDIOMA = _idioma_guardado() or detectar_idioma()
    return _IDIOMA


def t(clave, **kwargs):
    """Traduce una clave al idioma activo."""
    par = STRINGS.get(clave)
    if par is None:
        return clave
    texto = par[0] if get_idioma() == "es" else par[1]
    if kwargs:
        try:
            return texto.format(**kwargs)
        except (KeyError, IndexError):
            return texto
    return texto
