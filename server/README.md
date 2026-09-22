# Servidor de verificación de donaciones — SOul

Confirma que un código de donación apareció de verdad en un pago de
Ko-fi, sin guardar nombres, correos ni montos. Corre gratis en
Cloudflare Workers (hasta 100.000 peticiones al día sin costo).

## Qué vas a necesitar

- Una cuenta de Cloudflare (gratis): https://dash.cloudflare.com/sign-up
- Tu cuenta de Ko-fi ya creada: https://ko-fi.com

## Paso 1 — Instalar la herramienta de Cloudflare

En una terminal, dentro de esta carpeta (`server/`):

```bash
npm install -g wrangler
wrangler login
```

Esto abre tu navegador para que autorices la CLI con tu cuenta de
Cloudflare. Es un login normal, no hace falta tarjeta ni pagar nada.

## Paso 2 — Crear el almacén de códigos (KV)

```bash
wrangler kv namespace create CODIGOS
```

Te va a devolver algo como:

```
[[kv_namespaces]]
binding = "CODIGOS"
id = "a1b2c3d4e5f6..."
```

Copia ese `id` y pégalo en `wrangler.toml`, reemplazando
`PON_AQUI_EL_ID_QUE_TE_DE_WRANGLER`.

## Paso 3 — Obtener el token de verificación de Ko-fi

1. Entra a https://ko-fi.com/manage/webhooks
2. En la parte de abajo vas a ver un **Verification Token** — cópialo
   (es una cadena larga, no lo compartas con nadie, es como una
   contraseña).

## Paso 4 — Configurar el token como secreto en el Worker

```bash
wrangler secret put KOFI_TOKEN
```

Te va a pedir que pegues el token que copiaste en el paso 3. Queda
guardado cifrado en Cloudflare, nunca en este repositorio.

## Paso 5 — Publicar el Worker

```bash
wrangler deploy
```

Al terminar te da una URL parecida a:

```
https://soul-donaciones.<tu-usuario>.workers.dev
```

## Paso 6 — Conectar Ko-fi con tu Worker

1. Vuelve a https://ko-fi.com/manage/webhooks
2. En "Webhook URL" pon: `https://soul-donaciones.<tu-usuario>.workers.dev/webhook`
3. Guarda. Ko-fi tiene un botón para mandar un pago de prueba — úsalo
   para confirmar que responde `200 OK`.

## Paso 7 — Apuntar SOul a tu Worker

Si tu subdominio de Workers termina siendo distinto a
`soul-donaciones.vezzulab.workers.dev` (el que asume el código), edita
`soul/core.py`:

```python
SERVIDOR_DONACION = "https://soul-donaciones.<tu-usuario>.workers.dev"
```

## Probarlo de punta a punta

1. Abre SOul. Copia el código que te muestra (`SOUL-XXXXXXXX`).
2. Haz una donación real de prueba en tu propia página de Ko-fi (puede
   ser del monto mínimo), pegando ese código en el mensaje.
3. Espera un minuto y pulsa "Ya doné, verificar" en SOul.
4. Debería confirmar. Revisa los logs del Worker si no:
   ```bash
   wrangler tail
   ```

## Qué guarda el servidor y qué no

Guarda únicamente, por código: si se vio en un pago (`true`/`false`) y
cuándo. Nunca nombre, correo, mensaje completo ni monto — no hace falta
para responder la única pregunta que este servidor contesta.

## Límite honesto

Este servidor confirma que un pago real ocurrió con ese código en el
mensaje. No puede impedir que alguien edite el archivo local de SOul
para marcarse como donante sin pagar — eso es cierto para cualquier
programa de código abierto que corre en la máquina de cada quien. Lo
que sí logra es que la opción fácil (un botón que miente gratis) ya no
exista: la única forma de que el aviso desaparezca es un pago real, o
editar el código fuente a mano.
