"""Typing logger chạy ở system tray. Ghi phím gõ + thống kê.

Cài đặt:  pip install pynput pystray Pillow
Chạy:     python typing_logger.py
Dừng:     chuột phải vào icon tray -> 'Dừng và thoát'
"""
import os
import sys
import threading
from collections import Counter
from datetime import datetime
from pathlib import Path

from pynput import keyboard
import pystray
from PIL import Image, ImageDraw

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "typing_logs"
LOG_DIR.mkdir(exist_ok=True)

session_start = datetime.now()
stamp = session_start.strftime("%Y%m%d_%H%M%S")
log_file = LOG_DIR / f"typing_{stamp}.log"

key_counter: Counter = Counter()
total_keys = 0
lock = threading.Lock()


def format_key(key) -> str:
    try:
        if getattr(key, "char", None) is not None:
            return key.char
    except AttributeError:
        pass
    name = str(key).replace("Key.", "")
    return f"<{name}>"


def on_press(key):
    global total_keys
    k = format_key(key)
    ts = datetime.now().isoformat(timespec="milliseconds")
    with lock:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{ts}\t{k}\n")
        key_counter[k] += 1
        total_keys += 1


def make_icon_image() -> Image.Image:
    img = Image.new("RGB", (64, 64), color=(30, 30, 30))
    d = ImageDraw.Draw(img)
    d.rectangle([6, 18, 58, 46], fill=(80, 200, 120))
    d.rectangle([12, 24, 18, 30], fill=(30, 30, 30))
    d.rectangle([22, 24, 28, 30], fill=(30, 30, 30))
    d.rectangle([32, 24, 38, 30], fill=(30, 30, 30))
    d.rectangle([42, 24, 52, 30], fill=(30, 30, 30))
    d.rectangle([18, 34, 46, 40], fill=(30, 30, 30))
    return img


def on_show_status(icon, item):
    elapsed = (datetime.now() - session_start).total_seconds() / 60.0
    kpm = total_keys / elapsed if elapsed > 0 else 0
    icon.notify(
        f"Tổng phím: {total_keys} | Tốc độ: {kpm:.1f} phím/phút\nFile: {log_file.name}",
        "Typing Logger",
    )


def on_open_folder(icon, item):
    os.startfile(LOG_DIR)


def on_quit(icon, item):
    listener.stop()
    icon.stop()


listener = keyboard.Listener(on_press=on_press)
listener.start()

menu = pystray.Menu(
    pystray.MenuItem("Typing Logger (của bạn)", None, enabled=False),
    pystray.MenuItem("Xem trạng thái", on_show_status, default=True),
    pystray.MenuItem("Mở thư mục log", on_open_folder),
    pystray.MenuItem("Dừng và thoát", on_quit),
)

icon = pystray.Icon("typing_logger", make_icon_image(), "Typing Logger", menu)
print(f"[Typing Logger] Đang ghi vào: {log_file}")
print("Icon đã xuất hiện ở system tray. Chuột phải vào icon để dừng.")
icon.run()
