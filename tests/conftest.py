"""Generated assets shared by real FFmpeg and Qt integration tests."""

import pytest
from PySide6.QtWidgets import QMessageBox

from scripts.generate_fixtures import generate


@pytest.fixture(scope="session")
def media_files(tmp_path_factory):
    return generate(tmp_path_factory.mktemp("media"))


@pytest.fixture(autouse=True)
def isolated_editor_data(tmp_path, monkeypatch):
    """Keep recovery files out of user data; explicitly discard test-only edits on close."""
    monkeypatch.setenv("ASTRA_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(
        QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Discard
    )
