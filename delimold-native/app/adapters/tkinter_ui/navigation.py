"""Main catalog and location-settings navigation for the Tk adapter."""
import tkinter as tk
from app.application.dto import LocationUpdateRequest
from app.domain.models import AppConfig
from .location_settings import build_location_settings
from .app_window_theme import INK, PALE, WHITE, MUTED
from .catalog_config import TABS

class NavigationMixin:

    def _show_catalog_page(self):
        for child in self.content_host.winfo_children():
            child.destroy()
        self.current_view = "catalog"
        self.crumb_label.configure(text="DELIMOLD · " + TABS[self.collection])
        for key, button in self.nav_buttons.items():
            selected = key == self.collection
            button.configure(bg=PALE if selected else WHITE, fg=INK if selected else MUTED)
        self._render_catalog_content()

    def _back_to_catalog(self):
        self._show_catalog_page()
        self.refresh()

    def configure_locations(self):
        if self.mode != "master" or self.account.role != "SUPERVISOR":
            return
        for child in self.content_host.winfo_children():
            child.destroy()
        self.current_view = "settings"
        self.crumb_label.configure(text="DELIMOLD · Atur lokasi data")
        for key, button in self.nav_buttons.items():
            selected = key == "settings"
            button.configure(bg=PALE if selected else WHITE, fg=INK if selected else MUTED)

        def on_saved(previous, updated, database_path):
            result = self.use_cases.update_locations(LocationUpdateRequest(
                self.account, AppConfig.from_mapping(previous), AppConfig.from_mapping(updated)))
            self.config.update(updated)
            return result.message if result.publication_pending else None

        page = build_location_settings(self.content_host, self.base_dir, dict(self.config),
                                       on_saved=on_saved, on_back=self._back_to_catalog)
        self.location_status_label = page.status_label

    def select_collection(self, collection):
        self.collection = collection
        self.page_index = 0
        self._page_stats = None
        if getattr(self, "current_view", "catalog") == "settings":
            self._show_catalog_page()
            self.refresh()
            return
        for key, button in self.nav_buttons.items():
            button.configure(bg=PALE if key == collection else WHITE, fg=INK if key == collection else MUTED)
        self.title_label.configure(text=TABS[collection])
        self.crumb_label.configure(text="DELIMOLD · " + TABS[collection])
        self.list_label.configure(text="Daftar " + TABS[collection].lower())
        for button in getattr(self, "row_action_buttons", []):
            disabled = collection == "history" or (button is getattr(self, "toggle_button", None) and collection == "purchases")
            button.configure(state="disabled" if disabled else "normal")
        self._update_toolbar()
        self._build_filters()
        self.refresh()

