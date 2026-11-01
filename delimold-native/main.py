"""Entry point for the no-browser DELIMOLD native application."""
import json
import os
import sys
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

from delimold.network import CatalogApi, CatalogClient
from delimold.store import CatalogStore
from delimold.ui import NativeApp


def app_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resolve_path(base, value):
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else base / path


def load_config(base):
    path = base / "config.json"
    if not path.exists():
        return {"mode": "master", "database_path": "Database/delimold.sqlite3", "api_host": "0.0.0.0", "api_port": 8766}
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def main():
    base = app_root()
    config = load_config(base)
    mode = config.get("mode", "master")
    root = tk.Tk()
    root.withdraw()
    store = None
    api = None
    client = None
    snapshot = None
    try:
        if mode == "master":
            database = resolve_path(base, config.get("database_path", "Database/delimold.sqlite3"))
            store = CatalogStore(database)
            seed_path = resolve_path(base, config.get("seed_path", "seed/catalog.js"))
            if seed_path and seed_path.exists():
                store.seed_from_js(seed_path)
            publish_path = resolve_path(base, config.get("publish_path", ""))
            if publish_path and config.get("publish_on_start", True):
                try:
                    store.publish(publish_path)
                except Exception as exc:
                    messagebox.showwarning("Publikasi SALAK belum siap",
                                           "Data utama tetap dapat dipakai, tetapi snapshot SALAK belum dibuat.\n\n%s" % exc,
                                           parent=root)
            api = CatalogApi(store, config.get("api_host", "0.0.0.0"), config.get("api_port", 8765), publish_path)
            api.start()
        elif mode == "client":
            client = CatalogClient(config.get("server_host", "TENDERLOIN"), config.get("api_port", 8765))
        elif mode == "viewer":
            snapshot = {"snapshot_path": str(resolve_path(base, config.get("snapshot_path", "published/catalog.json")))}
        else:
            raise ValueError("Mode config harus master, client, atau viewer")
        root.deiconify()
        NativeApp(root, config, store=store, api_client=client, viewer_snapshot=snapshot, api_server=api)
        root.mainloop()
    except Exception as exc:
        try:
            messagebox.showerror("DELIMOLD tidak dapat dimulai", str(exc), parent=root)
        except Exception:
            pass
        if api:
            api.stop()
        if store:
            store.close()
        root.destroy()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

