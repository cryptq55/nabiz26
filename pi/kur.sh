#!/usr/bin/env bash
# Nabız 26 haber masasını Raspberry Pi'ye kurar. Haber masasını çalıştıracak kullanıcıyla (root DEĞİL) çalıştırın:
#   curl -fsSL https://raw.githubusercontent.com/cryptq55/nabiz26/main/pi/kur.sh | bash
# Tekrar çalıştırmak güvenlidir. Ayrıntı: pi/KURULUM.md
set -euo pipefail
REPO="$HOME/nabiz26"
KEY="$HOME/.ssh/nabiz26_deploy"
ENV_FILE="$HOME/.config/nabiz26.env"
[ "$(id -u)" != 0 ] || { echo "Root olarak değil, normal kullanıcıyla çalıştırın (sudo gerektiğinde sorulur)."; exit 1; }

echo "1/5 Paketler"
sudo apt-get update -qq
sudo apt-get install -y -qq git python3 python3-venv python3-pip util-linux libjpeg-dev zlib1g-dev >/dev/null

echo "2/5 GitHub anahtarı"
mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
[ -f "$KEY" ] || ssh-keygen -q -t ed25519 -N "" -C "nabiz26-pi" -f "$KEY"
if ! grep -q "Host github-nabiz26" "$HOME/.ssh/config" 2>/dev/null; then
  printf '\nHost github-nabiz26\n  HostName github.com\n  User git\n  IdentityFile %s\n  IdentitiesOnly yes\n' "$KEY" >> "$HOME/.ssh/config"
  chmod 600 "$HOME/.ssh/config"
fi
ssh-keyscan -t ed25519 github.com 2>/dev/null >> "$HOME/.ssh/known_hosts"
sort -u -o "$HOME/.ssh/known_hosts" "$HOME/.ssh/known_hosts"

echo "3/5 Depo ve Python ortamı"
if [ ! -d "$REPO/.git" ]; then
  git clone -q https://github.com/cryptq55/nabiz26.git "$REPO"   # depo herkese açık: okumak için anahtar gerekmez
fi
git -C "$REPO" remote set-url origin git@github-nabiz26:cryptq55/nabiz26.git
[ -d "$REPO/.venv" ] || python3 -m venv "$REPO/.venv"
"$REPO/.venv/bin/pip" install -q --upgrade pip
"$REPO/.venv/bin/pip" install -q -r "$REPO/requirements.txt"
chmod +x "$REPO/pi/tur.sh"

echo "4/5 Ayar dosyası ($ENV_FILE)"
mkdir -p "$(dirname "$ENV_FILE")"
if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" <<ENV
# Nabız 26 Pi masası ayarları. Bu dosya gizlidir (chmod 600); depoya ya da sohbete kopyalamayın.
NEWS_API_BASE=http://127.0.0.1:8317/v1
NEWS_API_MODEL=gemini-3.8-flash-high
NEWS_API_KEY=${NEWS_API_KEY:-BURAYA_CLIPROXY_ANAHTARI}
ENV
fi
chmod 600 "$ENV_FILE"

echo "5/5 Zamanlama (08.07-00.07 arası 2 saatte bir)"
sudo tee /etc/systemd/system/nabiz26-masa.service >/dev/null <<UNIT
[Unit]
Description=Nabiz 26 haber turu
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$USER
ExecStart=$REPO/pi/tur.sh
Nice=10
TimeoutStartSec=1500
UNIT
sudo tee /etc/systemd/system/nabiz26-masa.timer >/dev/null <<UNIT
[Unit]
Description=Nabiz 26 haber turu zamanlayicisi

[Timer]
OnCalendar=*-*-* 00,08,10,12,14,16,18,20,22:07:00 Europe/Istanbul
Persistent=true

[Install]
WantedBy=timers.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable -q --now nabiz26-masa.timer

echo
echo "KURULUM BİTTİ. Kalan iki iş:"
echo "A) Bu açık anahtarı GitHub'a ekleyin (yazma izniyle):"
echo "   https://github.com/cryptq55/nabiz26/settings/keys/new  ->  Title: nabiz26-pi, 'Allow write access' işaretli"
echo
cat "$KEY.pub"
echo
if grep -q BURAYA_CLIPROXY_ANAHTARI "$ENV_FILE"; then
  echo "B) $ENV_FILE dosyasındaki NEWS_API_KEY satırına CLIProxy anahtarını yazın."
fi
echo "Sonra deneme turu:  sudo systemctl start nabiz26-masa.service && tail -n 40 ~/.local/state/nabiz26/tur.log"
