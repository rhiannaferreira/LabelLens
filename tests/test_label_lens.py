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


def fake_client(reply_text, captured):
    class FakeMessages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=reply_text)])

    return SimpleNamespace(beta=SimpleNamespace(messages=FakeMessages()))


def test_warnings_drops_text_repeated_in_other_sections():
    label = {
        "openfda": {"generic_name": ["IBUPROFEN"]},
        "warnings": ["Warnings Allergy alert: may cause a severe allergic reaction. "
                     "Do not use right before or after heart surgery "
                     "When using this product take with food or milk"],
        "do_not_use": ["Do not use right before or after heart surgery"],
        "when_using": ["When using this product take with food or milk"],
    }
    sections = fda.label_info(label)["sections"]
    assert sections["Warnings"] == "Warnings Allergy alert: may cause a severe allergic reaction."
    assert sections["Do not use"] == "Do not use right before or after heart surgery"


def test_warnings_removed_when_nothing_left():
    label = {"warnings": ["Do not use if allergic"], "do_not_use": ["Do not use if allergic"]}
    assert "Warnings" not in fda.label_info(label)["sections"]


def test_read_packaging_sends_image_and_parses_json():
    from label_lens import vision

    captured = {}
    reply = json.dumps({"found": True, "name": "Advil", "active_ingredient": "ibuprofen", "strength": "200 mg"})
    result = vision.read_packaging(b"\x89PNG fake", "image/png", client=fake_client(reply, captured))

    assert result["name"] == "Advil"
    image_block = captured["messages"][0]["content"][0]
    assert image_block["type"] == "image" and image_block["source"]["media_type"] == "image/png"
    assert captured["output_config"]["format"]["type"] == "json_schema"


def test_media_type_rejects_heic():
    from label_lens import vision

    assert vision.media_type_for("Box.JPG") == "image/jpeg"
    with pytest.raises(ValueError):
        vision.media_type_for("IMG_0001.HEIC")


def test_check_interactions_includes_every_label():
    captured = {}
    warfarin = {"brand_name": "Coumadin", "generic_name": "WARFARIN", "manufacturer": None, "label_id": "x",
                "sections": {"Drug interactions": "NSAIDs increase bleeding risk", "What it's for": "clots"}}
    out = explain.check_interactions([fda.label_info(LABEL), warfarin], client=fake_client("Ask your pharmacist.", captured))

    prompt = captured["messages"][0]["content"]
    assert out == "Ask your pharmacist."
    assert 'medicine="Advil"' in prompt and 'medicine="Coumadin"' in prompt
    assert "NSAIDs increase bleeding risk" in prompt
    assert "clots" not in prompt  # only interaction-related sections are sent


def test_check_interactions_needs_two_medicines():
    with pytest.raises(ValueError):
        explain.check_interactions([fda.label_info(LABEL)], client=fake_client("", {}))
