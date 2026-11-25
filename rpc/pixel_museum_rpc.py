"""Pixel Museum — Discord Rich Presence.

Günün pixel tablosunu Discord profilinde "Playing Pixel Museum" kartı olarak gösterir.
Token gerektirmez, sadece Application ID. Discord masaüstü uygulaması açık olmalı.

Kurulum:  pip install pypresence requests
Çalıştır: pythonw pixel_museum_rpc.py   (pythonw = konsol penceresi açmaz)
"""
import datetime as dt, time, requests
from pypresence import Presence
from pypresence.exceptions import PipeClosed, DiscordNotFound

# ---------- AYARLAR ----------
CLIENT_ID = "1575282909638824168"                        # Pixel Museum Application ID
BASE = "https://arif-aygun.github.io/pixel-museum"       # GitHub Pages adresi
START = dt.date(2026, 11, 26)                            # "Day N" sayacının başladığı gün
CHECK_EVERY = 30 * 60                                    # yeni tablo kontrolü (saniye)
# -----------------------------

def connect():
    while True:
        try:
            rpc = Presence(CLIENT_ID)
            rpc.connect()
            print("Discord'a bağlandı")
            return rpc
        except (DiscordNotFound, ConnectionRefusedError, FileNotFoundError, OSError):
            time.sleep(60)  # Discord kapalı, bekle

def fetch():
    return requests.get(f"{BASE}/today.json", params={"t": int(time.time())}, timeout=15).json()

def show(rpc, art):
    day = (dt.date.today() - START).days + 1
    date = f" ({art['date']})" if art.get("date") else ""
    rpc.update(
        details=art["title"][:128] or "Untitled",
        state=f"{art['artist']}{date} · Day {day}"[:128],
        large_image=art["image_url"],
        large_text="Pixel Museum · today's piece",
        buttons=[
            {"label": "View full size", "url": BASE + "/"},
            {"label": "Original at the Met", "url": art.get("source") or BASE + "/"},
        ],
    )

def main():
    rpc, last = connect(), None
    while True:
        try:
            art = fetch()
            key = (art.get("image_url"), dt.date.today())
            if key != last:
                show(rpc, art)
                last = key
                print("Gösteriliyor:", art.get("caption"))
        except (PipeClosed, BrokenPipeError, ConnectionResetError):
            rpc, last = connect(), None  # Discord yeniden başlatıldı
            continue
        except Exception as e:
            print("Hata, sonra tekrar denenecek:", e)
        time.sleep(CHECK_EVERY)

if __name__ == "__main__":
    main()
