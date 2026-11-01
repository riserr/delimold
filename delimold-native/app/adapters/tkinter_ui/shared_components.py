"""Reusable shell components shared by all DELIMOLD data tabs."""
import tkinter as tk

from .app_window_theme import CARD, GREEN, INK, LINE, MUTED, PALE, WHITE


TAB_LABELS = {
    "molds": "Data Cetakan", "containers": "Data Container", "patterns": "Data Pattern",
    "stickers": "Data Sticker", "projects": "Development Project",
    "purchases": "Pembelian Mold", "accounts": "Management Akun", "history": "Riwayat perubahan",
}


class RoundedPanel(tk.Frame):
    """Frame container with a rounded painted surface and normal Tk children."""

    def __init__(self, parent, fill, border=LINE, radius=8, padx=0, pady=0):
        self.fill = fill
        self.border = border
        self.radius = radius
        self.outer_bg = parent.cget("bg")
        super().__init__(parent, bg=self.outer_bg, bd=0, highlightthickness=0)
        self.canvas = tk.Canvas(self, bg=self.outer_bg, bd=0, highlightthickness=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        inset = max(3, int(radius * 0.55))
        self.content = tk.Frame(self, bg=fill, bd=0, highlightthickness=0,
                                padx=padx, pady=pady)
        self.content.pack(fill="both", expand=True, padx=inset, pady=inset)
        self.bind("<Configure>", lambda _event: self._draw())
        self._draw()

    def _shape(self, x1, y1, x2, y2, radius, fill, outline):
        r = min(radius, max(2, (x2-x1)//2), max(2, (y2-y1)//2))
        points = [x1+r,y1, x2-r,y1, x2,y1+r, x2,y2-r,
                  x2-r,y2, x1+r,y2, x1,y2-r, x1,y1+r]
        self.canvas.create_polygon(points, smooth=True, splinesteps=18,
                                   fill=fill, outline=outline)

    def _draw(self):
        self.canvas.delete("all")
        width, height = max(self.winfo_width(), 2), max(self.winfo_height(), 2)
        self._shape(0, 0, width, height, self.radius, self.border, self.border)
        inset = 1
        self._shape(inset, inset, width-inset, height-inset,
                    max(2, self.radius-1), self.fill, self.fill)


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
        radius = 6
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

    def __init__(self, parent, command, orient="vertical", width=14):
        self.command = command
        self.orient = orient
        self.thumb = (0.0, 1.0)
        self.hovered = False
        self.drag_offset = None
        canvas_width = width if orient == "vertical" else 120
        canvas_height = 120 if orient == "vertical" else width
        super().__init__(parent, width=canvas_width, height=canvas_height, bd=0,
                         highlightthickness=0, relief="flat", bg=parent.cget("bg"),
                         cursor="hand2")
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

    def _length(self):
        return max(self.winfo_height() if self.orient == "vertical" else self.winfo_width(), 20)

    def _bounds(self):
        length = self._length()
        start = max(2, int(self.thumb[0] * length))
        end = min(length - 2, int(self.thumb[1] * length))
        if end - start < 24:
            end = min(length - 2, start + 24)
            start = max(2, end - 24)
        return start, end

    def _draw(self):
        self.delete("all")
        width = max(self.winfo_width(), 14)
        height = max(self.winfo_height(), 14)
        length = height if self.orient == "vertical" else width
        color = GREEN if self.hovered else "#718477"
        if self.orient == "vertical":
            center = width // 2
            self._pill_vertical(center, 2, height - 2, "#27352c", width)
            start, end = self._bounds()
            self._pill_vertical(center, start, end, color, width)
        else:
            center = height // 2
            self._pill_horizontal(2, center, length - 2, "#27352c", height)
            start, end = self._bounds()
            self._pill_horizontal(start, center, end, color, height)

    def _pill_vertical(self, center, top, bottom, color, width):
        radius = max(2, (width - 6) // 2)
        x1, x2 = center - radius, center + radius
        self.create_rectangle(x1, top + radius, x2, bottom - radius, fill=color, outline=color)
        self.create_oval(x1, top, x2, top + 2 * radius, fill=color, outline=color)
        self.create_oval(x1, bottom - 2 * radius, x2, bottom, fill=color, outline=color)

    def _pill_horizontal(self, left, center, right, color, height):
        radius = max(2, (height - 6) // 2)
        y1, y2 = center - radius, center + radius
        self.create_rectangle(left + radius, y1, right - radius, y2, fill=color, outline=color)
        self.create_oval(left, y1, left + 2 * radius, y2, fill=color, outline=color)
        self.create_oval(right - 2 * radius, y1, right, y2, fill=color, outline=color)

    def _press(self, event):
        position = event.y if self.orient == "vertical" else event.x
        start, end = self._bounds()
        length = max(self._length(), 1)
        if start <= position <= end:
            self.drag_offset = (position - start) / length
            return
        self.command("scroll", -1 if position < start else 1, "pages")

    def _drag(self, event):
        if self.drag_offset is None:
            return
        position = event.y if self.orient == "vertical" else event.x
        fraction = max(0.0, min(1.0, position / max(self._length(), 1) - self.drag_offset))
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
    footer = RoundedPanel(parent, fill=CARD, border=LINE, radius=7, padx=10, pady=8)
    footer.pack(fill="x", padx=11, pady=9)
    tk.Label(footer.content, text="Satu sumber data.\nHak akses mengikuti peran.",
             bg=CARD, fg=MUTED, justify="left", font=("Segoe UI", 8)).pack(anchor="w")
    return footer


def build_header(parent, role, mode):
    header = tk.Frame(parent, bg=WHITE, height=48, bd=0, highlightthickness=0)
    header.pack(fill="x")
    header.pack_propagate(False)
    crumb = tk.Label(header, text="DELIMOLD · Data Cetakan Ban", bg=WHITE, fg=MUTED,
                     font=("Segoe UI", 9))
    crumb.pack(side="left", padx=20)
    label = "TENDERLOIN  ·  %s" % role if mode != "viewer" else "SALAK  ·  Viewer"
    tk.Label(header, text=label, bg=WHITE, fg=MUTED, font=("Segoe UI", 8)).pack(side="right", padx=14)
    tk.Frame(header, bg=LINE, height=1).pack(side="bottom", fill="x")
    return header, crumb


def build_database_status(parent, mode):
    frame = RoundedPanel(parent, fill=WHITE, border=LINE, radius=6, padx=11, pady=7)
    frame.pack(fill="x", pady=(14, 11))
    tk.Label(frame.content, text="●", bg=WHITE, fg=GREEN,
             font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))
    text = "Salinan baca-saja · publikasi SALAK" if mode == "viewer" else "Data utama · TENDERLOIN"
    label = tk.Label(frame.content, text=text, bg=WHITE, fg=GREEN,
                     font=("Segoe UI", 9, "bold"))
    label.pack(side="left")
    return frame, label
