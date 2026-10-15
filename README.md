# CCNA Exam Scenario Tutor

A Streamlit micro-SaaS for **focused CCNA 200-301 v1.1 practice**. One free chat response per verified Google account, then a Stripe subscription. No GPU or local model weights are needed.

Repository: https://github.com/nipunajana97/ccna-ai-tutor

## What is implemented

- Six reviewed reference sections, loaded into embedded persistent ChromaDB.
- Gemini API document/query embeddings and current `google-genai` SDK.
- Configurable generation model, default `gemini-3.8-flash` per Google's October 2026 documentation.
- `gemini-embedding-001` with normalized 768-dimensional vectors and retrieval task types. Changing the embedding model rebuilds the index into a separate collection. The code currently expects this model's task-type semantics; do not switch to Embedding 2 without adapting them.
- ChatGPT-style conversation layout: saved chats in the sidebar, starter prompts, streamed answers, and a bottom message composer.
- First chat response free; the conversation remains readable when the subscription gate appears.
- Follow-up answers use recent conversation context and retrieved references.
- Persisted conversation history and source excerpts, isolated by authenticated account.
- Original practice scenarios can be requested directly in chat. AI answers, including numerical answers, need review against the reference.
- A separately tested deterministic /25–/30 IPv4 scenario engine remains available in the Python module; it does not verify arbitrary chat calculations.
- Google OIDC authentication, strict verified-email checks, and exact-price active Stripe subscription checks.
- One trial stored by Google subject ID; refreshes and simultaneous browser tabs do not create extra trials.
- Stripe customer portal access for managing/canceling subscriptions (the portal must be enabled in Stripe).
- Atomic quota reservations, failed-request recovery, input/output bounds, and configurable daily request ceilings.
- Minimal aggregate funnel metrics, including the subscription link's **checkout-click callback**. A click is not a completed payment.

## Important scope decisions

1. **The free prompt requires sign-in.** A verified account provides a durable identity for a one-response trial. Refreshing, opening another tab, or choosing New chat does not reset the allowance. Existing consumed scenario trials remain consumed after upgrading this interface.
2. **Delivered responses consume the trial.** A failure before useful text is returned leaves the free prompt available. A partially delivered response is saved, marked interrupted, and counts as the free response.
3. **Email typing is not authentication.** Subscription lookup uses the email in the verified Google identity token. Checkout must use that same email. No sidebar email textbox can unlock access.
4. **Subscriber allowance defaults to 100 requests/day** for prompts and follow-ups. A global ceiling defaults to 500 attempts/day. These are request-count controls, not dollar-denominated spend guarantees. Review pricing and set budgets in the Gemini account too.
5. **Only active subscriptions with a paid latest invoice for the configured price unlock new requests.** Canceled, incomplete, unpaid, past-due, trialing, wrong-price, and wrong-mode subscriptions do not. Scheduled cancellation remains active until Stripe changes its status at period end. Billing failures fail closed.
6. This MVP **polls Stripe directly**; it does not require a webhook server. Sidebar status can cache for 30 seconds, but every chat request rechecks Stripe without that display cache. Use “I've paid · Refresh access” after checkout.
7. The reference is **not full exam coverage**. It omits IPv6, wireless, many IP services and other blueprint material. AI output is not guaranteed correct merely because it uses retrieval.

## Project layout

```text
app.py                     Chat interface and authenticated request flow
start.py                   OIDC environment bootstrap and Render entry point
ccna_knowledge.txt         Reviewed starter reference
tutor/                    Identity, billing, quota, retrieval and model services
tests/                    Access, billing, Chroma and Streamlit workflow checks
docs/knowledge-review.md   Corrections to the supplied reference
docs/deploy.md             Google/Stripe/Render setup and funnel checks
render.yaml               Paid Starter service + 1 GB persistent disk blueprint
.env.example              Environment template; no secrets included
```

## Run a local sample without API keys

Use Python 3.11 or 3.12:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
DEMO_MODE=true python start.py
```

On Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DEMO_MODE="true"
.\.venv\Scripts\python.exe start.py
```

Open http://localhost:8501. The demo accepts one prompt, displays a curated offline example, and then shows the subscription gate. These examples are not Gemini responses, and the demo cannot unlock paid access. It makes no Google, Gemini, or Stripe calls. Use **Restart local preview** in the sidebar to try again with a separate temporary preview identity. This does not delete history or reset real account trials. The default demo trial survives refreshes in `data/demo/`. `DEMO_MODE=true` is rejected in Render.

If `py -3.12` refers to a missing executable on Windows, run `py -0p` to inspect registered installations. When a valid Python 3.11 is listed, create the environment with `py -3.11 -m venv .venv`. The pinned direct dependencies allow Python 3.11. Continue with `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.\.venv\Scripts\python.exe start.py` after setting `DEMO_MODE=true`.

## Run with real integrations in Stripe test mode

Copy `.env.example` to `.env`. Enter credentials locally or directly in Render's Environment screen. Never commit `.env` or `.streamlit/secrets.toml`.

Required credentials: Gemini API key, Stripe test secret key, Google OAuth client ID/secret, and a random auth cookie secret. See [deployment instructions](docs/deploy.md). Run `python start.py`; it creates a private, ignored Streamlit auth file from the environment.

The sandbox objects already created for this project are included in `.env.example` and the blueprint:

| Setting | Sandbox value |
| --- | --- |
| Product | `prod_VRWcVZfvzo3eL3` |
| Price | `price_1UQdZaCvG4xAhKW62tQteiuU` |
| Payment link | https://buy.stripe.com/test_aFa7sKfRceuj6BsfQk6wE00 |
| Amount | 9 USD/month |

These IDs/links are not secret keys. Live mode requires separate live objects and credentials.

## Tests and metrics

```bash
pip install -r requirements-dev.txt
python -m pytest -q
python -m pip check
python manage.py
```

`manage.py` prints per-day counts for visits, logins, paywall views, subscription-link clicks and completed requests. Visits are browser-session events, not unique people. A `checkout_click` callback records the outgoing subscription button click; it does not prove that Stripe loaded or a purchase completed. Stripe payment/subscription reports are the authoritative conversion evidence.

## Deployment status and verification limits

This package has been tested locally with real Chroma persistence, Streamlit's test runner, first-prompt gating, saved conversations, interrupted-stream recovery, deterministic engine cases, and mocked billing responses. Google login, paid Gemini generations, real Stripe checkout/portal, and Render deployment require credentials and have **not** been verified end to end here.

The blueprint is prepared, not applied. It creates paid compute/storage if applied. Use one instance with its attached disk; SQLite/embedded Chroma are not a multi-instance architecture. Back up the disk and test a restore before depending on it. The dependency versions are pinned to the packages installed for this build; dependencies should be reviewed periodically.

### Primary implementation references

- Google SDK: https://ai.google.dev/gemini-api/docs/libraries
- Model lifecycle: https://ai.google.dev/gemini-api/docs/deprecations
- Embeddings: https://ai.google.dev/gemini-api/docs/embeddings
- Streamlit authentication: https://docs.streamlit.io/develop/concepts/connections/authentication
- Stripe subscriptions: https://docs.stripe.com/api/subscriptions/list
- Render free limitations: https://render.com/docs/free
- Render persistent disks: https://render.com/docs/disks
