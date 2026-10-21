"""Yeni haberleri Instagram'a paylaşır (Instagram Graph API, içerik yayınlama).

Görseller sitede yayınlandıktan sonra çalışır: nabiz26.com/social/feed.json okunur, henüz
paylaşılmamış haberler story olarak, fotoğraflı olanların en yenisi de gönderi olarak paylaşılır.
Paylaşılanlar data/instagram.json dosyasında tutulur.

Ortam değişkenleri: IG_USER_ID, IG_ACCESS_TOKEN (Meta), isteğe bağlı GRAPH_VERSION.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

SITE = "https://nabiz26.com"
STATE = Path(__file__).parent / "data" / "instagram.json"
GRAPH = f"https://graph.facebook.com/{os.environ.get('GRAPH_VERSION', 'v23.0')}"
MAX_STORIES = 4   # tur başına
MAX_POSTS = 1     # tur başına; akışı boğmamak için


def call(method, path, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    data = urllib.parse.urlencode(params).encode()
    url = f"{GRAPH}/{path}"
    req = urllib.request.Request(url if method == "POST" else f"{url}?{data.decode()}",
                                 data=data if method == "POST" else None, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode()[:500]) from None


def publish(user, **media):
    container = call("POST", f"{user}/media", **media)["id"]
    for _ in range(20):  # Instagram görseli işleyene kadar bekle
        status = call("GET", container, fields="status_code").get("status_code")
        if status == "FINISHED":
            break
        if status == "ERROR":
            raise RuntimeError("Instagram görseli işleyemedi")
        time.sleep(3)
    return call("POST", f"{user}/media_publish", creation_id=container)["id"]


def main():
    user, token = os.environ.get("IG_USER_ID"), os.environ.get("IG_ACCESS_TOKEN")
    if not user or not token:
        print("Instagram bilgileri (IG_USER_ID, IG_ACCESS_TOKEN) tanımlı değil; paylaşım atlandı.")
        return
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"stories": [], "posts": []}
    with urllib.request.urlopen(f"{SITE}/social/feed.json?t={int(time.time())}", timeout=30) as r:
        feed = json.load(r)
    if not state["stories"] and not state["posts"]:
        # İlk çalıştırmada eski haberlerin hepsini birden paylaşma: en yeni 2 haberle başla
        state["stories"] = [f["slug"] for f in feed[2:]]
        state["posts"] = [f["slug"] for f in feed[2:]]
    new = [f for f in reversed(feed) if f["slug"] not in state["stories"]]  # eskiden yeniye
    for f in new[-MAX_STORIES:]:
        try:
            mid = publish(user, image_url=f["story"], media_type="STORIES")
            print("story:", f["slug"], mid)
            state["stories"].append(f["slug"])
        except RuntimeError as e:
            print("story hatası:", f["slug"], e, file=sys.stderr)
    for f in [f for f in feed if f["has_photo"] and f["slug"] not in state["posts"]][:MAX_POSTS]:
        try:
            mid = publish(user, image_url=f["post"], caption=f["caption"])
            print("gönderi:", f["slug"], mid)
            state["posts"].append(f["slug"])
        except RuntimeError as e:
            print("gönderi hatası:", f["slug"], e, file=sys.stderr)
    # Atlananlar bir daha denenmesin
    for f in new[:-MAX_STORIES]:
        state["stories"].append(f["slug"])
    state["stories"], state["posts"] = state["stories"][-500:], state["posts"][-500:]
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
