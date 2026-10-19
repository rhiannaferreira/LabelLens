"""Look up official drug labels from the openFDA API (https://open.fda.gov/apis/drug/label/)."""

import requests

LABEL_URL = "https://api.fda.gov/drug/label.json"

# Label sections worth explaining, in reading order. Prescription labels and
# over-the-counter "Drug Facts" labels use different fields, so we list both.
SECTIONS = {
    "boxed_warning": "Boxed warning",
    "purpose": "Purpose",
    "indications_and_usage": "What it's for",
    "dosage_and_administration": "How to take it",
    "contraindications": "Do not use if",
    "do_not_use": "Do not use",
    "warnings_and_cautions": "Warnings",
    "warnings": "Warnings",
    "ask_doctor": "Ask a doctor before use",
    "ask_doctor_or_pharmacist": "Ask a doctor or pharmacist before use",
    "drug_interactions": "Drug interactions",
    "when_using": "When using this product",
    "stop_use": "Stop use and ask a doctor if",
    "pregnancy_or_breast_feeding": "Pregnancy or breastfeeding",
    "adverse_reactions": "Side effects",
}


class DrugNotFound(Exception):
    pass


def search_label(name: str, timeout: float = 10.0) -> dict:
    """Return the best-matching label record for a brand or generic drug name."""
    name = name.strip().replace('"', "")
    for field in ("openfda.brand_name", "openfda.generic_name"):
        resp = requests.get(
            LABEL_URL,
            params={"search": f'{field}:"{name}"', "limit": 1},
            timeout=timeout,
        )
        if resp.status_code == 404:  # openFDA returns 404 when nothing matches
            continue
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if results:
            return results[0]
    raise DrugNotFound(f"No FDA label found for {name!r}")


def label_info(label: dict) -> dict:
    """Pull out the drug's names and the readable sections of a label record."""
    openfda = label.get("openfda", {})
    sections = {}
    for field, title in SECTIONS.items():
        if field in label and title not in sections:
            sections[title] = "\n".join(label[field]).strip()
    return {
        "brand_name": ", ".join(openfda.get("brand_name", [])) or None,
        "generic_name": ", ".join(openfda.get("generic_name", [])) or None,
        "manufacturer": ", ".join(openfda.get("manufacturer_name", [])) or None,
        "label_id": label.get("id"),
        "sections": sections,
    }
