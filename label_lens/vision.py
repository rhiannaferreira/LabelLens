"""Read a medicine's name and strength from a photo of its box or bottle."""

import base64
import json

import anthropic

from label_lens.model import ask

READ_PROMPT = """You read photos of medicine packaging. Find the medicine's brand name (or the
generic name if there's no brand), its active ingredient, and its strength (for example
"200 mg"). Read only what's printed; don't guess. If you can't read the packaging, set found to
false."""

SCHEMA = {
    "type": "object",
    "properties": {
        "found": {"type": "boolean"},
        "name": {"type": "string"},
        "active_ingredient": {"type": "string"},
        "strength": {"type": "string"},
    },
    "required": ["found", "name", "active_ingredient", "strength"],
    "additionalProperties": False,
}

MEDIA_TYPES = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif"}


def read_packaging(image: bytes, media_type: str, client: anthropic.Anthropic | None = None) -> dict:
    """Return {"found", "name", "active_ingredient", "strength"} read from the photo."""
    content = [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": base64.b64encode(image).decode()},
        },
        {"type": "text", "text": "What medicine is this?"},
    ]
    text = ask(
        content,
        READ_PROMPT,
        client=client,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
    )
    return json.loads(text)


def media_type_for(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in MEDIA_TYPES:
        raise ValueError(f"Unsupported image type: .{ext}. Use JPG, PNG, WEBP or GIF.")
    return MEDIA_TYPES[ext]
