# Local verification — 2026-10-15

Python 3.12.14. Package versions are pinned in `requirements.txt`.

## Results

- `python -m pytest -q`: **32 passed**.
- `python -m pip check`: no broken requirements.
- Numerical subnet test checks **250 generated scenarios** against independently reconstructed `ipaddress` networks.
- Real Chroma is initialized, queried with a section filter, and reopened without re-embedding existing documents.
- Streamlit AppTest completes sample generation, answer feedback, and a fresh-session paywall check.
- A 16-attempt concurrent reservation test permits only one pending trial for the same account.
- Identity checks reject unverified emails, wrong issuers, invalid identities and expired tokens.
- Billing tests reject wrong prices, wrong modes, canceled/past-due/unpaid/trialing/incomplete subscriptions and active subscriptions with unpaid latest invoices. API failures do not unlock access.
- The **installed Stripe SDK** serializes requests and decodes mock HTTP responses, including the expanded invoice.
- The **installed Gemini SDK** serializes embeddings and the scenario schema and parses mock generation/SSE responses. No real model API request is made by these tests.

## Bugs caught and fixed during verification

- Stripe SDK 15 objects require conversion with `to_dict()` before dictionary-style `.get()` access.
- Gemini SDK schema conversion rejects integer Literal enums; the correct answer index uses an integer with bounds 0–3 instead.
- HTTPX proxy support required the `socks` extra in this execution environment; it is included in the pinned dependencies.
- Local visual testing exposed unwanted Streamlit internal help output from standalone conditional expressions. Explicit `if`/`else` rendering fixes it in account status and answer feedback. The Streamlit workflow regression now rejects internal `help_info` elements.

## Pending external checks

Google OAuth callback configuration, real Gemini account/model access and output quality, the existing Stripe sandbox key, test checkout-to-unlock, the Stripe customer portal, Render persistence under restart, Render memory/concurrency, and backup/restore have not yet been verified on a deployed service.

This report records local verification before the application was uploaded to GitHub. No live payments were collected, no Render service was provisioned, and no Reddit post was published.
