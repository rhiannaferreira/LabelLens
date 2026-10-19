"""Label Lens web app. Run with:  streamlit run app.py"""

import json
from pathlib import Path

import streamlit as st

from label_lens.explain import check_interactions, display_name, explain_label
from label_lens.fda import DrugNotFound, label_info, search_label
from label_lens.vision import read_packaging

MEDS_FILE = Path(__file__).parent / "my_medicines.json"
LANGUAGES = ["English", "Spanish", "Chinese (Simplified)", "Vietnamese", "Tagalog", "Korean",
             "Portuguese", "Hindi", "Arabic", "French", "Russian"]

st.set_page_config(page_title="Label Lens", page_icon="💊", layout="centered")


@st.cache_data(show_spinner=False, ttl=24 * 3600)
def get_info(name: str) -> dict:
    return label_info(search_label(name))


@st.cache_data(show_spinner=False)
def get_explanation(name: str, language: str) -> str:
    return explain_label(get_info(name), language=language)


def load_meds() -> list[str]:
    try:
        return json.loads(MEDS_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_meds(meds: list[str]) -> None:
    MEDS_FILE.write_text(json.dumps(meds, indent=2))


if "meds" not in st.session_state:
    st.session_state.meds = load_meds()
if "current" not in st.session_state:
    st.session_state.current = None

st.title("Label Lens")
st.caption("Official FDA medicine labels, explained in plain language.")

language = st.selectbox("Explain in", LANGUAGES, key="language")

look_up, my_meds = st.tabs(["Look up a medicine", f"My medicines ({len(st.session_state.meds)})"])

with look_up:
    typed, photo = st.columns(2)
    with typed:
        with st.form("search"):
            query = st.text_input("Medicine name", placeholder="e.g. Advil or ibuprofen", key="query")
            if st.form_submit_button("Look up", use_container_width=True) and query.strip():
                st.session_state.current = query.strip()
    with photo:
        upload = st.file_uploader("Or upload a photo of the box", type=["jpg", "jpeg", "png", "webp"], key="photo")
        if upload and st.button("Read photo", use_container_width=True):
            with st.spinner("Reading the packaging..."):
                try:
                    found = read_packaging(upload.getvalue(), upload.type)
                except Exception as e:
                    st.error(f"Couldn't read the photo: {e}")
                    found = None
            if found and found["found"]:
                st.success(f"Found {found['name']} {found['strength']}".strip())
                st.session_state.current = found["name"] or found["active_ingredient"]
            elif found is not None:
                st.warning("Couldn't make out a medicine name. Try a sharper photo of the front of the box.")

    name = st.session_state.current
    if name:
        try:
            with st.spinner(f"Finding the FDA label for {name}..."):
                info = get_info(name)
        except DrugNotFound:
            st.error(f"No FDA label found for “{name}”. Check the spelling or try the generic name.")
            info = None
        except Exception as e:
            st.error(f"Couldn't reach the FDA label service: {e}")
            info = None

        if info:
            st.subheader(display_name(info))
            st.caption(f"{info['generic_name'] or ''} · {info['manufacturer'] or 'Unknown maker'}")
            if "Boxed warning" in info["sections"]:
                st.error("**Boxed warning (the FDA's strongest warning):** " + info["sections"]["Boxed warning"])

            if name not in st.session_state.meds:
                if st.button(f"Add {display_name(info)} to my medicines"):
                    st.session_state.meds.append(name)
                    save_meds(st.session_state.meds)
                    st.rerun()
            else:
                st.caption("✓ In your medicines")

            try:
                with st.spinner("Explaining the label..."):
                    st.markdown(get_explanation(name, language))
            except Exception as e:
                st.error(f"Couldn't get an explanation: {e}")

            with st.expander("Read the official label text"):
                for title, text in info["sections"].items():
                    st.markdown(f"**{title}**")
                    st.write(text)

with my_meds:
    meds = st.session_state.meds
    if not meds:
        st.info("No medicines yet. Look one up and tap “Add to my medicines”.")
    for med in list(meds):
        left, right = st.columns([4, 1])
        left.write(med)
        if right.button("Remove", key=f"remove-{med}"):
            meds.remove(med)
            save_meds(meds)
            st.rerun()

    if len(meds) >= 2 and st.button("Check my medicines together", type="primary"):
        try:
            with st.spinner("Comparing the labels..."):
                st.markdown(check_interactions([get_info(m) for m in meds], language=language))
        except Exception as e:
            st.error(f"Couldn't check interactions: {e}")

st.divider()
st.caption("Label Lens summarizes official FDA labels and isn't medical advice. Always check with a pharmacist or doctor.")
