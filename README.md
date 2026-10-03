# FastQuote Teacher Demo

This repository contains the functional FastQuote application and the real,
73-row DIN933 A2 price-list subset. It is intended for deployment from a private
GitHub repository to Streamlit Community Cloud. The web app can then be shared
with the teacher using its fixed `streamlit.app` URL. Do not change the repository
to public unless you also intend to publish the price data.

## Contents

- `streamlit_app.py`, `fastquote/`, `data/`: hosted teacher demo.
- `project/`: local Python app, tests, evaluation scripts and datasets.
- `submission/`: Colab notebook, price-list spreadsheet and operation manual.

The final written report and narrated video are not yet included; add them to
`submission/` only after they are finished and reviewed.

## Deploy

1. In [Streamlit Community Cloud](https://share.streamlit.io/), create an app
   from that repository, selecting `streamlit_app.py` as the entry point.
2. For rules-only demonstration, no API secret is required. To demonstrate
   OpenRouter extraction, set these app secrets in Advanced settings:

   ```toml
   OPENROUTER_API_KEY = "your-key-here"
   OPENROUTER_MODEL = "openai/gpt-4.1-mini"
   ```

   Enter the real key only in Streamlit's Secrets field, never in a repository
   file or screenshot.
3. In the app's Sharing settings, grant the teacher access or make the app
   public. Send the generated `https://...streamlit.app` URL.

The 504 errors from `gradio.live` do not affect this hosted version. OpenRouter
is only used when a key is configured; the pricing rules are always local and
deterministic. A public app with an OpenRouter key can receive requests from
any visitor, so use private sharing when possible.

## Local check

Run `python -m pip install -r requirements.txt` and then
`streamlit run streamlit_app.py` from this folder.
