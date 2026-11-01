"""Reusable shell components shared by all DELIMOLD data tabs."""
import tkinter as tk

from .app_window_theme import CARD, GREEN, INK, LINE, MUTED, PALE, WHITE


TAB_LABELS = {
    "molds": "Data Cetakan", "containers": "Data Container", "patterns": "Data Pattern",
    "stickers": "Data Sticker", "projects": "Development Project",
    "purchases": "Pembelian Mold", "accounts": "Management Akun", "history": "Riwayat perubahan",
}


class SidebarNavItem(tk.Canvas):
    """Rounded, preview-matched navigation row with a clear active marker."""

    def __init__(self, parent, label, command, selected=False):
        super().__init__(parent, width=180, height=40, bg=WHITE, bd=0,
                         highlightthickness=0, relief="flat")
        self.label = label
        self.command = command
        self.selected = selected
        self.hovered = False
        self.bind("<Button-1>", lambda _event: self.command())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Configure>", lambda _event: self._draw())
        self._draw()

    def configure(self, cnf=None, **kwargs):
        bg = kwargs.pop("bg", kwargs.pop("background", None))
        kwargs.pop("fg", kwargs.pop("foreground", None))
        if bg is not None:
            self.selected = bg == PALE
            self._draw()
        if kwargs:
            super().configure(cnf, **kwargs)

    config = configure

    def _on_enter(self, _event):
        self.hovered = True
        self._draw()

    def _on_leave(self, _event):
        self.hovered = False
        self._draw()

    def _draw(self):
        self.delete("all")
        width = max(self.winfo_width(), 180)
        height = max(self.winfo_height(), 40)
        if self.selected:
            fill = PALE
        elif self.hovered:
            fill = "#26352b"
        else:
            fill = WHITE
        radius = 7
        points = [
            radius, 2, width-radius, 2, width-2, radius+2, width-2, height-radius-2,
            width-radius, height-2, radius, height-2, 2, height-radius-2, 2, radius+2,
        ]
        self.create_polygon(points, smooth=True, splinesteps=16, fill=fill, outline=fill)
        icon_color = GREEN if not self.selected else GREEN
        text_color = INK if self.selected else MUTED
        if self.selected:
            self.create_line(3, 10, 3, height-10, fill=GREEN, width=3, capstyle="round")
        self.create_text(17, height/2, text="▤", anchor="w", fill=icon_color,
                         font=("Segoe UI", 9))
        self.create_text(34, height/2, text=self.label, anchor="w", fill=text_color,
                         font=("Segoe UI", 9))


class RoundedScrollbar(tk.Canvas):
    """Compact canvas scrollbar with rounded track and thumb."""

    def __init__(self, parent, command, width=14):
        self.command = command
        self.thumb = (0.0, 1.0)
        self.hovered = False
        self.drag_offset = None
        super().__init__(parent, width=width, bd=0, highlightthickness=0,
                         relief="flat", bg=parent.cget("bg"), cursor="hand2")
        self.bind("<Configure>", lambda _event: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", self._release)
        self._draw()

    def set(self, first, last):
        self.thumb = (float(first), float(last))
        self._draw()

    def _on_enter(self, _event):
        self.hovered = True
        self._draw()

    def _on_leave(self, _event):
        self.hovered = False
        self._draw()

    def _bounds(self):
        height = max(self.winfo_height(), 20)
        top = max(2, int(self.thumb[0] * height))
        bottom = min(height - 2, int(self.thumb[1] * height))
        if bottom - top < 24:
            bottom = min(height - 2, top + 24)
            top = max(2, bottom - 24)
        return top, bottom

    def _draw(self):
        self.delete("all")
        width = max(self.winfo_width(), 14)
        height = max(self.winfo_height(), 20)
        center = width // 2
        self._pill(center, 2, height - 2, "#27352c")
        top, bottom = self._bounds()
        color = GREEN if self.hovered else "#718477"
        self._pill(center, top, bottom, color)

    def _pill(self, center, top, bottom, color):
        radius = max(2, (self.winfo_width() - 6) // 2)
        x1, x2 = center - radius, center + radius
        self.create_rectangle(x1, top + radius, x2, bottom - radius,
                              fill=color, outline=color)
        self.create_oval(x1, top, x2, top + 2 * radius,
                         fill=color, outline=color)
        self.create_oval(x1, bottom - 2 * radius, x2, bottom,
                         fill=color, outline=color)

    def _press(self, event):
        top, bottom = self._bounds()
        height = max(self.winfo_height(), 1)
        if top <= event.y <= bottom:
            self.drag_offset = (event.y - top) / height
            return
        self.command("scroll", -1 if event.y < top else 1, "pages")

    def _drag(self, event):
        if self.drag_offset is None:
            return
        height = max(self.winfo_height(), 1)
        fraction = max(0.0, min(1.0, event.y / height - self.drag_offset))
        self.command("moveto", str(fraction))

    def _release(self, _event):
        self.drag_offset = None


def build_sidebar(parent, role, mode, selected, on_select, on_settings=None):
    sidebar = tk.Frame(parent, bg=WHITE, width=205, highlightbackground=LINE, highlightthickness=1)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)
    brand = tk.Frame(sidebar, bg=WHITE)
    brand.pack(fill="x", padx=14, pady=(19, 16))
    tk.Label(brand, text="M", bg=GREEN, fg="#102017", font=("Georgia", 18), width=2, height=1).pack(side="left", padx=(0, 8))
    tk.Label(brand, text="DELIMOLD\nDATA CETAKAN BAN", bg=WHITE, fg=INK, justify="left", font=("Segoe UI", 10, "bold")).pack(side="left")

    visible_tabs = ["molds", "containers", "patterns", "stickers"]
    if role in ("SUPERVISOR", "ENGINEER"):
        visible_tabs.append("projects")
    if role == "SUPERVISOR":
        visible_tabs.extend(("purchases", "accounts", "history"))
    if mode == "viewer":
        visible_tabs = ["molds", "containers", "patterns", "stickers"]
    buttons = {}
    for key in visible_tabs:
        button = SidebarNavItem(
            sidebar, TAB_LABELS[key], lambda item=key: on_select(item), selected=(key == selected))
        button.pack(fill="x", padx=8, pady=2)
        buttons[key] = button
    if mode == "master" and role == "SUPERVISOR" and on_settings:
        button = SidebarNavItem(sidebar, "Atur lokasi data", on_settings,
                                selected=(selected == "settings"))
        button.pack(fill="x", padx=8, pady=2)
        buttons["settings"] = button
    tk.Frame(sidebar, bg=WHITE).pack(fill="both", expand=True)
    build_shared_footer(sidebar)
    return sidebar, buttons


def build_shared_footer(parent):
    """Keep the common policy note at the bottom of the shared sidebar."""
    footer = tk.Frame(parent, bg=CARD, padx=10, pady=10)
    footer.pack(fill="x", padx=11, pady=9)
    tk.Label(footer, text="Satu sumber data.\nHak akses mengikuti peran.", bg=CARD, fg=MUTED,
             justify="left", font=("Segoe UI", 8)).pack(anchor="w")
    return footer


def build_header(parent, role, mode):
    header = tk.Frame(parent, bg=WHITE, height=46, highlightbackground=LINE, highlightthickness=1)
    header.pack(fill="x")
    header.pack_propagate(False)
    crumb = tk.Label(header, text="DELIMOLD · Data Cetakan Ban", bg=WHITE, fg=INK,
                     font=("Segoe UI", 9))
    crumb.pack(side="left", padx=17)
    label = "TENDERLOIN  ·  %s" % role if mode != "viewer" else "SALAK  ·  Viewer"
    tk.Label(header, text=label, bg=WHITE, fg=INK, font=("Segoe UI", 8)).pack(side="right", padx=14)
    return header, crumb


def build_database_status(parent, mode):
    frame = tk.Frame(parent, bg=WHITE, highlightbackground=LINE, highlightthickness=1)
    frame.pack(fill="x", pady=(13, 12))
    tk.Label(frame, text="●", bg=WHITE, fg=GREEN, font=("Segoe UI", 12)).pack(side="left", padx=(12, 6), pady=9)
    text = "Salinan baca-saja · publikasi SALAK" if mode == "viewer" else "Data utama · TENDERLOIN"
    label = tk.Label(frame, text=text, bg=WHITE, fg=GREEN, font=("Segoe UI", 9, "bold"))
    label.pack(side="left", pady=9)
    return frame, label
