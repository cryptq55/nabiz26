// Haber masası için aktarıcı: GET /?url=<adres>. Yalnızca listedeki kurum sitelerine izin verir.
const ALLOWED = new Set(["www.eskisehir.bel.tr", "eskisehir.bel.tr", "www.beylikova.bel.tr", "beylikova.bel.tr"]);

export default {
  async fetch(request, env, ctx) {
    if (request.method !== "GET") return new Response("yalnızca GET", { status: 405 });
    const target = new URL(request.url).searchParams.get("url");
    let url;
    try { url = new URL(target); } catch { return new Response("geçersiz adres", { status: 400 }); }
    if (url.protocol !== "https:" && url.protocol !== "http:") return new Response("geçersiz adres", { status: 400 });
    if (!ALLOWED.has(url.hostname)) return new Response("izin verilmeyen site", { status: 403 });

    const cache = caches.default;
    const key = new Request(url.toString());
    const hit = await cache.match(key);
    if (hit) return hit;

    const res = await fetch(url.toString(), {
      headers: { "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36",
                 "Accept-Language": "tr-TR,tr;q=0.9" },
      redirect: "follow",
    });
    const out = new Response(res.body, { status: res.status, headers: {
      "Content-Type": res.headers.get("Content-Type") || "application/octet-stream",
      "Cache-Control": "public, max-age=600",
    } });
    if (res.ok) ctx.waitUntil(cache.put(key, out.clone()));
    return out;
  },
};
