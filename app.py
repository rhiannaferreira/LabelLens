"""Label Lens web API. The website in public/ calls these routes.

Run locally:  uvicorn app:app --reload   then open http://localhost:8000
"""

import base64
import binascii
import os
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from label_lens.explain import check_interactions, display_name, explain_label
from label_lens.fda import DrugNotFound, label_info, search_label
from label_lens.vision import read_packaging

PUBLIC = Path(__file__).parent / "public"
MAX_IMAGE_BYTES = 3_000_000  # Vercel caps request bodies at 4.5 MB; base64 adds a third
LANGUAGES = {"English", "Spanish", "Chinese (Simplified)", "Vietnamese", "Tagalog", "Korean",
             "Portuguese", "Hindi", "Arabic", "French", "Russian"}

app = FastAPI(title="Label Lens")


def check_access(x_access_code: str | None = Header(default=None)) -> None:
    """If APP_ACCESS_CODE is set, the AI routes need it, so strangers can't spend your API credit."""
    expected = os.environ.get("APP_ACCESS_CODE")
    if expected and x_access_code != expected:
        raise HTTPException(401, "Enter the access code to use the AI features.")


@lru_cache(maxsize=256)
def get_info(name: str) -> dict:
    return label_info(search_label(name))


def lookup(name: str) -> dict:
    name = name.strip()
    if not name:
        raise HTTPException(400, "Enter a medicine name.")
    try:
        return get_info(name.lower())
    except DrugNotFound:
        raise HTTPException(404, f"No FDA label found for “{name}”. Check the spelling or try the generic name.")
    except Exception:
        raise HTTPException(502, "Couldn't reach the FDA label service. Try again in a moment.")


def check_language(language: str) -> str:
    if language not in LANGUAGES:
        raise HTTPException(400, "Unsupported language.")
    return language


class ExplainRequest(BaseModel):
    name: str = Field(max_length=100)
    language: str = "English"


class PhotoRequest(BaseModel):
    image: str  # base64-encoded image
    media_type: str = "image/jpeg"


class InteractionsRequest(BaseModel):
    names: list[str] = Field(min_length=2, max_length=10)
    language: str = "English"


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(PUBLIC / "index.html")


@app.get("/api/config")
def config():
    return {"access_code_required": bool(os.environ.get("APP_ACCESS_CODE")), "languages": sorted(LANGUAGES)}


@app.get("/api/label")
def label(name: str):
    info = lookup(name)
    return {**info, "display_name": display_name(info)}


@app.post("/api/explain", dependencies=[Depends(check_access)])
def explain(req: ExplainRequest):
    info = lookup(req.name)
    try:
        return {"explanation": explain_label(info, language=check_language(req.language))}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Couldn't get an explanation right now. Try again in a moment.")


@app.post("/api/photo", dependencies=[Depends(check_access)])
def photo(req: PhotoRequest):
    if req.media_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(400, "Use a JPG, PNG or WEBP photo.")
    try:
        image = base64.b64decode(req.image, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(400, "That photo couldn't be read.")
    if len(image) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "That photo is too large.")
    try:
        found = read_packaging(image, req.media_type)
    except Exception:
        raise HTTPException(502, "Couldn't read the photo right now. Try again in a moment.")
    if not found["found"] or not (found["name"] or found["active_ingredient"]):
        raise HTTPException(422, "Couldn't make out a medicine name. Try a sharper photo of the front of the box.")
    return found


@app.post("/api/interactions", dependencies=[Depends(check_access)])
def interactions(req: InteractionsRequest):
    infos = [lookup(name) for name in req.names]
    try:
        return {"result": check_interactions(infos, language=check_language(req.language))}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Couldn't check your medicines right now. Try again in a moment.")


# On Vercel the CDN serves public/ directly. Locally, serve it from here.
if not os.environ.get("VERCEL"):
    app.mount("/", StaticFiles(directory=PUBLIC), name="public")
