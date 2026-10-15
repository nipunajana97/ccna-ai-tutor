# CCNA Exam Scenario Tutor

A Streamlit micro-SaaS for **focused CCNA 200-301 v1.1 practice**. One free chat response per verified Google account, then a Stripe subscription. The default AI backend is now **Ollama with downloaded local models**, using your CCNA reference through RAG. A Gemini API key is not required for this backend.

Repository: https://github.com/nipunajana97/ccna-ai-tutor

## What is implemented

- Six reviewed reference sections, loaded into embedded persistent ChromaDB.
- Local answers from `qwen3:1.7b` and local search embeddings from `nomic-embed-text:v1.5` through Ollama.
- CPU inference, bounded 4K context, two retrieved reference chunks, and immediate model unloading for the 8 GB laptop prototype.
- Correct Nomic document/query prefixes and normalized 768-dimensional vectors, with separate Chroma collection profiles for incompatible embedding providers.
- `start.py --local-ai` for real local answers without Google/Stripe setup; `check_local_ai.py` checks the server/models and can run an actual RAG answer.
- The previous Gemini adapter remains available only when explicitly selecting `AI_PROVIDER=gemini` and supplying its key.
- ChatGPT-style conversation layout with a navy sidebar, colored topic cards, streamed answers, saved chats, and a bottom message composer.
- Compact welcome screen and a direct upgrade panel when the trial is used; the local preview restart control sits below New chat.
- First chat response free; the conversation remains readable when the subscription gate appears.
- Follow-up answers use recent conversation context and retrieved references.
- Persisted conversation history and source excerpts, isolated by authenticated account.
- Original practice scenarios can be requested directly in chat. AI answers, including numerical answers, need review against the reference.
- Python supplies verified subnet facts for explicit IPv4/CIDR questions to the local model. The deterministic /25–/30 scenario engine also remains available. Generated prose and arbitrary calculations still need review.
- Google OIDC authentication, strict verified-email checks, and exact-price active Stripe subscription checks.
- One trial stored by Google subject ID; refreshes and simultaneous browser tabs do not create extra trials.
- Stripe customer portal access for managing/canceling subscriptions (the portal must be enabled in Stripe).
- Atomic quota reservations, failed-request recovery, input/output bounds, and configurable daily request ceilings.
- Minimal aggregate funnel metrics, including the subscription link's **checkout-click callback**. A click is not a completed payment.

## Important scope decisions

1. **Customer trials require sign-in.** A verified account provides a durable identity for a one-response trial. Refreshing, opening another tab, or choosing New chat does not reset the allowance. Existing consumed trials remain consumed. Owner-side local tests use a separate identity/database and are bound to localhost.
2. **Delivered responses consume the trial.** A failure before useful text is returned leaves the free prompt available. A partially delivered response is saved, marked interrupted, and counts as the free response.
3. **Email typing is not authentication.** Subscription lookup uses the email in the verified Google identity token. Checkout must use that same email. No sidebar email textbox can unlock access.
4. **Subscriber allowance defaults to 100 requests/day** for prompts and follow-ups. A global ceiling defaults to 500 attempts/day. Self-hosting uses your hardware/server resources; this prototype has not been load-tested with paid customers.
5. **Only active subscriptions with a paid latest invoice for the configured price unlock new requests.** Canceled, incomplete, unpaid, past-due, trialing, wrong-price, and wrong-mode subscriptions do not. Scheduled cancellation remains active until Stripe changes its status at period end. Billing failures fail closed.
6. This MVP **polls Stripe directly**; it does not require a webhook server. Sidebar status can cache for 30 seconds, but every chat request rechecks Stripe without that display cache. Use “I've paid · Refresh access” after checkout.
7. The reference is **not full exam coverage**. It omits IPv6, wireless, many IP services and other blueprint material. AI output is not guaranteed correct merely because it uses retrieval.

## Project layout

```text
app.py                     Chat interface and authenticated request flow
start.py                   OIDC environment bootstrap and Render entry point
check_local_ai.py          Ollama availability, models, memory and optional RAG check
ccna_knowledge.txt         Reviewed starter reference
tutor/                    Identity, billing, quota, retrieval and model services
tests/                    Access, billing, Chroma and Streamlit workflow checks
docs/knowledge-review.md   Corrections to the supplied reference
docs/deploy.md             Google/Stripe/Render setup and funnel checks
docs/local-ai.md           Ollama installation, reference updates and local testing
render.yaml               Paid Starter service + 1 GB persistent disk blueprint
.env.example              Environment template; no secrets included
```

## Run real local AI first

Install [Ollama for Windows](https://ollama.com/download/windows), keep it running, and reopen PowerShell. For the supplied 8 GB / Intel UHD laptop, start with:

```powershell
ollama pull qwen3:1.7b
ollama pull nomic-embed-text:v1.5
.\.venv\Scripts\python.exe check_local_ai.py
.\.venv\Scripts\python.exe start.py --local-ai
```

Use your existing virtual environment. For a fresh checkout, create it and install `requirements.txt` first. No new Python dependency is required by the local adapter. Close unused apps before loading models; the supplied screenshot showed 96% memory use. See [the full local AI guide](docs/local-ai.md) for an actual answer check, reference updates, and memory limits. The local AI banner must be visible. This is a new trial in `data/local-ai/`; use **Restart local AI trial** to repeat owner-side testing.

## Run an offline interface sample

Use Python 3.11 or 3.12:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python start.py --demo
```

On Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe start.py --demo
```

Open http://localhost:8501. The demo accepts one prompt, displays a curated offline example, and then shows the subscription gate. These examples are not Gemini responses, and the demo cannot unlock paid access. It makes no Google, Gemini, or Stripe calls. Use **Restart local preview** in the sidebar to try again with a separate temporary preview identity. This does not delete history or reset real account trials. The default demo trial survives refreshes in `data/demo/`. `DEMO_MODE=true` is rejected in Render.

If `py -3.12` refers to a missing executable on Windows, run `py -0p` to inspect registered installations. When a valid Python 3.11 is listed, create the environment with `py -3.11 -m venv .venv`. The pinned direct dependencies allow Python 3.11. Continue with `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.\.venv\Scripts\python.exe start.py` after setting `DEMO_MODE=true`.

## Run with real integrations in Stripe test mode

Copy `.env.example` to `.env`. Enter credentials locally or directly in Render's Environment screen. Never commit `.env` or `.streamlit/secrets.toml`.

With Ollama, required customer-mode credentials are the Stripe test secret key, Google OAuth client ID/secret, and a random auth cookie secret. Keep both preview flags false, and provide a running model server. See [deployment instructions](docs/deploy.md). Run `python start.py`; it creates a private, ignored Streamlit auth file from the environment. A remote model server needs your authenticated HTTPS proxy; the app does not deploy that server automatically.

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

The automated suite includes real Chroma persistence, Streamlit workflows, both AI provider adapters, local-mode isolation, first-prompt gating, and streaming failures. Ollama HTTP responses are mocked here: actual model output, latency, and RAM use on the Windows laptop still need the local acceptance check. Google login, real Stripe checkout/portal, and Render deployment also remain unverified end to end.

The blueprint is prepared, not applied. It creates paid web compute/storage if applied and requires a separately provisioned Ollama model server. It cannot reach your laptop through localhost. Use one web instance with its attached disk; SQLite/embedded Chroma are not a multi-instance architecture. Back up the disk and test a restore before depending on it.

### Primary implementation references

- Ollama local API: https://docs.ollama.com/api/introduction
- Local models and Windows setup: [docs/local-ai.md](docs/local-ai.md)
- Google SDK: https://ai.google.dev/gemini-api/docs/libraries
- Model lifecycle: https://ai.google.dev/gemini-api/docs/deprecations
- Embeddings: https://ai.google.dev/gemini-api/docs/embeddings
- Streamlit authentication: https://docs.streamlit.io/develop/concepts/connections/authentication
- Stripe subscriptions: https://docs.stripe.com/api/subscriptions/list
- Render free limitations: https://render.com/docs/free
- Render persistent disks: https://render.com/docs/disks
