"""Smoke test the web app with the FDA and AI calls replaced by fakes."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from label_lens import explain, fda

LABEL = json.loads((Path(__file__).parent / "fixtures" / "ibuprofen_label.json").read_text())
APP = str(Path(__file__).parent.parent / "app.py")


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setattr(fda, "search_label", lambda name: LABEL)
    monkeypatch.setattr(explain, "ask", lambda *a, **k: "## What it's for\nPain and fever.")
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    return at


def test_app_starts_with_empty_medicine_list(app):
    assert not app.exception
    assert app.title[0].value == "Label Lens"


def test_looking_up_a_medicine_shows_the_explanation(app):
    app.text_input(key="query").input("advil")
    app.button[0].click().run()  # the form's "Look up" button
    assert not app.exception
    assert app.subheader[0].value == "Advil"
    assert any("Pain and fever." in m.value for m in app.markdown)
