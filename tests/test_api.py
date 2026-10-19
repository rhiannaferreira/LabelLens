"""Test the web API with the FDA and AI calls replaced by fakes."""

import base64
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app as web
from label_lens import fda

LABEL = json.loads((Path(__file__).parent / "fixtures" / "ibuprofen_label.json").read_text())


@pytest.fixture
def client(monkeypatch):
    web.get_info.cache_clear()
    monkeypatch.delenv("APP_ACCESS_CODE", raising=False)

    def fake_search(name):
        if name == "notarealdrug":
            raise fda.DrugNotFound(name)
        return LABEL

    monkeypatch.setattr(web, "search_label", fake_search)
    monkeypatch.setattr(web, "explain_label", lambda info, language: f"Explained in {language}")
    monkeypatch.setattr(web, "check_interactions", lambda infos, language: f"Checked {len(infos)}")
    monkeypatch.setattr(web, "read_packaging", lambda image, media_type: {
        "found": True, "name": "Advil", "active_ingredient": "ibuprofen", "strength": "200 mg"})
    return TestClient(web.app)


def test_home_serves_the_website(client):
    res = client.get("/")
    assert res.status_code == 200 and "Label Lens" in res.text


def test_label_lookup(client):
    res = client.get("/api/label", params={"name": "Advil"})
    assert res.status_code == 200
    assert res.json()["display_name"] == "Advil"


def test_unknown_drug_gives_friendly_404(client):
    res = client.get("/api/label", params={"name": "notarealdrug"})
    assert res.status_code == 404
    assert "No FDA label found" in res.json()["detail"]


def test_explain_and_language_check(client):
    assert client.post("/api/explain", json={"name": "Advil", "language": "Spanish"}).json() == {
        "explanation": "Explained in Spanish"}
    assert client.post("/api/explain", json={"name": "Advil", "language": "Klingon"}).status_code == 400


def test_photo(client):
    image = base64.b64encode(b"fake jpeg bytes").decode()
    res = client.post("/api/photo", json={"image": image, "media_type": "image/jpeg"})
    assert res.status_code == 200 and res.json()["name"] == "Advil"
    assert client.post("/api/photo", json={"image": "not base64!!", "media_type": "image/jpeg"}).status_code == 400
    assert client.post("/api/photo", json={"image": image, "media_type": "image/heic"}).status_code == 400


def test_interactions_need_two(client):
    assert client.post("/api/interactions", json={"names": ["Advil", "Tylenol"]}).json() == {"result": "Checked 2"}
    assert client.post("/api/interactions", json={"names": ["Advil"]}).status_code == 422


def test_access_code(client, monkeypatch):
    monkeypatch.setenv("APP_ACCESS_CODE", "secret")
    assert client.get("/api/config").json()["access_code_required"] is True
    assert client.post("/api/explain", json={"name": "Advil"}).status_code == 401
    ok = client.post("/api/explain", json={"name": "Advil"}, headers={"X-Access-Code": "secret"})
    assert ok.status_code == 200
    assert client.get("/api/label", params={"name": "Advil"}).status_code == 200  # FDA lookups stay open
