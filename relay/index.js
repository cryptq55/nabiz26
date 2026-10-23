// Haber masası için aktarıcı: GET /?url=<adres>. Yalnızca listedeki kurum sitelerine izin verir.
// İstek, Türkiye'ye yakın bir veri merkezine sabitlenen bir Durable Object üzerinden yapılır: bazı kurum
// siteleri yurt dışı IP'lerini engelliyor, aktarıcı ise çağrıldığı yere yakın merkezde çalışırdı.
const ALLOWED = new Set(["www.eskisehir.bel.tr", "eskisehir.bel.tr", "www.beylikova.bel.tr", "beylikova.bel.tr"]);
const UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36";

export class Fetcher {
  constructor(state) { this.state = state; }
  async fetch(request) {
    const u = new URL(request.url);
    if (u.pathname === "/sayac") {  // günlük görsel sayacı (kötüye kullanıma karşı sınır)
      const day = new Date().toISOString().slice(0, 10);
      const n = ((await this.state.storage.get(day)) || 0) + 1;
      await this.state.storage.put(day, n);
      return new Response(String(n));
    }
    const target = u.searchParams.get("url");
    if (target === "trace") return fetch("https://www.cloudflare.com/cdn-cgi/trace");  // hangi merkezde çalışıyor
    const res = await fetch(target, { headers: { "User-Agent": UA, "Accept-Language": "tr-TR,tr;q=0.9" }, redirect: "follow" });
    return new Response(res.body, { status: res.status, headers: {
      "Content-Type": res.headers.get("Content-Type") || "application/octet-stream" } });
  }
}

// Temsilî haber görseli: resmî fotoğrafı olmayan haberler için. Llama sahneyi tarif eder, FLUX fotoğrafı üretir.
// Gerçek kişi, yüz, yazı ve logo istenmez; site görselin altına "Temsilî görsel (yapay zekâ)" yazar.
const DAILY_IMAGES = 250;

async function gorsel(request, env) {
  const { title = "", spot = "", category = "", district = "" } = await request.json();
  if (!title || title.length > 300) return new Response("başlık gerekli", { status: 400 });
  const counter = env.FETCHER.get(env.FETCHER.idFromName("sayac"));
  const n = Number(await (await counter.fetch("https://do/sayac")).text());
  if (n > DAILY_IMAGES) return new Response("günlük görsel sınırı doldu", { status: 429 });
  const brief = await env.AI.run("@cf/meta/llama-3.1-8b-instruct-fast", {  // hafif model: kota daha çok görsele yetsin
    messages: [
      { role: "system", content: "You write prompts for an image model. Reply with ONE English prompt only (max 70 words), no quotes, no preface." },
      { role: "user", content:
        "Write a prompt for a realistic editorial news photograph that illustrates this local news story from Eskişehir, Turkey.\n" +
        "Rules: show a generic, plausible scene (places, buildings, streets, vehicles, objects, nature, crowds seen from behind or far away). " +
        "No identifiable faces, no real or named people, no politicians, no readable text, signs, logos or flags. " +
        "Everything must look like Turkey: Turkish streets and architecture, Turkish police cars (white with blue stripes), Turkish license plates " +
        "without readable characters. Documentary photojournalism style, natural light, 35mm, high detail. If the story is about politics or government, show a generic Turkish " +
        "building exterior, an empty meeting hall or a podium without people.\n\n" +
        `Category: ${category}\nPlace: ${district}\nHeadline (Turkish): ${title}\nSummary (Turkish): ${spot}` },
    ],
    max_tokens: 160,
  });
  const prompt = (brief.response || "").trim().replace(/^"|"$/g, "") ||
    `Realistic editorial photograph of a street scene in Eskişehir, Turkey, natural light, no people, no text`;
  const img = await env.AI.run("@cf/black-forest-labs/flux-1-schnell", { prompt, steps: 4 });
  const bytes = Uint8Array.from(atob(img.image), (c) => c.charCodeAt(0));
  return new Response(bytes, { headers: { "Content-Type": "image/jpeg", "X-Prompt": encodeURIComponent(prompt.slice(0, 500)) } });
}

export default {
  async fetch(request, env, ctx) {
    if (new URL(request.url).pathname === "/gorsel" && request.method === "POST") return gorsel(request, env);
    if (request.method !== "GET") return new Response("yalnızca GET", { status: 405 });
    const params = new URL(request.url).searchParams;
    const hint = params.get("hint") || "eeur";
    if (params.get("url") === "trace") {
      const stub = env.FETCHER.get(env.FETCHER.idFromName(hint), { locationHint: hint });
      return stub.fetch("https://do/?url=trace");
    }
    let url;
    try { url = new URL(params.get("url")); } catch { return new Response("geçersiz adres", { status: 400 }); }
    if (!["https:", "http:"].includes(url.protocol) || !ALLOWED.has(url.hostname)) return new Response("izin verilmeyen site", { status: 403 });

    const cache = caches.default;
    const key = new Request(url.toString());
    const hit = await cache.match(key);
    if (hit) return hit;
    const stub = env.FETCHER.get(env.FETCHER.idFromName(hint), { locationHint: hint });
    const res = await stub.fetch("https://do/?url=" + encodeURIComponent(url.toString()));
    const out = new Response(res.body, { status: res.status, headers: {
      "Content-Type": res.headers.get("Content-Type") || "application/octet-stream", "Cache-Control": "public, max-age=600" } });
    if (res.ok) ctx.waitUntil(cache.put(key, out.clone()));
    return out;
  },
};
