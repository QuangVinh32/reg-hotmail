import tkinter as tk
from tkinter import ttk, messagebox
import re


BG = "#fafafa"
CARD_BG = "#ffffff"
BORDER = "#dbdbdb"
TEXT = "#262626"
MUTED = "#8e8e8e"
LINK = "#00376b"
BLUE = "#0095f6"
BLUE_DISABLED = "#b2dffc"
FB_BLUE = "#385185"


class PlaceholderEntry(ttk.Entry):
    def __init__(self, master, placeholder, show=None, **kwargs):
        super().__init__(master, **kwargs)
        self.placeholder = placeholder
        self.show_char = show
        self._has_value = False
        self.configure(foreground=MUTED)
        self.insert(0, placeholder)
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<KeyRelease>", self._on_key)

    def _on_focus_in(self, _):
        if not self._has_value:
            self.delete(0, "end")
            self.configure(foreground=TEXT)
            if self.show_char:
                self.configure(show=self.show_char)

    def _on_focus_out(self, _):
        if not self.get():
            self._has_value = False
            self.configure(show="", foreground=MUTED)
            self.insert(0, self.placeholder)

    def _on_key(self, _):
        self._has_value = bool(self.get()) and self.get() != self.placeholder

    def value(self):
        return "" if not self._has_value else self.get()


class SignupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Instagram")
        self.geometry("400x720")
        self.configure(bg=BG)
        self.resizable(False, False)

        self._setup_styles()
        self._build_card()
        self._build_login_card()

    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Field.TEntry",
            fieldbackground="#fafafa",
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            relief="solid",
            padding=8,
        )
        style.configure("TSeparator", background=BORDER)

    def _build_card(self):
        card = tk.Frame(self, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=20, pady=(20, 10))

        tk.Label(
            card,
            text="Instagram",
            font=("Segoe Script", 36, "bold"),
            bg=CARD_BG,
            fg=TEXT,
        ).pack(pady=(36, 8))

        tk.Label(
            card,
            text="Đăng ký để xem ảnh và video\ntừ bạn bè.",
            font=("Segoe UI", 11, "bold"),
            bg=CARD_BG,
            fg=MUTED,
            justify="center",
        ).pack(pady=(0, 16))

        fb_btn = tk.Button(
            card,
            text="  Đăng nhập bằng Facebook",
            font=("Segoe UI", 10, "bold"),
            bg=FB_BLUE,
            fg="white",
            relief="flat",
            cursor="hand2",
            activebackground=FB_BLUE,
            activeforeground="white",
            command=lambda: messagebox.showinfo("Demo", "Đây là form học Tkinter, không có chức năng thật."),
        )
        fb_btn.pack(fill="x", padx=40, pady=(0, 18), ipady=6)

        divider = tk.Frame(card, bg=CARD_BG)
        divider.pack(fill="x", padx=40, pady=(0, 16))
        tk.Frame(divider, bg=BORDER, height=1).pack(side="left", fill="x", expand=True, pady=8)
        tk.Label(divider, text="HOẶC", font=("Segoe UI", 9, "bold"), bg=CARD_BG, fg=MUTED).pack(side="left", padx=10)
        tk.Frame(divider, bg=BORDER, height=1).pack(side="left", fill="x", expand=True, pady=8)

        self.email = self._add_field(card, "Số di động hoặc email")
        self.fullname = self._add_field(card, "Tên đầy đủ")
        self.username = self._add_field(card, "Tên người dùng")
        self.password = self._add_field(card, "Mật khẩu", show="*")

        self.strength_var = tk.StringVar(value="")
        tk.Label(card, textvariable=self.strength_var, font=("Segoe UI", 8), bg=CARD_BG, fg=MUTED).pack(padx=40, anchor="w")
        self.password.bind("<KeyRelease>", self._update_strength, add="+")

        tk.Label(
            card,
            text="Những người dùng dịch vụ của chúng tôi có thể đã tải\nthông tin liên hệ của bạn lên Instagram.",
            font=("Segoe UI", 8),
            bg=CARD_BG,
            fg=MUTED,
            justify="center",
            wraplength=300,
        ).pack(pady=(12, 8), padx=40)

        tk.Label(
            card,
            text="Bằng cách đăng ký, bạn đồng ý với Điều khoản,\nChính sách dữ liệu và Chính sách cookie của chúng tôi.",
            font=("Segoe UI", 8),
            bg=CARD_BG,
            fg=MUTED,
            justify="center",
            wraplength=300,
        ).pack(pady=(0, 16), padx=40)

        self.signup_btn = tk.Button(
            card,
            text="Đăng ký",
            font=("Segoe UI", 10, "bold"),
            bg=BLUE_DISABLED,
            fg="white",
            relief="flat",
            cursor="hand2",
            activebackground=BLUE,
            activeforeground="white",
            state="disabled",
            command=self._on_signup,
        )
        self.signup_btn.pack(fill="x", padx=40, pady=(0, 24), ipady=6)

        for entry in (self.email, self.fullname, self.username, self.password):
            entry.bind("<KeyRelease>", self._validate_form, add="+")

    def _build_login_card(self):
        card = tk.Frame(self, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=20, pady=(0, 20))

        inner = tk.Frame(card, bg=CARD_BG)
        inner.pack(pady=18)
        tk.Label(inner, text="Có tài khoản? ", font=("Segoe UI", 10), bg=CARD_BG, fg=TEXT).pack(side="left")
        link = tk.Label(inner, text="Đăng nhập", font=("Segoe UI", 10, "bold"), bg=CARD_BG, fg=BLUE, cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>", lambda _: messagebox.showinfo("Demo", "Đây là form học Tkinter, không có chức năng thật."))

    def _add_field(self, parent, placeholder, show=None):
        entry = PlaceholderEntry(parent, placeholder, show=show, style="Field.TEntry", font=("Segoe UI", 10))
        entry.pack(fill="x", padx=40, pady=4, ipady=2)
        return entry

    def _password_strength(self, pw):
        if len(pw) < 6:
            return "Yếu", "#ed4956"
        score = 0
        if re.search(r"[a-z]", pw): score += 1
        if re.search(r"[A-Z]", pw): score += 1
        if re.search(r"\d", pw): score += 1
        if re.search(r"[^\w\s]", pw): score += 1
        if len(pw) >= 10: score += 1
        if score <= 2: return "Trung bình", "#f0a500"
        return "Mạnh", "#2ecc71"

    def _update_strength(self, _):
        pw = self.password.value()
        if not pw:
            self.strength_var.set("")
            return
        label, color = self._password_strength(pw)
        self.strength_var.set(f"Độ mạnh: {label}")

    def _validate_form(self, _=None):
        ok = all(e.value().strip() for e in (self.email, self.fullname, self.username, self.password))
        if ok:
            self.signup_btn.configure(state="normal", bg=BLUE)
        else:
            self.signup_btn.configure(state="disabled", bg=BLUE_DISABLED)

    def _on_signup(self):
        messagebox.showinfo(
            "Demo",
            "Đây chỉ là giao diện học Tkinter — không gửi dữ liệu đi đâu cả.\n\n"
            f"Email/SĐT: {self.email.value()}\n"
            f"Tên: {self.fullname.value()}\n"
            f"Username: {self.username.value()}",
        )


if __name__ == "__main__":
    SignupApp().mainloop()
