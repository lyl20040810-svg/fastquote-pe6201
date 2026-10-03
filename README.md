# FastQuote PE6201

FastQuote is a review-only quotation assistant for fastener sales. A customer supplies a diameter, length and quantity in pieces, boxes or cartons; they do not need to know the catalog standard. The system extracts those fields, matches an exact SKU in a verified 73-row DIN933 A2 price-list subset, calculates the quote with deterministic Python rules, and drafts an English reply for a salesperson to review. It never sends the reply or approves an order automatically.

## Repository contents

- `streamlit_app.py`, `fastquote/`, `data/`: hosted teacher demo, including the real verified price data.
- `FastQuote_Project_Source.zip`: local Python app, unit tests, evaluation scripts and development datasets.
- `FastQuote_Colab.ipynb`: personal Colab notebook; its embedded page is not a public demo URL.
- `FastQuote_Price_List.xlsx`: readable copy of the catalog subset.

The final written report and narrated video are separate deliverables and are not yet included here.

## Try the demo

Install with `python -m pip install -r requirements.txt`, then run `streamlit run streamlit_app.py` from the repository root. Rules mode needs no API key. Suggested inputs:

- `M16x50, 2 cartons` for a normal quote.
- `M20x80, 10 cartons` for a quote that needs manager approval.
- `M16 bolts, 3 boxes` for a request that needs clarification.

The interface shows the exact catalog match, quantities, calculated amount, Need Approval = YES/NO, and a customer reply draft. Monetary values and the 10% internal approval gate are calculated by code, not by the language model. A salesperson must verify the result before any customer communication.

## Host for teacher access

Import this **private** repository into [Streamlit Community Cloud](https://share.streamlit.io/) and select the root-level `streamlit_app.py` as the entry point. Share the resulting `streamlit.app` URL according to the app's sharing settings. A GitHub repository link alone does not launch the app.

To use OpenRouter extraction, add `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` in Streamlit Secrets. Never commit a real key. A publicly accessible app can use API credits and reveal prices through its quotes, so limit access when possible. The original `gradio.live` 504 tunnel errors do not affect Streamlit hosting.

## Scope and evidence

The source catalog contains 73 rows transcribed and checked from the supplied price-list photos. Rows with unclear packaging were excluded. The project source includes 11 automated tests and a 15-case development set. Final blind evaluation results should be reported separately from development results; extraction accuracy, automatic coverage, false flag rate and pricing correctness are distinct measures.
