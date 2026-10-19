"""Ask an AI model to explain a drug label in plain language."""

import anthropic

MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """You explain official FDA drug labels to ordinary people, such as a patient,
a parent, or someone caring for an older relative. Use only what the label says; never add
facts, doses, or advice that aren't in it. Write at about an 8th-grade reading level, in short
sentences, with no medical jargon (or explain a term the first time you use it).

Structure the answer with these headings, skipping any the label doesn't cover:
What it's for, How to take it, Don't take it if, Watch out for, Mixing with other medicines,
When to call a doctor.

End with one line reminding the reader to check with their pharmacist or doctor, because this
is a summary of the label and not medical advice."""


def explain_label(info: dict, language: str = "English", client: anthropic.Anthropic | None = None) -> str:
    client = client or anthropic.Anthropic()
    name = info["brand_name"] or info["generic_name"] or "this medicine"
    label_text = "\n\n".join(f"## {title}\n{text}" for title, text in info["sections"].items())
    prompt = (
        f"Explain this label for {name} ({info['generic_name'] or 'generic name unknown'}). "
        f"Write the explanation in {language}.\n\n<label>\n{label_text}\n</label>"
    )

    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        output_config={"effort": "medium"},
        # If a safety check declines the request, the API retries it on a fallback model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("The model declined to explain this label.")
    return "".join(block.text for block in response.content if block.type == "text")
