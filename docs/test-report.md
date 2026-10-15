# Local verification — 2026-10-15

Python 3.12.14. Package versions are pinned in `requirements.txt`.

## Results

- `python -m pytest -q`: **70 passed**.
- `python -m pip check`: no broken requirements.
- A real `start.py --local-ai` child starts on loopback and returns HTTP 200 `ok` from `/_stcore/health`; it is stopped after the check.
- Numerical subnet test checks **250 generated scenarios** against independently reconstructed `ipaddress` networks.
- Real Chroma is initialized, queried with a section filter, and reopened without re-embedding existing documents.
- Streamlit AppTest submits a first chat prompt, restores saved messages in a fresh session, and verifies that both the composer and starter buttons remain blocked after choosing New chat.
- Customer UI workflows exercise both Ollama and legacy Gemini provider selection with stubbed identity, billing, retrieval, and generation boundaries. They verify subscription unlock, follow-up context, and immediate denial after cancellation even while the sidebar display cache is stale.
- Local AI AppTest uses the real Ollama adapter, HTTPX mock transport, and real Chroma to index references and stream a first answer without auth or billing keys. It then verifies the paywall, New chat, and isolated local-trial reset. A stopped Ollama server leaves the free response available.
- Ollama contract checks cover Nomic task prefixes, batching, normalized 768-dimensional vectors, bounded history, verified subnet facts, thinking-output exclusion, immediate unloading, CPU options, missing/cloud models, invalid vectors, and incomplete streams.
- Startup/configuration checks reject preview modes on Render, remote local-test URLs, conflicting modes, and cloud tags. The local launcher overrides an old demo flag and binds only to loopback; customer mode still requires Google auth and Stripe configuration.
- Separate embedding profiles create distinct Chroma collections, preventing incompatible vector reuse.
- Streaming lifecycle checks verify that failures before text release the trial; partial delivered responses are saved as interrupted and consume it.
- Conversation ownership checks prevent reading or writing another account's chat. Trial completion and message persistence use one SQLite transaction.
- A 16-attempt concurrent reservation test permits only one pending trial for the same account.
- Identity checks reject unverified emails, wrong issuers, invalid identities and expired tokens.
- Billing tests reject wrong prices, wrong modes, canceled/past-due/unpaid/trialing/incomplete subscriptions and active subscriptions with unpaid latest invoices. API failures do not unlock access.
- The **installed Stripe SDK** serializes requests and decodes mock HTTP responses, including the expanded invoice.
- The **installed Gemini SDK** serializes embeddings, the scenario schema, and multi-turn user/model chat roles, and parses mock generation/SSE responses. No real model API request is made by these tests.

## Bugs caught and fixed during verification

- Stripe SDK 15 objects require conversion with `to_dict()` before dictionary-style `.get()` access.
- Gemini SDK schema conversion rejects integer Literal enums; the correct answer index uses an integer with bounds 0–3 instead.
- HTTPX proxy support required the `socks` extra in this execution environment; it is included in the pinned dependencies.
- Local visual testing exposed unwanted Streamlit internal help output from standalone conditional expressions. Explicit `if`/`else` rendering fixes it in account status and answer feedback. The Streamlit workflow regression now rejects internal `help_info` elements.

## Pending external checks

Actual Qwen/Nomic output, latency, and memory use on the Windows laptop are pending. This workspace has no running Ollama daemon: `python check_local_ai.py` correctly exits with an actionable server-not-ready message. Automated Ollama responses are mocked; the suite does not prove CCNA answer quality. Google OAuth, real Stripe checkout/portal, remote model hosting, Render persistence/concurrency, and backup/restore also remain pending.

The visual refinement adds a navy sidebar, mint accents, topic cards, compact welcome layout, and a direct upgrade panel instead of disabled starter cards after the trial. Keyboard focus styles, mobile spacing rules, and reduced-motion rules are included.

This report records local verification of the chat-interface update. The UI workflows use Streamlit's test runner. A browser screenshot check was attempted, but the cloud browser could not connect to the workspace's localhost server (`ERR_CONNECTION_REFUSED`); rendered desktop/mobile screenshots have not been verified. No live payments were collected, no Render service was provisioned, and no Reddit post was published.
