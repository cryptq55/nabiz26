# Nabız 26 haber masasını Raspberry Pi'de çalıştırma

Amaç: haberleri Pi'nin kendisi yazsın (yandaki CLIProxy, `http://127.0.0.1:8317/v1`), proxy internete açılmasın.
Fotoğraf bulma, Instagram ve site yayını GitHub'da kalır; Pi yalnızca haber kayıtlarını `main`'e gönderir.

## Kurulum (Pi'deki yardımcı ajan ya da sahibi)
1. Haber masasını çalıştıracak normal kullanıcıyla (root değil; sudo yetkisi olmalı):
   `curl -fsSL https://raw.githubusercontent.com/cryptq55/nabiz26/main/pi/kur.sh | bash`
   Betiği çalıştırmadan önce okuyun: `pi/kur.sh` (paket kurar, `~/nabiz26`'ya depoyu indirir, Python ortamı kurar,
   `~/.ssh/nabiz26_deploy` anahtarı üretir, `~/.config/nabiz26.env` ayar dosyasını ve systemd zamanlayıcısını yazar).
2. Betiğin sonunda yazdırdığı **açık anahtarı** (ssh-ed25519 ... nabiz26-pi) sahibine verin; sahibi
   https://github.com/cryptq55/nabiz26/settings/keys/new adresinde "Allow write access" işaretleyerek ekler.
   Açık anahtar gizli değildir. Özel anahtarı (`~/.ssh/nabiz26_deploy`) hiçbir yere kopyalamayın.
3. `~/.config/nabiz26.env` içindeki `NEWS_API_KEY` satırına CLIProxy anahtarını yazın (dosya 600 izinli kalsın).
   Anahtarı sohbete, günlüğe ya da depoya yazmayın. Model adı proxy'deki listede olmalı (`NEWS_API_MODEL`).
4. Deneme: `sudo systemctl start nabiz26-masa.service` sonra `tail -n 40 ~/.local/state/nabiz26/tur.log`.
   Beklenen: `[yazıldı]` / `[fotoğraf bekliyor]` satırları ve "Gönderildi.". `Permission denied (publickey)` görülürse
   2. adım eksiktir. `CLIProxy: ConnectionError` görülürse proxy 8317'de dinlemiyordur ya da adres yanlıştır.
5. Zamanlama: `systemctl list-timers nabiz26-masa.timer` (08.07-00.07 TSİ arası 2 saatte bir).

## Kurallar
- `~/nabiz26` içinde elle değişiklik yapmayın: her tur `git reset --hard origin/main` ile başlar, değişiklikler silinir.
- Kod, iş akışı ve ayar değişiklikleri GitHub'daki depoda yapılır (bkz. `AGENTS.md`, `CLAUDE.md`).
- Kurulum doğrulanınca Claude'a haber verin: GitHub'daki otomatik masa yedeğe çekilecek ve Funnel kapatılabilecek
  (`sudo tailscale funnel --https=443 off` ya da `tailscale funnel reset`).

## Kaldırma
`sudo systemctl disable --now nabiz26-masa.timer && sudo rm /etc/systemd/system/nabiz26-masa.*`
