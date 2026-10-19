# Label Lens

Type a medicine name or upload a photo of the box, and get its official FDA label explained
in plain language, in the language you choose.

## Use it

Open the website on your phone or laptop, and type a medicine name or tap **Scan a medicine box**.

- The official FDA label, explained in plain language in any of 11 languages, with the
  original text underneath.
- A boxed warning, the FDA's strongest warning, shown in red at the top.
- **My medicines**: a list saved on your device. Check two or more against each other's labels
  for warnings about taking them together.

## Run it on your computer

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn app:app --reload
```

Then open http://localhost:8000.

## Deploy on Vercel

1. Import this repo into Vercel. It's detected as a FastAPI app, and the website in `public/`
   is served alongside it.
2. In **Settings › Environment Variables**, add `ANTHROPIC_API_KEY`.
3. Optional: add `APP_ACCESS_CODE`. Visitors then need the code to use the AI features, so
   strangers can't spend your API credit. Label lookups stay open.

## Command line

```bash
python lookup.py ibuprofen                        # print the official label
python lookup.py Zyrtec --explain                 # plain-language explanation
python lookup.py metformin --explain --language Spanish
pytest                                            # run the tests (needs requirements-dev.txt)
```

## How it's organized

- `app.py`: the web API (FastAPI) that the website calls.
- `public/`: the website (HTML, CSS and JavaScript).
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
- [x] Website, deployable on Vercel
- [ ] Screenshots in this README, a 1-minute demo video

## Ideas once it works

- Add a "read it aloud" button for people with low vision.
- Cache labels so the same drug isn't fetched twice.

Label Lens summarizes official labels and isn't medical advice. Always check with a
pharmacist or doctor.
