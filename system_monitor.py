import tkinter as tk
import threading
import subprocess
import time
import platform
import re

try:
    import psutil
except ImportError:
    raise SystemExit("Cần cài psutil trước: pip install psutil")


BG = "#f0f0f0"
PILL_BG = "#ffffff"
BORDER = "#b8b8b8"
TEXT = "#202020"
MUTED = "#606060"
GREEN = "#2e9e4f"
YELLOW = "#d49a00"
RED = "#c23434"


def color_for(pct):
    if pct < 60: return GREEN
    if pct < 85: return YELLOW
    return RED


class Pill(tk.Frame):
    def __init__(self, master, label):
        super().__init__(master, bg=PILL_BG, highlightbackground=BORDER, highlightthickness=1)
        self.label_text = label
        self.var = tk.StringVar(value=f"{label}: --")
        self.lbl = tk.Label(self, textvariable=self.var, font=("Segoe UI", 10), bg=PILL_BG, fg=TEXT, padx=12, pady=4)
        self.lbl.pack()

    def set_value(self, value_str, color=None):
        self.var.set(f"{self.label_text}: {value_str}")
        if color:
            self.lbl.configure(fg=color)


class SignalIcon(tk.Canvas):
    def __init__(self, master):
        super().__init__(master, width=22, height=18, bg=BG, highlightthickness=0)
        self.bars = []
        heights = [4, 8, 12, 16]
        for i, h in enumerate(heights):
            x = 2 + i * 5
            bar = self.create_rectangle(x, 18 - h, x + 3, 18, fill="#cccccc", width=0)
            self.bars.append(bar)

    def set_strength(self, ms):
        if ms is None:
            levels = 0
        elif ms < 40:   levels = 4
        elif ms < 100:  levels = 3
        elif ms < 200:  levels = 2
        else:           levels = 1
        for i, bar in enumerate(self.bars):
            self.itemconfig(bar, fill=GREEN if i < levels else "#cccccc")


class CpuProbe:
    def __init__(self):
        self.latest = 0.0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._stop.is_set():
            self.latest = psutil.cpu_percent(interval=1.0)

    def stop(self):
        self._stop.set()


class PingProbe:
    def __init__(self, host="8.8.8.8"):
        self.host = host
        self.latest = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        is_windows = platform.system() == "Windows"
        while not self._stop.is_set():
            try:
                cmd = ["ping", "-n", "1", "-w", "1000", self.host] if is_windows \
                    else ["ping", "-c", "1", "-W", "1", self.host]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                self.latest = self._parse(result.stdout)
            except Exception:
                self.latest = None
            time.sleep(5)

    @staticmethod
    def _parse(out):
        m = re.search(r"time[=<](\d+\.?\d*)\s*ms", out)
        if m: return float(m.group(1))
        m = re.search(r"Average = (\d+)ms", out)
        if m: return float(m.group(1))
        return None

    def stop(self):
        self._stop.set()


class MonitorBar(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("System Monitor")
        self.geometry("520x44")
        self.configure(bg=BG)
        self.resizable(False, False)

        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="both", expand=True, padx=8, pady=6)

        self.cpu = Pill(bar, "CPU")
        self.ram = Pill(bar, "RAM")
        self.cpu.pack(side="left", padx=4)
        self.ram.pack(side="left", padx=4)

        sig_frame = tk.Frame(bar, bg=BG)
        sig_frame.pack(side="left", padx=12)
        self.signal = SignalIcon(sig_frame)
        self.signal.pack(side="left")
        self.ping_var = tk.StringVar(value="-- ms")
        tk.Label(sig_frame, textvariable=self.ping_var, font=("Segoe UI", 10), bg=BG, fg=MUTED).pack(side="left", padx=4)

        self._probe = PingProbe()
        self._cpu = CpuProbe()
        self._cpu_smoothed = 0.0
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(1000, self._tick)

    def _tick(self):
        alpha = 0.5
        self._cpu_smoothed = alpha * self._cpu.latest + (1 - alpha) * self._cpu_smoothed
        cpu_pct = self._cpu_smoothed
        self.cpu.set_value(f"{cpu_pct:.1f}%", color_for(cpu_pct))

        mem_pct = psutil.virtual_memory().percent
        self.ram.set_value(f"{mem_pct:.1f}%", color_for(mem_pct))

        ms = self._probe.latest
        self.signal.set_strength(ms)
        self.ping_var.set("-- ms" if ms is None else f"{ms:.0f} ms")

        self.after(1000, self._tick)

    def _on_close(self):
        self._probe.stop()
        self._cpu.stop()
        self.destroy()


if __name__ == "__main__":
    MonitorBar().mainloop()
