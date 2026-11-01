"""Authentication screens and flows for the Tk desktop adapter."""
import socket
import tkinter as tk
from tkinter import ttk

from app.application.dto import AuthenticationRequest, InitialSupervisorRequest
from app.domain.models import Actor
from .error_presenter import present_error
from .app_window_theme import GREEN, INK, MUTED

class AuthenticationMixin:

    def _login(self):
        if self.mode == "viewer":
            self.account = Actor("viewer", "Viewer SALAK", "VIEWER")
            return
        if self.use_cases.needs_initial_setup():
            self._setup_supervisor()
        if self.root.winfo_exists():
            self._local_login()

    def _setup_supervisor(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Setup Supervisor · DELIMOLD")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        box = ttk.Frame(dlg, padding=22)
        box.pack(fill="both", expand=True)
        ttk.Label(box, text="Buat akun Supervisor", font=("Segoe UI", 15, "bold"), foreground=INK).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        ttk.Label(box, text="Akun pertama disimpan pada database lokal.", foreground=MUTED).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 14))
        fields = {}
        for row, label in enumerate(("Nama akun", "Nama tampilan", "Password (4–12 karakter)", "Ulangi password"), 2):
            ttk.Label(box, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
            entry = ttk.Entry(box, width=34, show="•" if "Password" in label or "Ulangi" in label else "")
            entry.grid(row=row, column=1, sticky="ew", pady=5)
            fields[label] = entry
        error = tk.StringVar()
        ttk.Label(box, textvariable=error, foreground="#a34739").grid(row=6, column=0, columnspan=2, sticky="w", pady=5)
        def submit():
            username = fields["Nama akun"].get().strip()
            display = fields["Nama tampilan"].get().strip()
            pw = fields["Password (4–12 karakter)"].get()
            again = fields["Ulangi password"].get()
            try:
                if pw != again:
                    raise ValueError("Password belum sama")
                self.use_cases.setup_initial_supervisor(
                    InitialSupervisorRequest(username, display, pw))
                dlg.destroy()
            except Exception as exc:
                error.set(present_error(exc))
        ttk.Button(box, text="Buat akun", command=submit).grid(row=7, column=1, sticky="e", pady=(9, 0))
        dlg.protocol("WM_DELETE_WINDOW", self.root.destroy)
        dlg.wait_window()

    def _local_login(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Login DELIMOLD")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        box = ttk.Frame(dlg, padding=22)
        box.pack(fill="both", expand=True)
        ttk.Label(box, text="DELI MOLD", font=("Segoe UI", 17, "bold"), foreground=GREEN).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(box, text="Masuk ke data utama TENDERLOIN", foreground=MUTED).grid(row=1, column=0, columnspan=2, sticky="w", pady=(3, 16))
        ttk.Label(box, text="Nama akun").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=5)
        username = ttk.Entry(box, width=32)
        username.grid(row=2, column=1, pady=5)
        ttk.Label(box, text="Password").grid(row=3, column=0, sticky="w", padx=(0, 12), pady=5)
        password = ttk.Entry(box, width=32, show="•")
        password.grid(row=3, column=1, pady=5)
        error = tk.StringVar()
        ttk.Label(box, textvariable=error, foreground="#a34739").grid(row=4, column=0, columnspan=2, sticky="w", pady=5)
        def submit(event=None):
            try:
                self.account = self.use_cases.authenticate(AuthenticationRequest(
                    username.get(), password.get(), socket.gethostname()))
                dlg.destroy()
            except Exception as exc:
                error.set(present_error(exc))
                password.delete(0, "end")
                password.focus_set()
        ttk.Button(box, text="Masuk", command=submit).grid(row=5, column=1, sticky="e", pady=(8, 0))
        password.bind("<Return>", submit)
        dlg.protocol("WM_DELETE_WINDOW", self.root.destroy)
        dlg.wait_window()

