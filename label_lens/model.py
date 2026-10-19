"""Shared helper for calling the AI model."""

import anthropic

MODEL = "claude-opus-5-5"


def ask(content, system: str, client: anthropic.Anthropic | None = None, **options) -> str:
    """Send one message and return the text of the reply."""
    client = client or anthropic.Anthropic()
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=system,
        output_config=options.pop("output_config", {"effort": "medium"}),
        # If a safety check declines the request, the API retries it on a fallback model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": content}],
        **options,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("The model declined this request.")
    return "".join(block.text for block in response.content if block.type == "text")
