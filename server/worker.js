/**
 * Servidor de verificacion de donaciones de SOul (Vezzu Studio).
 *
 * Corre como un Cloudflare Worker (gratis, hasta 100.000 peticiones/dia).
 * No guarda nombres, correos ni montos: solo el codigo y si se vio en un
 * pago real de Ko-fi. Es lo minimo necesario para responder una sola
 * pregunta: "¿este codigo ya aparecio en una donacion real?".
 *
 * Requiere un KV namespace llamado CODIGOS, enlazado a este Worker desde
 * el panel de Cloudflare (ver server/README.md para los pasos).
 *
 * Variable secreta requerida: KOFI_TOKEN — el "Verification Token" que
 * Ko-fi muestra en ko-fi.com/manage/webhooks. Se configura como Secret
 * en el Worker, nunca queda escrito en este archivo.
 */

// alfabeto sin caracteres ambiguos (sin 0/O, 1/I/L): mas facil de leer
// y de escribir bien a mano en el mensaje de Ko-fi
const CLASE = "23456789ABCDEFGHJKMNPQRSTUVWXYZ";
// para ENCONTRAR el codigo dentro de un mensaje mas largo (sin anclas)
const PATRON_BUSCAR = new RegExp(`SOUL-[${CLASE}]{8}`);
// para VALIDAR que un codigo suelto tenga el formato exacto (con anclas)
const PATRON_EXACTO = new RegExp(`^SOUL-[${CLASE}]{8}$`);

const LIMITE_INTENTOS_POR_HORA = 20;

function cors(resp) {
  resp.headers.set("Access-Control-Allow-Origin", "*");
  resp.headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  resp.headers.set("Access-Control-Allow-Headers", "Content-Type");
  return resp;
}

async function manejarWebhookKofi(request, env) {
  // Ko-fi manda application/x-www-form-urlencoded con un campo "data"
  // que contiene el JSON real como texto.
  const form = await request.formData();
  const crudo = form.get("data");
  if (!crudo) return new Response("sin datos", { status: 400 });

  let datos;
  try {
    datos = JSON.parse(crudo);
  } catch (e) {
    return new Response("json invalido", { status: 400 });
  }

  // se verifica que el aviso venga de verdad de Ko-fi, no de cualquiera
  if (!env.KOFI_TOKEN || datos.verification_token !== env.KOFI_TOKEN) {
    return new Response("token invalido", { status: 401 });
  }

  const mensaje = (datos.message || "") + " " + (datos.from_name || "");
  const match = mensaje.toUpperCase().match(PATRON_BUSCAR);
  if (!match) {
    // pago real, pero sin codigo de SOul en el mensaje: no hay nada que
    // conectar con ninguna instalacion. Se ignora, no es un error.
    return new Response("ok, sin codigo", { status: 200 });
  }

  const codigo = match[0];
  await env.CODIGOS.put(codigo, JSON.stringify({
    donado: true,
    cuando: datos.timestamp || new Date().toISOString(),
  }));

  return new Response("ok", { status: 200 });
}

async function limiteSuperado(request, env) {
  // limite simple por IP, para frenar adivinar codigos a fuerza bruta
  const ip = request.headers.get("CF-Connecting-IP") || "desconocida";
  const clave = `_intentos:${ip}`;
  const actual = parseInt((await env.CODIGOS.get(clave)) || "0", 10);
  if (actual >= LIMITE_INTENTOS_POR_HORA) return true;
  await env.CODIGOS.put(clave, String(actual + 1), { expirationTtl: 3600 });
  return false;
}

async function manejarVerificar(request, env) {
  if (await limiteSuperado(request, env)) {
    return cors(Response.json({ donado: false, error: "demasiados intentos, espera" }, { status: 429 }));
  }
  const url = new URL(request.url);
  const codigo = (url.searchParams.get("codigo") || "").toUpperCase().trim();
  if (!PATRON_EXACTO.test(codigo)) {
    return cors(Response.json({ donado: false, error: "codigo invalido" }, { status: 400 }));
  }
  const valor = await env.CODIGOS.get(codigo);
  if (!valor) return cors(Response.json({ donado: false }));
  const datos = JSON.parse(valor);
  return cors(Response.json({ donado: true, cuando: datos.cuando }));
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return cors(new Response(null, { status: 204 }));
    }

    if (url.pathname === "/webhook" && request.method === "POST") {
      return manejarWebhookKofi(request, env);
    }

    if (url.pathname === "/verificar" && request.method === "GET") {
      return manejarVerificar(request, env);
    }

    return new Response("SOul donation verifier — Vezzu Studio", { status: 200 });
  },
};
