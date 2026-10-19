# Label Lens

Snap or type a medicine name and get its official FDA label explained in plain language, in
the language you choose.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # your Anthropic API key
```

The openFDA API needs no key for light use (about 1,000 requests a day per IP address).

## Try it

```bash
python lookup.py ibuprofen                        # print the official label
python lookup.py Zyrtec --explain                 # plain-language explanation
python lookup.py metformin --explain --language Spanish
pytest                                            # run the tests (offline)
```

## How it's organized

- `label_lens/fda.py`: finds a drug's label on openFDA by brand name, then generic name, and
  pulls out the readable sections. Prescription and over-the-counter labels use different
  field names, and `SECTIONS` covers both.
- `label_lens/explain.py`: sends the label to the AI model with instructions to use only what the
  label says.
- `lookup.py`: the command line.
- `tests/`: offline tests using a shortened sample label.

## The plan for the week

- [x] **Mon:** Look up a drug on openFDA and print its label.
- [x] **Tue:** Have the AI model explain the label in plain language and other languages.
- [ ] **Wed:** Read the drug name and strength from a photo of the box or bottle.
  Send the image to the model as a base64 `image` content block, and ask for JSON with
  `name` and `strength`. Then feed `name` into `search_label`.
- [ ] **Thu:** Build a "my medicines" list.
  - Save the list to a small JSON file.
  - When a new drug is added, give the model its label plus the names of the others, and ask what
    the label says about them.
  - Only report interactions the label text mentions.
- [ ] **Fri:** Build a Streamlit web page.
  - Add a photo upload (`st.camera_input` / `st.file_uploader`), a language picker and the
    medicine list.
  - Run it with `streamlit run app.py`.
- [ ] **Weekend:** Polish.
  - Handle errors, such as no label found, an unreadable photo, or a brand with many labels.
  - Add screenshots to this README, record a 1-minute demo, and push to GitHub.

## Ideas once it works

- Highlight the boxed warning, the FDA's strongest warning, in red at the top.
- Add a "read it aloud" button for people with low vision.
- Cache labels so the same drug isn't fetched twice.

Label Lens summarizes official labels and isn't medical advice. Always check with a
pharmacist or doctor.
