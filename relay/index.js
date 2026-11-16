// Haber masası için aktarıcı: GET /?url=<adres>. Yalnızca listedeki kurum sitelerine izin verir.
// İstek, Türkiye'ye yakın bir veri merkezine sabitlenen bir Durable Object üzerinden yapılır: bazı kurum
// siteleri yurt dışı IP'lerini engelliyor, aktarıcı ise çağrıldığı yere yakın merkezde çalışırdı.
const ALLOWED = new Set(["www.eskisehir.bel.tr", "eskisehir.bel.tr", "www.beylikova.bel.tr", "beylikova.bel.tr"]);
const UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36";

export class Fetcher {
  constructor(state) { this.state = state; }
  async fetch(request) {
    const u = new URL(request.url);
    const target = u.searchParams.get("url");
    if (target === "trace") return fetch("https://www.cloudflare.com/cdn-cgi/trace");  // hangi merkezde çalışıyor
    const res = await fetch(target, { headers: { "User-Agent": UA, "Accept-Language": "tr-TR,tr;q=0.9" }, redirect: "follow" });
    return new Response(res.body, { status: res.status, headers: {
      "Content-Type": res.headers.get("Content-Type") || "application/octet-stream" } });
  }
}

export default {
  async fetch(request, env, ctx) {
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
