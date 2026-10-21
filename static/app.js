// Nabız 26: küçük istemci özellikleri (göreli zaman, tema, hava durumu, arama)
(function () {
  // "12 dk önce" gibi göreli zaman
  function rel(iso) {
    var diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 0) return null;
    if (diff < 60) return "az önce";
    if (diff < 3600) return Math.floor(diff / 60) + " dk önce";
    if (diff < 86400) return Math.floor(diff / 3600) + " saat önce";
    if (diff < 172800) return "dün";
    return null;
  }
  function updateTimes() {
    document.querySelectorAll("time[data-rel]").forEach(function (el) {
      var r = rel(el.getAttribute("datetime"));
      if (r) { el.title = el.title || el.textContent; el.textContent = r; }
    });
  }
  updateTimes();
  setInterval(updateTimes, 60000);

  // Açık/koyu tema
  var btn = document.getElementById("theme-toggle");
  if (btn) btn.addEventListener("click", function () {
    var root = document.documentElement;
    var dark = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = dark ? "light" : "dark";
    try { localStorage.setItem("tema", root.dataset.theme); } catch (e) {}
  });

  // Bağlantı kopyala
  document.querySelectorAll("[data-copy]").forEach(function (b) {
    b.addEventListener("click", function () {
      navigator.clipboard && navigator.clipboard.writeText(location.href).then(function () {
        b.textContent = "Kopyalandı"; setTimeout(function () { b.textContent = "Kopyala"; }, 1600);
      });
    });
  });

  // Eskişehir hava durumu (Open-Meteo, anahtarsız ve ücretsiz)
  var w = document.getElementById("weather");
  if (w) {
    var codes = { 0: "☀️ Açık", 1: "🌤️ Az bulutlu", 2: "⛅ Parçalı bulutlu", 3: "☁️ Bulutlu", 45: "🌫️ Sisli", 48: "🌫️ Sisli",
      51: "🌦️ Çisenti", 53: "🌦️ Çisenti", 55: "🌦️ Çisenti", 61: "🌧️ Yağmurlu", 63: "🌧️ Yağmurlu", 65: "🌧️ Sağanak",
      71: "🌨️ Karlı", 73: "🌨️ Karlı", 75: "❄️ Yoğun kar", 80: "🌦️ Sağanak", 81: "🌧️ Sağanak", 82: "⛈️ Kuvvetli sağanak",
      95: "⛈️ Gök gürültülü", 96: "⛈️ Dolu", 99: "⛈️ Dolu" };
    fetch("https://api.open-meteo.com/v1/forecast?latitude=39.7767&longitude=30.5206&current=temperature_2m,weather_code&timezone=Europe%2FIstanbul")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var c = d.current;
        w.textContent = "Eskişehir " + Math.round(c.temperature_2m) + "°C · " + (codes[c.weather_code] || "");
        w.hidden = false;
      })
      .catch(function () {});
  }

  // Arama sayfası
  var q = document.getElementById("q");
  var out = document.getElementById("results");
  if (q && out) {
    var base = out.dataset.base || "";
    var data = [];
    var norm = function (s) { return s.toLocaleLowerCase("tr").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/ı/g, "i"); };
    fetch(base + "search.json").then(function (r) { return r.json(); }).then(function (d) { data = d; render(); });
    function render() {
      var term = norm(q.value.trim());
      out.innerHTML = "";
      if (term.length < 2) return;
      var hits = data.filter(function (a) { return norm(a.t + " " + a.s + " " + a.c + " " + a.d).indexOf(term) !== -1; }).slice(0, 50);
      if (!hits.length) { out.innerHTML = "<p class='empty'>Sonuç bulunamadı.</p>"; return; }
      hits.forEach(function (a) {
        var el = document.createElement("a");
        el.href = base + a.u;
        var meta = document.createElement("span"); meta.textContent = a.c + " · " + a.d;
        var t = document.createElement("strong"); t.textContent = a.t;
        el.append(meta, t);
        out.append(el);
      });
    }
    q.addEventListener("input", render);
    var p = new URLSearchParams(location.search).get("q");
    if (p) q.value = p;
  }

  // Manşet slaytı: üstteki çubuk dolunca sıradaki habere geçer; dokunma, fare ve odakta durur
  var slider = document.querySelector("[data-slider]");
  if (slider) {
    var track = slider.querySelector("[data-track]");
    var slides = slider.querySelectorAll(".slide");
    var dots = slider.querySelectorAll("[data-dot]");
    var cur = -1, holds = 0, settle;
    var still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (still) slider.classList.add("still");
    var go = function (i) {
      i = (i + slides.length) % slides.length;
      track.scrollTo({ left: i * track.clientWidth, behavior: still ? "auto" : "smooth" });
      mark(i);
    };
    var mark = function (i) {
      if (i === cur) return;
      cur = i;
      slides.forEach(function (s, k) { s.inert = k !== i; });
      dots.forEach(function (d, k) {
        d.classList.toggle("done", k < i);
        d.classList.remove("on");
        if (k === i) { void d.offsetWidth; d.classList.add("on"); }  // çubuk animasyonu baştan başlasın
        d.setAttribute("aria-current", k === i ? "true" : "false");
      });
    };
    var hold = function (on) { holds = Math.max(0, holds + (on ? 1 : -1)); slider.classList.toggle("paused", holds > 0); };
    dots.forEach(function (d, k) {
      d.addEventListener("click", function () { go(k); });
      d.querySelector("i").addEventListener("animationend", function () { if (k === cur) go(cur + 1); });
    });
    var prev = slider.querySelector("[data-prev]"), next = slider.querySelector("[data-next]");
    if (prev) prev.addEventListener("click", function () { go(cur - 1); });
    if (next) next.addEventListener("click", function () { go(cur + 1); });
    // Parmakla kaydırınca hangi haberde durulduğunu bul
    track.addEventListener("scroll", function () {
      clearTimeout(settle);
      settle = setTimeout(function () { mark(Math.round(track.scrollLeft / track.clientWidth)); }, 90);
    }, { passive: true });
    slider.addEventListener("mouseenter", function () { hold(true); });
    slider.addEventListener("mouseleave", function () { hold(false); });
    // Klavyeyle gezenlerde odaktayken durur; dokunup bırakılan çubuk kaymayı kalıcı durdurmasın
    var focusHeld = false;
    slider.addEventListener("focusin", function (e) {
      if (!focusHeld && e.target.matches(":focus-visible")) { focusHeld = true; hold(true); }
    });
    slider.addEventListener("focusout", function (e) {
      if (focusHeld && !slider.contains(e.relatedTarget)) { focusHeld = false; hold(false); }
    });
    track.addEventListener("touchstart", function () { hold(true); }, { passive: true });
    track.addEventListener("touchend", function () { setTimeout(function () { hold(false); }, 1500); }, { passive: true });
    document.addEventListener("visibilitychange", function () { hold(document.hidden); });
    slider.addEventListener("keydown", function (e) {
      if (e.key === "ArrowRight") go(cur + 1);
      if (e.key === "ArrowLeft") go(cur - 1);
    });
    addEventListener("resize", function () { track.scrollLeft = cur * track.clientWidth; });
    mark(0);
  }

  // "Story'de paylaş": haberin hazır story görselini telefonun paylaşım menüsüne gönderir (Instagram > Hikaye)
  var story = document.querySelector("[data-story]");
  if (story && navigator.canShare && matchMedia("(pointer: coarse)").matches) {
    var probe = new File([""], "story.jpg", { type: "image/jpeg" });
    if (navigator.canShare({ files: [probe] })) {
      story.hidden = false;
      // Görsel önceden indirilir: paylaşım menüsü dokunuşun hemen ardından açılmalı (iOS beklemeye izin vermez)
      var file = null;
      fetch(story.dataset.story).then(function (r) { return r.blob(); }).then(function (b) {
        file = new File([b], "nabiz26-" + story.dataset.slug.slice(0, 40) + ".jpg", { type: "image/jpeg" });
      }).catch(function () {});
      story.addEventListener("click", function () {
        if (!file) { location.href = story.dataset.story; return; }  // henüz inmediyse görseli aç
        navigator.share({ files: [file] }).catch(function () {});
      });
    }
  }
})();
