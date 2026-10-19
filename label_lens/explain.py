"""Ask an AI model to explain drug labels in plain language."""

import anthropic

from label_lens.model import ask

STYLE = """Use only what the label text says; never add facts, doses, or advice that aren't in it.
Write at about an 8th-grade reading level, in short sentences, with no medical jargon (or explain
a term the first time you use it)."""

EXPLAIN_PROMPT = f"""You explain official FDA drug labels to ordinary people, such as a patient,
a parent, or someone caring for an older relative. {STYLE}

Structure the answer with these Markdown headings, skipping any the label doesn't cover:
What it's for, How to take it, Don't take it if, Watch out for, Mixing with other medicines,
When to call a doctor.

End with one line reminding the reader to check with their pharmacist or doctor, because this
is a summary of the label and not medical advice."""

INTERACTIONS_PROMPT = f"""You check a person's list of medicines against the official FDA labels
for those medicines. {STYLE}

Report only combinations that one of the labels warns about, either by name or by a group the
label names (for example "blood thinners" or "other NSAIDs"). For each one, say which medicines,
what the label says could happen, and quote the label's words in quotation marks. If the labels
warn about none of the combinations, say so plainly. Don't speculate about interactions the
labels don't mention.

End with one line telling the reader to show the list to their pharmacist, because labels don't
cover every interaction."""

# Label sections that talk about combining medicines or who shouldn't take them.
INTERACTION_SECTIONS = (
    "Boxed warning",
    "Do not use if",
    "Do not use",
    "Warnings",
    "Ask a doctor before use",
    "Ask a doctor or pharmacist before use",
    "Drug interactions",
)


def display_name(info: dict) -> str:
    return info["brand_name"] or info["generic_name"] or "this medicine"


def label_text(info: dict, only: tuple[str, ...] | None = None) -> str:
    return "\n\n".join(
        f"## {title}\n{text}" for title, text in info["sections"].items() if only is None or title in only
    )


def explain_label(info: dict, language: str = "English", client: anthropic.Anthropic | None = None) -> str:
    prompt = (
        f"Explain this label for {display_name(info)} ({info['generic_name'] or 'generic name unknown'}). "
        f"Write the explanation in {language}.\n\n<label>\n{label_text(info)}\n</label>"
    )
    return ask(prompt, EXPLAIN_PROMPT, client=client)


def check_interactions(infos: list[dict], language: str = "English", client: anthropic.Anthropic | None = None) -> str:
    if len(infos) < 2:
        raise ValueError("Add at least two medicines to check them against each other.")
    names = ", ".join(f"{display_name(i)} ({i['generic_name'] or '?'})" for i in infos)
    labels = "\n\n".join(
        f'<label medicine="{display_name(i)}">\n{label_text(i, INTERACTION_SECTIONS)}\n</label>' for i in infos
    )
    prompt = f"My medicines: {names}. Answer in {language}.\n\n{labels}"
    return ask(prompt, INTERACTIONS_PROMPT, client=client)
