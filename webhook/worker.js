// Webhook de Telegram en un Worker de Cloudflare (gratis).
//
// ¿Para qué? GitHub Actions no puede estar "escuchando" a Telegram. Este
// pequeño programa sí: vive en Cloudflare y Telegram le avisa (webhook) en
// cuanto pulsas un botón o escribes al bot. Él hace dos cosas:
//   1. Te contesta al momento ("⏳ Preparando la carta...").
//   2. Le pide a GitHub que lance el workflow que toca (repository_dispatch),
//      pasándole tu mensaje. GitHub tarda unos segundos en arrancar.
//
//   Telegram ──► worker (Cloudflare) ──► GitHub Actions ──► Telegram
//
// Lo que entiende:
//   - Botones Sí/No de las ofertas   → workflow "Leer respuestas de Telegram"
//   - Un PDF (tu CV)                 → lo mismo: lo guarda como tu CV
//   - /buscar                        → workflow "Actualizar ofertas"
//   - /ayuda                         → te contesta él mismo
//
// Variables que hay que poner en Cloudflare (Settings → Variables and Secrets):
//   TELEGRAM_TOKEN    el token del bot                         (tipo Secret)
//   TELEGRAM_CHAT_ID  tu chat id                               (tipo Text)
//   TELEGRAM_SECRET   una contraseña que inventas tú           (tipo Secret)
//   GITHUB_TOKEN      token de GitHub con permiso Contents: Read and write
//                     solo en este repo                        (tipo Secret)
//   REPO              samujimlop/buscador-practicas            (tipo Text)

const AYUDA = [
  "Esto es lo que sé hacer:",
  "/buscar — buscar ofertas ahora (tarda unos minutos)",
  "✅ / ❌ en una oferta — preparo la carta o la descarto",
  "Mándame un PDF — lo guardo como tu CV",
].join("\n");

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("Webhook del buscador de prácticas: funcionando.");
    }

    // Seguridad 1: Telegram manda en esta cabecera la contraseña que le dimos
    // al configurar el webhook. Si no coincide, la petición no viene de Telegram.
    if (request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.TELEGRAM_SECRET) {
      return new Response("No autorizado", { status: 403 });
    }

    const update = await request.json();
    const mensaje = update.message;
    const clic = update.callback_query;
    const chat = mensaje?.chat?.id ?? clic?.message?.chat?.id;

    // Seguridad 2: cualquiera puede escribir a un bot. Solo hacemos caso a tu chat.
    if (String(chat) !== String(env.TELEGRAM_CHAT_ID)) {
      return new Response("ok");
    }

    if (clic) {
      const siOno = (clic.data || "").startsWith("si:");
      await telegram(env, "answerCallbackQuery", {
        callback_query_id: clic.id,
        text: siOno ? "⏳ Preparando la carta, te llega en 1-2 minutos" : "Descartada",
      });
      await lanzar(env, chat, "telegram", update);
    } else if (mensaje?.document?.mime_type === "application/pdf") {
      await telegram(env, "sendMessage", { chat_id: chat, text: "📎 Recibido, guardando tu CV..." });
      await lanzar(env, chat, "telegram", update);
    } else if ((mensaje?.text || "").startsWith("/buscar")) {
      await telegram(env, "sendMessage", { chat_id: chat, text: "🔎 Buscando ofertas... te aviso en unos minutos." });
      await lanzar(env, chat, "buscar", {});
    } else if (mensaje?.text) {
      await telegram(env, "sendMessage", { chat_id: chat, text: AYUDA });
    }

    // Siempre contestamos 200 a Telegram; si no, nos reenviaría el mensaje.
    return new Response("ok");
  },
};

// Pide a GitHub que lance los workflows que escuchan `repository_dispatch`
// con este tipo de evento. Lo que va en client_payload le llega al workflow.
async function lanzar(env, chat, tipo, update) {
  const respuesta = await fetch(`https://api.github.com/repos/${env.REPO}/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "buscador-practicas-webhook",
    },
    body: JSON.stringify({ event_type: tipo, client_payload: { update } }),
  });
  if (!respuesta.ok) {
    // Nunca mostramos el token: solo el código de error.
    // 401/403 suele ser el GITHUB_TOKEN (caducado o sin permiso Contents: write).
    await telegram(env, "sendMessage", {
      chat_id: chat,
      text: `⚠️ No he podido avisar a GitHub (error ${respuesta.status}). Revisa el GITHUB_TOKEN del worker.`,
    });
  }
}

async function telegram(env, metodo, parametros) {
  await fetch(`https://api.telegram.org/bot${env.TELEGRAM_TOKEN}/${metodo}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(parametros),
  });
}
