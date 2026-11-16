#!/usr/bin/env bash
# Nabız 26 haber turu (Raspberry Pi): haberleri yandaki CLIProxy ile yazar, GitHub'a gönderir.
# Gönderim deploy anahtarıyla yapıldığı için GitHub'da "Fotoğraf bul" ve "Bildir ve paylaş" kendiliğinden başlar.
set -uo pipefail
{   # betik tur sırasında güncellenebilir: tamamı belleğe okunduktan sonra çalışsın
REPO="${NABIZ26_DIR:-$HOME/nabiz26}"
ENV_FILE="${NABIZ26_ENV:-$HOME/.config/nabiz26.env}"
LOG_DIR="$HOME/.local/state/nabiz26"
mkdir -p "$LOG_DIR"
exec 9>"$LOG_DIR/tur.lock"
flock -n 9 || { echo "Önceki tur sürüyor, çıkılıyor."; exit 0; }
exec >>"$LOG_DIR/tur.log" 2>&1
echo "=== $(date '+%F %T') tur başladı"

set -a; . "$ENV_FILE"; set +a
cd "$REPO"
# Pi'de elle değişiklik yapılmaz: her tur depodaki son hâlden başlar
git fetch -q origin main && git reset -q --hard origin/main && git clean -fdq data || { echo "git güncellenemedi"; exit 1; }
"$REPO/.venv/bin/pip" install -q -r requirements.txt

"$REPO/.venv/bin/python" newsbot.py --auto --max "${NABIZ26_MAX:-10}"
echo "newsbot çıkış kodu: $?"

git add data SON_HABERLER.md
if git diff --cached --quiet; then
  echo "Yeni kayıt yok."
else
  git -c user.name="nabiz26-pi" -c user.email="nabiz26-pi@users.noreply.github.com" commit -q -m "Haber turu (Pi masası)"
  for i in 1 2 3; do
    git pull -q --rebase origin main && git push -q origin HEAD:main && { echo "Gönderildi."; break; }
    sleep 10
  done
fi
# Günlük dosyası büyümesin
tail -n 3000 "$LOG_DIR/tur.log" > "$LOG_DIR/tur.log.tmp" && mv "$LOG_DIR/tur.log.tmp" "$LOG_DIR/tur.log"
echo "=== $(date '+%F %T') tur bitti"
exit 0
}
