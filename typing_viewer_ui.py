"""Viewer GUI cho typing logs. Dùng cùng phong cách với system_monitor.py.

Chạy:  python typing_viewer_ui.py
"""
import sys
import tkinter as tk
from tkinter import ttk
from collections import Counter
from datetime import datetime
from pathlib import Path

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "typing_logs"

BG = "#f0f0f0"
PILL_BG = "#ffffff"
BORDER = "#b8b8b8"
TEXT = "#202020"
MUTED = "#606060"
GREEN = "#2e9e4f"
YELLOW = "#d49a00"
RED = "#c23434"


def color_for_kpm(kpm: float) -> str:
    if kpm < 100: return MUTED
    if kpm < 250: return GREEN
    if kpm < 400: return YELLOW
    return RED


class Pill(tk.Frame):
    def __init__(self, master, label):
        super().__init__(master, bg=PILL_BG, highlightbackground=BORDER, highlightthickness=1)
        self.label_text = label
        self.var = tk.StringVar(value=f"{label}: --")
        self.lbl = tk.Label(self, textvariable=self.var, font=("Segoe UI", 10),
                            bg=PILL_BG, fg=TEXT, padx=12, pady=4)
        self.lbl.pack()

    def set_value(self, value_str, color=None):
        self.var.set(f"{self.label_text}: {value_str}")
        if color:
            self.lbl.configure(fg=color)


def reconstruct(log_path: Path):
    chars = []
    counter: Counter = Counter()
    total = 0
    first_ts = None
    last_ts = None
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t", 1)
                if len(parts) != 2:
                    continue
                ts, key = parts
                if first_ts is None:
                    first_ts = ts
                last_ts = ts
                counter[key] += 1
                total += 1
                if key == "<space>": chars.append(" ")
                elif key == "<enter>": chars.append("\n")
                elif key == "<tab>": chars.append("\t")
                elif key == "<backspace>":
                    if chars: chars.pop()
                elif key.startswith("<"): continue
                else: chars.append(key)
    except FileNotFoundError:
        return None
    return {
        "first_ts": first_ts,
        "last_ts": last_ts,
        "total": total,
        "counter": counter,
        "text": "".join(chars),
    }


def parse_ts(ts: str):
    try:
        return datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None


class ViewerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Typing Logger — Viewer")
        self.geometry("980x620")
        self.configure(bg=BG)
        self.minsize(780, 480)

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=10, pady=(10, 6))
        self.pill_total = Pill(top, "Tổng phím")
        self.pill_kpm = Pill(top, "Tốc độ")
        self.pill_elapsed = Pill(top, "Thời lượng")
        self.pill_file = Pill(top, "Session")
        for p in (self.pill_total, self.pill_kpm, self.pill_elapsed, self.pill_file):
            p.pack(side="left", padx=4)

        refresh_btn = tk.Button(top, text="↻ Refresh", font=("Segoe UI", 9),
                                bg=PILL_BG, fg=TEXT, relief="flat",
                                highlightbackground=BORDER, highlightthickness=1,
                                padx=10, pady=3, command=self.refresh_sessions)
        refresh_btn.pack(side="right", padx=4)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=6)

        left = tk.Frame(body, bg=PILL_BG, highlightbackground=BORDER, highlightthickness=1)
        left.pack(side="left", fill="y", padx=(0, 8))
        tk.Label(left, text="Sessions", font=("Segoe UI", 10, "bold"),
                 bg=PILL_BG, fg=TEXT, padx=10, pady=6).pack(anchor="w")
        self.session_list = tk.Listbox(left, font=("Consolas", 9), width=28,
                                       bg=PILL_BG, fg=TEXT, bd=0,
                                       highlightthickness=0, activestyle="none",
                                       selectbackground="#cce4ff", selectforeground=TEXT)
        self.session_list.pack(fill="y", expand=True, padx=8, pady=(0, 8))
        self.session_list.bind("<<ListboxSelect>>", self.on_select)

        center = tk.Frame(body, bg=BG)
        center.pack(side="left", fill="both", expand=True)

        tk.Label(center, text="Nội dung tái tạo", font=("Segoe UI", 10, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w")
        text_frame = tk.Frame(center, bg=PILL_BG, highlightbackground=BORDER, highlightthickness=1)
        text_frame.pack(fill="both", expand=True, pady=(4, 0))
        self.text = tk.Text(text_frame, font=("Consolas", 10), bg=PILL_BG, fg=TEXT,
                            bd=0, padx=10, pady=8, wrap="word")
        scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True)

        right = tk.Frame(body, bg=PILL_BG, highlightbackground=BORDER, highlightthickness=1)
        right.pack(side="right", fill="y", padx=(8, 0))
        tk.Label(right, text="Top phím", font=("Segoe UI", 10, "bold"),
                 bg=PILL_BG, fg=TEXT, padx=10, pady=6).pack(anchor="w")
        self.top_keys = tk.Text(right, font=("Consolas", 10), bg=PILL_BG, fg=TEXT,
                                bd=0, padx=10, pady=4, width=22, wrap="none")
        self.top_keys.pack(fill="y", expand=True, padx=(0, 8), pady=(0, 8))

        self.sessions: list[Path] = []
        self.refresh_sessions()

    def refresh_sessions(self):
        self.sessions = sorted(LOG_DIR.glob("typing_*.log"))
        self.session_list.delete(0, "end")
        if not self.sessions:
            self.session_list.insert("end", "  (chưa có log)")
            self._set_empty()
            return
        for s in self.sessions:
            self.session_list.insert("end", s.stem.replace("typing_", ""))
        self.session_list.selection_set("end")
        self.session_list.see("end")
        self.show_session(self.sessions[-1])

    def on_select(self, event):
        sel = self.session_list.curselection()
        if not sel or not self.sessions:
            return
        idx = sel[0]
        if 0 <= idx < len(self.sessions):
            self.show_session(self.sessions[idx])

    def _set_empty(self):
        self.pill_total.set_value("--")
        self.pill_kpm.set_value("--", MUTED)
        self.pill_elapsed.set_value("--")
        self.pill_file.set_value("--")
        self.text.delete("1.0", "end")
        self.top_keys.delete("1.0", "end")

    def show_session(self, log_path: Path):
        info = reconstruct(log_path)
        if info is None:
            self._set_empty()
            return

        first = parse_ts(info["first_ts"])
        last = parse_ts(info["last_ts"])
        elapsed_min = 0.0
        if first and last:
            elapsed_min = (last - first).total_seconds() / 60.0

        kpm = info["total"] / elapsed_min if elapsed_min > 0 else 0.0

        self.pill_total.set_value(f"{info['total']}")
        self.pill_kpm.set_value(f"{kpm:.1f} / phút", color_for_kpm(kpm))
        self.pill_elapsed.set_value(f"{elapsed_min:.1f} phút" if elapsed_min else "<1 phút")
        self.pill_file.set_value(log_path.stem.replace("typing_", ""))

        self.text.delete("1.0", "end")
        self.text.insert("1.0", info["text"] or "(trống)")

        self.top_keys.delete("1.0", "end")
        for k, c in info["counter"].most_common(20):
            label = k if not k.startswith("<") else k
            self.top_keys.insert("end", f"{label:<12} {c}\n")


if __name__ == "__main__":
    LOG_DIR.mkdir(exist_ok=True)
    ViewerApp().mainloop()
