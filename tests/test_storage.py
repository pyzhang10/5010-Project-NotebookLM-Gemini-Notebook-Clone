from pathlib import Path

import pytest

from storage import LocalStorage


def test_notebook_crud_and_persistence(tmp_path: Path):
    storage = LocalStorage(tmp_path)
    notebook = storage.create_notebook("Research")
    assert storage.get_notebook(notebook.id).name == "Research"
    assert storage.list_notebooks()[0].id == notebook.id

    renamed = storage.rename_notebook(notebook.id, "Renamed")
    assert renamed.name == "Renamed"

    storage.save_history(notebook.id, [{"role": "user", "content": "hello"}])
    restarted = LocalStorage(tmp_path)
    assert restarted.history(notebook.id)[0]["content"] == "hello"

    storage.delete_notebook(notebook.id)
    assert storage.list_notebooks() == []


def test_blank_name_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        LocalStorage(tmp_path).create_notebook("   ")


def test_artifact_must_be_markdown(tmp_path: Path):
    storage = LocalStorage(tmp_path)
    notebook = storage.create_notebook("Artifacts")
    with pytest.raises(ValueError):
        storage.save_artifact(notebook.id, "unsafe.txt", "text")

