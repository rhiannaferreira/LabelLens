# Label Lens

Type a medicine name or upload a photo of the box, and get its official FDA label explained
in plain language, in the language you choose.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # your Anthropic API key
```

The openFDA API needs no key for light use (about 1,000 requests a day per IP address).

## Run the app

```bash
streamlit run app.py
```

It opens in your browser at http://localhost:8501. You can:

- **Look up a medicine** by typing its name, or by uploading a photo of the box or bottle.
- **Read the explanation** in any of 11 languages, with the official label text underneath.
- **Add medicines to your list**, then check them together for warnings their labels give
  about combining them. The list is saved in `my_medicines.json` on your computer.

Photos must be JPG, PNG or WEBP. On iPhone, set Camera › Formats to "Most Compatible", or take a
screenshot of the photo.

## Command line

```bash
python lookup.py ibuprofen                        # print the official label
python lookup.py Zyrtec --explain                 # plain-language explanation
python lookup.py metformin --explain --language Spanish
pytest                                            # run the tests (offline)
```

## How it's organized

- `app.py`: the web app (Streamlit).
- `label_lens/fda.py`: finds a drug's label on openFDA by brand name, then generic name, and
  pulls out the readable sections. It covers both prescription and over-the-counter label fields.
- `label_lens/explain.py`: plain-language explanations and the medicine-list check. Both are
  told to use only what the labels say.
- `label_lens/vision.py`: reads the name and strength from a photo of the packaging.
- `label_lens/model.py`: the shared call to the AI model.
- `tests/`: offline tests, using a shortened sample label and fake model replies.

## Progress

- [x] Look up a drug on openFDA and print its label
- [x] Explain the label in plain language, in other languages
- [x] Read the drug name from a photo of the box
- [x] "My medicines" list with a combined label check
- [x] Web app
- [ ] Screenshots in this README, a 1-minute demo video

## Ideas once it works

- Add a "read it aloud" button for people with low vision.
- Cache labels so the same drug isn't fetched twice.

Label Lens summarizes official labels and isn't medical advice. Always check with a
pharmacist or doctor.
