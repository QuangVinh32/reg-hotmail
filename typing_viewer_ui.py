"""Viewer GUI cho typing logs. Dùng cùng phong cách với system_monitor.py.

Chạy:  python typing_viewer_ui.py
"""
import os
import sys
import tkinter as tk
import unicodedata
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
BAR_FG = "#2e9e4f"
BAR_BG = "#e6e6e6"


def color_for_kpm(kpm: float) -> str:
    if kpm < 100: return MUTED
    if kpm < 250: return GREEN
    if kpm < 400: return YELLOW
    return RED


VIET_BASE_MAP = {"đ": "d", "Đ": "D"}


def base_letter(c: str) -> str:
    if c in VIET_BASE_MAP:
        return VIET_BASE_MAP[c]
    decomp = unicodedata.normalize("NFD", c)
    stripped = "".join(ch for ch in decomp if not unicodedata.combining(ch))
    return stripped or c


def clean_vietnamese(text: str) -> str:
    """Gộp các ký tự liên tiếp cùng âm gốc → giữ ký tự cuối cùng.

    VD: "khoơởi dđoôộng maáy" → "khởi động máy" — phù hợp khi keylogger ghi cả
    phím gõ thô lẫn ký tự đã được IME (Unikey) thay thế.
    """
    result: list[str] = []
    for ch in text:
        if (
            result
            and result[-1] != ch
            and base_letter(result[-1]).lower() == base_letter(ch).lower()
        ):
            result[-1] = ch
        else:
            result.append(ch)
    return "".join(result)


def parse_ts(ts: str):
    try:
        return datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None


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


def _apply_key(chars: list[str], key: str) -> None:
    if key == "<space>": chars.append(" ")
    elif key == "<enter>": chars.append("\n")
    elif key == "<tab>": chars.append("\t")
    elif key == "<backspace>":
        if chars: chars.pop()
    elif key.startswith("<"): return
    else: chars.append(key)


def bucket_key(t: datetime) -> str:
    return f"{t.strftime('%Y-%m-%d')} {t.hour:02d}h"


def reconstruct(log_path: Path, bucket_filter: str | None = None):
    chars: list[str] = []
    counter: Counter = Counter()
    per_bucket: Counter = Counter()
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
                t = parse_ts(ts)
                bk = bucket_key(t) if t else None
                if bucket_filter is not None and bk != bucket_filter:
                    continue
                if first_ts is None:
                    first_ts = ts
                last_ts = ts
                counter[key] += 1
                total += 1
                if bk is not None:
                    per_bucket[bk] += 1
                _apply_key(chars, key)
    except FileNotFoundError:
        return None
    return {
        "first_ts": first_ts,
        "last_ts": last_ts,
        "total": total,
        "counter": counter,
        "per_bucket": per_bucket,
        "text": "".join(chars),
    }


class ViewerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Typing Logger — Viewer")
        self.geometry("1080x720")
        self.configure(bg=BG)
        self.minsize(880, 560)

        self.current_log: Path | None = None
        self.vn_mode = tk.BooleanVar(value=True)

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=10, pady=(10, 6))
        self.pill_total = Pill(top, "Tổng phím")
        self.pill_kpm = Pill(top, "Tốc độ")
        self.pill_elapsed = Pill(top, "Thời lượng")
        self.pill_file = Pill(top, "Session")
        for p in (self.pill_total, self.pill_kpm, self.pill_elapsed, self.pill_file):
            p.pack(side="left", padx=4)

        refresh_btn = self._mk_btn(top, "↻ Refresh", self.refresh_sessions)
        refresh_btn.pack(side="right", padx=4)
        open_log_btn = self._mk_btn(top, "📄 Mở file log", self.on_view_log)
        open_log_btn.pack(side="right", padx=4)
        vn_chk = tk.Checkbutton(
            top, text="VN có dấu", variable=self.vn_mode,
            command=self.on_toggle_vn, bg=BG, fg=TEXT,
            activebackground=BG, font=("Segoe UI", 9),
        )
        vn_chk.pack(side="right", padx=4)

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
        text_frame.pack(fill="both", expand=True, pady=(4, 8))
        self.text = tk.Text(text_frame, font=("Consolas", 10), bg=PILL_BG, fg=TEXT,
                            bd=0, padx=10, pady=8, wrap="word")
        scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True)

        tk.Label(center, text="Biểu đồ hoạt động (theo ngày + giờ)",
                 font=("Segoe UI", 10, "bold"), bg=BG, fg=TEXT).pack(anchor="w")
        chart_frame = tk.Frame(center, bg=PILL_BG, highlightbackground=BORDER, highlightthickness=1)
        chart_frame.pack(fill="x", expand=False, pady=(4, 8))
        self.chart = tk.Canvas(chart_frame, bg=PILL_BG, height=160, highlightthickness=0)
        self.chart.pack(fill="x", expand=True)
        self.chart.bind("<Configure>", lambda _e: self._render_chart(self._last_buckets))
        self.chart_tip = tk.Label(self.chart, bg="#333333", fg="white",
                                  font=("Segoe UI", 8), padx=6, pady=2)
        self.chart_tip.place_forget()
        self._last_buckets: Counter = Counter()
        self._heatmap_buckets: list[str] = []

        tk.Label(center, text="Mốc thời gian (ngày + giờ) — bấm để xem chi tiết",
                 font=("Segoe UI", 10, "bold"), bg=BG, fg=TEXT).pack(anchor="w")
        heatmap_frame = tk.Frame(center, bg=PILL_BG, highlightbackground=BORDER, highlightthickness=1)
        heatmap_frame.pack(fill="both", expand=False, pady=(4, 0))
        self.heatmap = tk.Text(heatmap_frame, font=("Consolas", 10), bg=PILL_BG, fg=TEXT,
                               bd=0, padx=10, pady=6, height=10, wrap="none", cursor="hand2")
        hscroll = ttk.Scrollbar(heatmap_frame, orient="vertical", command=self.heatmap.yview)
        self.heatmap.configure(yscrollcommand=hscroll.set, state="disabled")
        hscroll.pack(side="right", fill="y")
        self.heatmap.pack(fill="both", expand=True)
        self.heatmap.tag_configure("bar", foreground=BAR_FG)
        self.heatmap.tag_configure("bg", foreground=BAR_BG)
        self.heatmap.tag_configure("muted", foreground=MUTED)
        self.heatmap.tag_configure("hover", background="#eef6ff")
        self.heatmap.bind("<Button-1>", self._on_heatmap_click)
        self.heatmap.bind("<Motion>", self._on_heatmap_hover)
        self.heatmap.bind("<Leave>", lambda _e: self.heatmap.tag_remove("hover", "1.0", "end"))

        right = tk.Frame(body, bg=PILL_BG, highlightbackground=BORDER, highlightthickness=1)
        right.pack(side="right", fill="y", padx=(8, 0))
        tk.Label(right, text="Top phím", font=("Segoe UI", 10, "bold"),
                 bg=PILL_BG, fg=TEXT, padx=10, pady=6).pack(anchor="w")
        self.top_keys = tk.Text(right, font=("Consolas", 10), bg=PILL_BG, fg=TEXT,
                                bd=0, padx=10, pady=4, width=22, wrap="none")
        self.top_keys.pack(fill="y", expand=True, padx=(0, 8), pady=(0, 8))

        self.sessions: list[Path] = []
        self.refresh_sessions()

    def _mk_btn(self, parent, label, command):
        return tk.Button(parent, text=label, font=("Segoe UI", 9),
                         bg=PILL_BG, fg=TEXT, relief="flat",
                         highlightbackground=BORDER, highlightthickness=1,
                         padx=10, pady=3, command=command, cursor="hand2")

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

    def on_view_log(self):
        if self.current_log and self.current_log.exists():
            try:
                os.startfile(str(self.current_log))
            except OSError:
                pass

    def on_toggle_vn(self):
        if self.current_log:
            self.show_session(self.current_log)

    def _set_empty(self):
        self.current_log = None
        self.pill_total.set_value("--")
        self.pill_kpm.set_value("--", MUTED)
        self.pill_elapsed.set_value("--")
        self.pill_file.set_value("--")
        self.text.delete("1.0", "end")
        self.top_keys.delete("1.0", "end")
        self.heatmap.configure(state="normal")
        self.heatmap.delete("1.0", "end")
        self.heatmap.configure(state="disabled")
        self._heatmap_buckets = []
        self._last_buckets = Counter()
        self.chart.delete("all")

    def show_session(self, log_path: Path):
        info = reconstruct(log_path)
        if info is None:
            self._set_empty()
            return
        self.current_log = log_path

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

        body_text = info["text"]
        if self.vn_mode.get():
            body_text = clean_vietnamese(body_text)
        self.text.delete("1.0", "end")
        self.text.insert("1.0", body_text or "(trống)")

        self.top_keys.delete("1.0", "end")
        for k, c in info["counter"].most_common(20):
            self.top_keys.insert("end", f"{k:<12} {c}\n")

        self._last_buckets = info["per_bucket"]
        self._render_heatmap(info["per_bucket"])
        self._render_chart(info["per_bucket"])

    def _on_heatmap_hover(self, event):
        self.heatmap.tag_remove("hover", "1.0", "end")
        idx = self.heatmap.index(f"@{event.x},{event.y}")
        line_no = int(idx.split(".")[0])
        if 1 <= line_no <= len(self._heatmap_buckets):
            self.heatmap.tag_add("hover", f"{line_no}.0", f"{line_no}.end")

    def _on_heatmap_click(self, event):
        if not self.current_log:
            return
        idx = self.heatmap.index(f"@{event.x},{event.y}")
        line_no = int(idx.split(".")[0])
        i = line_no - 1
        if 0 <= i < len(self._heatmap_buckets):
            self._show_bucket_detail(self._heatmap_buckets[i])

    def _show_bucket_detail(self, bk: str):
        info = reconstruct(self.current_log, bucket_filter=bk)
        if info is None or info["total"] == 0:
            return
        win = tk.Toplevel(self)
        win.title(f"Chi tiết — {bk} ({self.current_log.stem.replace('typing_', '')})")
        win.geometry("760x560")
        win.configure(bg=BG)
        win.transient(self)

        header = tk.Frame(win, bg=BG)
        header.pack(fill="x", padx=12, pady=(12, 4))
        tk.Label(header, text=bk, font=("Segoe UI", 12, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        tk.Label(header, text=f"  {info['total']} phím gõ",
                 font=("Segoe UI", 10), bg=BG, fg=MUTED).pack(side="left", padx=8)

        tk.Label(win, text="Text gõ trong mốc này:", font=("Segoe UI", 10, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=12, pady=(8, 2))
        text_frame = tk.Frame(win, bg=PILL_BG, highlightbackground=BORDER, highlightthickness=1)
        text_frame.pack(fill="both", expand=True, padx=12)
        body = info["text"]
        if self.vn_mode.get():
            body = clean_vietnamese(body)
        txt = tk.Text(text_frame, font=("Consolas", 10), bg=PILL_BG, fg=TEXT,
                      bd=0, padx=10, pady=8, wrap="word")
        sb = ttk.Scrollbar(text_frame, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", body or "(trống)")
        txt.configure(state="disabled")

        tk.Label(win, text="Top phím trong mốc này:", font=("Segoe UI", 10, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", padx=12, pady=(10, 2))
        top_frame = tk.Frame(win, bg=PILL_BG, highlightbackground=BORDER, highlightthickness=1)
        top_frame.pack(fill="x", padx=12, pady=(0, 12))
        top = tk.Text(top_frame, font=("Consolas", 9), bg=PILL_BG, fg=TEXT,
                      bd=0, padx=10, pady=6, height=8, wrap="none")
        top.pack(fill="x", expand=True)
        for k, c in info["counter"].most_common(15):
            top.insert("end", f"{k:<14} {c}\n")
        top.configure(state="disabled")

    def _render_heatmap(self, per_bucket: Counter):
        self.heatmap.configure(state="normal")
        self.heatmap.delete("1.0", "end")
        self._heatmap_buckets = []
        bar_width = 28
        max_count = max(per_bucket.values()) if per_bucket else 0
        if max_count == 0:
            self.heatmap.insert("end", "(không có timestamp hợp lệ)\n", "muted")
            self.heatmap.configure(state="disabled")
            return
        for bk in sorted(per_bucket.keys()):
            count = per_bucket[bk]
            bar_len = int(round(count / max_count * bar_width)) if max_count > 0 else 0
            self.heatmap.insert("end", f"{bk}  ")
            self.heatmap.insert("end", "█" * bar_len, "bar")
            self.heatmap.insert("end", "░" * (bar_width - bar_len), "bg")
            self.heatmap.insert("end", f"  {count}\n")
            self._heatmap_buckets.append(bk)
        self.heatmap.configure(state="disabled")

    def _render_chart(self, per_bucket: Counter):
        self.chart.delete("all")
        if not per_bucket:
            self.chart.create_text(12, 12, anchor="nw", text="(không có dữ liệu)", fill=MUTED)
            return
        self.chart.update_idletasks()
        w = self.chart.winfo_width()
        h = self.chart.winfo_height()
        if w < 50 or h < 50:
            return
        keys = sorted(per_bucket.keys())
        values = [per_bucket[k] for k in keys]
        max_v = max(values)
        n = len(keys)
        ml, mr, mt, mb = 38, 8, 8, 34
        cw = w - ml - mr
        ch = h - mt - mb
        slot = cw / n
        bw = max(2, slot * 0.78)

        self.chart.create_line(ml, mt + ch, ml + cw, mt + ch, fill=BORDER)
        self.chart.create_text(ml - 4, mt, anchor="ne", text=str(max_v),
                               fill=MUTED, font=("Segoe UI", 8))
        self.chart.create_text(ml - 4, mt + ch, anchor="se", text="0",
                               fill=MUTED, font=("Segoe UI", 8))

        for i, (k, v) in enumerate(zip(keys, values)):
            x0 = ml + i * slot + (slot - bw) / 2
            x1 = x0 + bw
            bh = (v / max_v) * ch if max_v else 0
            y0 = mt + ch - bh
            y1 = mt + ch
            bar_id = self.chart.create_rectangle(x0, y0, x1, y1, fill=BAR_FG, outline="")
            self.chart.tag_bind(bar_id, "<Button-1>",
                                lambda _e, key=k: self._show_bucket_detail(key))
            self.chart.tag_bind(bar_id, "<Enter>",
                                lambda _e, key=k, val=v: self._show_tip(key, val))
            self.chart.tag_bind(bar_id, "<Leave>", lambda _e: self.chart_tip.place_forget())

        step = max(1, n // 6)
        for i in range(0, n, step):
            x = ml + i * slot + slot / 2
            y = mt + ch + 4
            self.chart.create_text(x, y, anchor="n", text=keys[i],
                                   fill=MUTED, font=("Segoe UI", 7))

    def _show_tip(self, key: str, val: int):
        self.chart_tip.configure(text=f"{key}: {val} phím")
        self.chart_tip.place(relx=1.0, rely=0, anchor="ne", x=-6, y=4)


if __name__ == "__main__":
    LOG_DIR.mkdir(exist_ok=True)
    ViewerApp().mainloop()
