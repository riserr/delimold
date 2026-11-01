"""Reusable shell components shared by all DELIMOLD data tabs."""
import tkinter as tk

from .app_window_theme import CARD, GREEN, INK, LINE, MUTED, PALE, WHITE


TAB_LABELS = {
    "molds": "Data Cetakan", "containers": "Data Container", "patterns": "Data Pattern",
    "stickers": "Data Sticker", "projects": "Development Project",
    "purchases": "Pembelian Mold", "accounts": "Management Akun", "history": "Riwayat perubahan",
}


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
        button = tk.Button(sidebar, text="▤   " + TAB_LABELS[key], anchor="w", relief="flat", bd=0,
                           bg=PALE if key == selected else WHITE, fg=INK if key == selected else MUTED,
                           activebackground=PALE, padx=13, pady=10, font=("Segoe UI", 9),
                           command=lambda item=key: on_select(item))
        button.pack(fill="x", padx=8, pady=2)
        buttons[key] = button
    if mode == "master" and role == "SUPERVISOR" and on_settings:
        tk.Button(sidebar, text="⚙   Atur lokasi data", anchor="w", relief="flat", bd=0,
                  bg=WHITE, fg=MUTED, activebackground=PALE, padx=13, pady=10,
                  font=("Segoe UI", 9), command=on_settings).pack(fill="x", padx=8, pady=2)
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
