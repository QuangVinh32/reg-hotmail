"""Typing logger chạy ở system tray. Ghi phím gõ + thống kê.

Cài đặt:  pip install pynput pystray Pillow
Chạy:     python typing_logger.py
Dừng:     chuột phải vào icon tray -> 'Dừng và thoát'
"""
import ctypes
import os
import subprocess
import sys
import threading
import winreg
from collections import Counter
from datetime import datetime
from pathlib import Path

from pynput import keyboard
import pystray
from PIL import Image, ImageDraw

IS_FROZEN = getattr(sys, "frozen", False)
if IS_FROZEN:
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "typing_logs"
LOG_DIR.mkdir(exist_ok=True)
FIRST_RUN_FLAG = LOG_DIR / ".first_run_done"

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "TypingLogger"


def get_autostart_path() -> str | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return value
    except FileNotFoundError:
        return None


def is_autostart_enabled() -> bool:
    return get_autostart_path() is not None


def set_autostart(enabled: bool) -> None:
    if not IS_FROZEN:
        return
    exe_path = f'"{Path(sys.executable).resolve()}"'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_ALL_ACCESS) as key:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass


def sync_autostart_path() -> None:
    if not IS_FROZEN or not is_autostart_enabled():
        return
    expected = f'"{Path(sys.executable).resolve()}"'
    if get_autostart_path() != expected:
        set_autostart(True)


def prompt_first_run() -> bool:
    MB_YESNO = 0x4
    MB_ICONQUESTION = 0x20
    MB_TOPMOST = 0x40000
    IDYES = 6
    msg = (
        "Bật tự khởi động cùng Windows?\n\n"
        "Có  → app tự chạy vào tray mỗi khi bạn đăng nhập.\n"
        "Không → bạn phải tự bật mỗi lần.\n\n"
        "Có thể bật/tắt sau qua menu chuột phải lên icon tray."
    )
    result = ctypes.windll.user32.MessageBoxW(
        None, msg, "Typing Logger — Lần đầu chạy",
        MB_YESNO | MB_ICONQUESTION | MB_TOPMOST,
    )
    return result == IDYES

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


def on_open_viewer(icon, item):
    if IS_FROZEN:
        viewer_exe = BASE_DIR / "TypingViewer.exe"
        if viewer_exe.exists():
            os.startfile(str(viewer_exe))
            return
    viewer_py = BASE_DIR / "typing_viewer_ui.py"
    if viewer_py.exists():
        subprocess.Popen([sys.executable, str(viewer_py)], cwd=str(BASE_DIR))


def on_toggle_autostart(icon, item):
    new_state = not is_autostart_enabled()
    set_autostart(new_state)
    icon.notify(
        f"Tự khởi động: {'BẬT' if new_state else 'TẮT'}",
        "Typing Logger",
    )


def on_quit(icon, item):
    listener.stop()
    icon.stop()


if IS_FROZEN and not FIRST_RUN_FLAG.exists():
    if prompt_first_run():
        set_autostart(True)
    FIRST_RUN_FLAG.write_text("done", encoding="utf-8")
sync_autostart_path()

listener = keyboard.Listener(on_press=on_press)
listener.start()

menu = pystray.Menu(
    pystray.MenuItem("Typing Logger (của bạn)", None, enabled=False),
    pystray.MenuItem("Mở viewer", on_open_viewer, default=True),
    pystray.MenuItem("Xem trạng thái", on_show_status),
    pystray.MenuItem("Mở thư mục log", on_open_folder),
    pystray.MenuItem(
        "Tự khởi động cùng Windows",
        on_toggle_autostart,
        checked=lambda item: is_autostart_enabled(),
    ),
    pystray.MenuItem("Dừng và thoát", on_quit),
)

icon = pystray.Icon("typing_logger", make_icon_image(), "Typing Logger", menu)
print(f"[Typing Logger] Đang ghi vào: {log_file}")
print("Icon đã xuất hiện ở system tray. Chuột phải vào icon để dừng.")
icon.run()
