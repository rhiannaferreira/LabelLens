import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from label_lens import explain, fda

LABEL = json.loads((Path(__file__).parent / "fixtures" / "ibuprofen_label.json").read_text())


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_search_falls_back_to_generic_name(monkeypatch):
    queries = []

    def fake_get(url, params, timeout):
        queries.append(params["search"])
        if params["search"].startswith("openfda.brand_name"):
            return FakeResponse(404)
        return FakeResponse(200, {"results": [LABEL]})

    monkeypatch.setattr(fda.requests, "get", fake_get)
    assert fda.search_label("ibuprofen")["id"] == "sample-ibuprofen-0001"
    assert queries == ['openfda.brand_name:"ibuprofen"', 'openfda.generic_name:"ibuprofen"']


def test_search_raises_when_nothing_matches(monkeypatch):
    monkeypatch.setattr(fda.requests, "get", lambda url, params, timeout: FakeResponse(404))
    with pytest.raises(fda.DrugNotFound):
        fda.search_label("notarealdrug")


def test_label_info_keeps_readable_sections_in_order():
    info = fda.label_info(LABEL)
    assert info["brand_name"] == "Advil"
    assert info["generic_name"] == "IBUPROFEN"
    assert list(info["sections"]) == [
        "Purpose",
        "What it's for",
        "How to take it",
        "Warnings",
        "Ask a doctor or pharmacist before use",
    ]


def test_explain_sends_label_and_language_to_model():
    captured = {}

    class FakeMessages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="Para qué sirve...")])

    fake_client = SimpleNamespace(beta=SimpleNamespace(messages=FakeMessages()))
    out = explain.explain_label(fda.label_info(LABEL), language="Spanish", client=fake_client)

    assert out == "Para qué sirve..."
    prompt = captured["messages"][0]["content"]
    assert "Spanish" in prompt and "aspirin" in prompt
    assert captured["model"] == "claude-opus-5-5"
