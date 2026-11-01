"""JSON adapter for the packaged initial catalog."""
import json
from pathlib import Path

from app.application.ports import SeedCatalogReader
from app.domain.errors import StorageError


class JsonSeedCatalogReader(SeedCatalogReader):
    def read(self, path):
        try:
            with Path(path).open("r", encoding="utf-8") as stream:
                catalog = json.load(stream)
            if not isinstance(catalog, dict) or not isinstance(catalog.get("collections"), dict):
                raise ValueError("format katalog awal tidak valid")
            return catalog
        except (OSError, ValueError) as exc:
            raise StorageError("Katalog awal DELIMOLD tidak dapat dibaca.") from exc
