from __future__ import annotations

import json
import shutil
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from config import NOTEBOOKS_DIR
from models import Notebook, utc_now


class StorageBackend(ABC):
    @abstractmethod
    def create_notebook(self, name: str) -> Notebook: ...

    @abstractmethod
    def list_notebooks(self) -> list[Notebook]: ...

    @abstractmethod
    def rename_notebook(self, notebook_id: str, new_name: str) -> Notebook: ...

    @abstractmethod
    def delete_notebook(self, notebook_id: str) -> None: ...


class LocalStorage(StorageBackend):
    """File-backed storage organized by immutable notebook UUID."""

    def __init__(self, root: Path = NOTEBOOKS_DIR):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, notebook_id: str) -> Path:
        # UUID validation prevents path traversal and accidental cross-notebook access.
        safe_id = str(uuid.UUID(notebook_id))
        return self.root / safe_id

    def _json_read(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return default

    def _json_write(self, path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(path)

    def create_notebook(self, name: str) -> Notebook:
        clean = name.strip()
        if not clean:
            raise ValueError("Notebook name cannot be empty.")
        notebook = Notebook(id=str(uuid.uuid4()), name=clean)
        base = self.path(notebook.id)
        for child in ("raw", "extracted", "vector_db", "chats", "artifacts"):
            (base / child).mkdir(parents=True, exist_ok=True)
        self._json_write(base / "metadata.json", notebook.to_dict())
        self._json_write(base / "sources.json", [])
        self._json_write(base / "chats" / "history.json", [])
        return notebook

    def list_notebooks(self) -> list[Notebook]:
        notebooks: list[Notebook] = []
        for metadata in self.root.glob("*/metadata.json"):
            value = self._json_read(metadata, None)
            if value:
                try:
                    notebooks.append(Notebook(**value))
                except TypeError:
                    continue
        return sorted(notebooks, key=lambda item: item.updated_at, reverse=True)

    def get_notebook(self, notebook_id: str) -> Notebook:
        value = self._json_read(self.path(notebook_id) / "metadata.json", None)
        if not value:
            raise KeyError("Notebook not found.")
        return Notebook(**value)

    def rename_notebook(self, notebook_id: str, new_name: str) -> Notebook:
        clean = new_name.strip()
        if not clean:
            raise ValueError("Notebook name cannot be empty.")
        notebook = self.get_notebook(notebook_id)
        notebook.name = clean
        notebook.updated_at = utc_now()
        self._json_write(self.path(notebook_id) / "metadata.json", notebook.to_dict())
        return notebook

    def delete_notebook(self, notebook_id: str) -> None:
        directory = self.path(notebook_id)
        if not directory.exists():
            raise KeyError("Notebook not found.")
        shutil.rmtree(directory)

    def touch(self, notebook_id: str) -> None:
        notebook = self.get_notebook(notebook_id)
        notebook.updated_at = utc_now()
        self._json_write(self.path(notebook_id) / "metadata.json", notebook.to_dict())

    def sources(self, notebook_id: str) -> list[dict[str, Any]]:
        return self._json_read(self.path(notebook_id) / "sources.json", [])

    def add_source(self, notebook_id: str, source: dict[str, Any]) -> None:
        items = self.sources(notebook_id)
        items.append(source)
        self._json_write(self.path(notebook_id) / "sources.json", items)
        self.touch(notebook_id)

    def history(self, notebook_id: str) -> list[dict[str, str]]:
        return self._json_read(
            self.path(notebook_id) / "chats" / "history.json", []
        )

    def save_history(self, notebook_id: str, history: list[dict[str, str]]) -> None:
        self._json_write(
            self.path(notebook_id) / "chats" / "history.json", history
        )
        self.touch(notebook_id)

    def clear_history(self, notebook_id: str) -> None:
        self.save_history(notebook_id, [])

    def save_artifact(self, notebook_id: str, filename: str, content: str) -> Path:
        safe_name = Path(filename).name
        if not safe_name.endswith(".md"):
            raise ValueError("Artifacts must be Markdown files.")
        output = self.path(notebook_id) / "artifacts" / safe_name
        output.write_text(content, encoding="utf-8")
        self.touch(notebook_id)
        return output

    def artifacts(self, notebook_id: str) -> list[Path]:
        return sorted(
            (self.path(notebook_id) / "artifacts").glob("*.md"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

