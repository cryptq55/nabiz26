// www.nabiz26.com ve http:// isteklerini kalıcı (301) olarak https://nabiz26.com'a yönlendirir; Google aynı haberi
// iki adreste görmesin. Geri kalan her şey public/ içindeki statik dosyalardan sunulur.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.hostname === "www.nabiz26.com" || (url.protocol === "http:" && url.hostname === "nabiz26.com")) {
      url.hostname = "nabiz26.com";
      url.protocol = "https:";
      return Response.redirect(url.toString(), 301);
    }
    return env.ASSETS.fetch(request);
  },
};
