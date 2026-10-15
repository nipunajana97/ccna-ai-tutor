# Setup, deployment and test funnel

## 1. GitHub

Use the `main` branch of https://github.com/nipunajana97/ccna-ai-tutor for this project. The application and Render blueprint are at the repository root. Do not add `.env`, `.streamlit/secrets.toml`, generated `data/`, API keys or a virtual environment.

## 2. Google sign-in

In Google Cloud Console, use or create the project for this app:

1. Configure the OAuth consent screen / Google Auth Platform branding and audience. During testing, add your Google account as a test user where required.
2. Create an OAuth client with application type **Web application**.
3. For local testing, add the authorized redirect URI `http://localhost:8501/oauth2callback`.
4. For deployment, add `https://YOUR-SERVICE.onrender.com/oauth2callback` using the exact Render hostname. Add your custom domain callback too if you later use one.
5. Store `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in Render Environment.

`start.py` uses Google's OIDC metadata and Streamlit's native auth implementation. It does not implement password collection. A Google identity without verified email or with an expired token must sign in again.

## 3. Gemini

Create an API key in Google AI Studio and put it in `GEMINI_API_KEY`. The project's generation model must support `generateContent`, streaming, and JSON structured output. Defaults:

- `GEMINI_MODEL=gemini-3.8-flash`
- `GEMINI_EMBEDDING_MODEL=gemini-embedding-001`

Free-tier access/rate limits are account/model dependent. The package does not assume unlimited free usage. Enable billing only when ready and configure provider-side budgets/alerts. The first AI request indexes the small reference; later requests reuse its stored embeddings. No embedding model weights are downloaded by the app.

## 4. Stripe sandbox

The product, recurring price and payment link already exist. In the same sandbox:

1. Find **Developers / API keys** and copy the **test secret key** directly into Render's `STRIPE_SECRET_KEY` field. Keep it out of chat and Git.
2. Keep `BILLING_MODE=test`, the included test price ID, and the included test payment link together.
3. In Billing settings, activate/configure the **test customer portal** so subscribers can manage/cancel their subscription. Enable cancellation and review the portal's subscription settings. The app creates portal sessions only for the authenticated subscriber's customer.
4. For purchases, use the **same email as the verified Google login**. A different email will not unlock that Google account.

No webhook key is needed for this direct-polling MVP. Every request verifies subscription status through Stripe; there is no “payment succeeded” query parameter that grants access.

## 5. Render

The included `render.yaml` provisions **paid Starter compute plus a persistent disk**. Applying it is a paid deployment; review the displayed cost before creating it. Do not substitute Free for a durable trial database. A separate external durable database could support a future free-service variant, but that variant is not implemented here.

Either import the repository as a Render Blueprint or create a Python Web Service manually:

| Setting | Value |
| --- | --- |
| Build command | `pip install -r requirements.txt` |
| Start command | `python start.py` |
| Health check | `/_stcore/health` |
| Disk mount | `/var/data` |
| Disk initial size | 1 GB |
| DATA_DIR | `/var/data/ccna` |
| Python | 3.12.14 |

Environment variables:

| Variable | Value / source |
| --- | --- |
| `GEMINI_API_KEY` | Google AI Studio secret |
| `GEMINI_MODEL` | `gemini-3.8-flash` |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` |
| `STRIPE_SECRET_KEY` | Secret from this Stripe sandbox |
| `STRIPE_PRICE_ID` | `price_1UQdZaCvG4xAhKW62tQteiuU` |
| `STRIPE_PAYMENT_LINK` | `https://buy.stripe.com/test_aFa7sKfRceuj6BsfQk6wE00` |
| `BILLING_MODE` | `test` |
| `GOOGLE_CLIENT_ID` | Google OAuth Web client |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Web client secret |
| `AUTH_COOKIE_SECRET` | Random stable secret; Blueprint generates one |
| `DATA_DIR` | `/var/data/ccna` |
| `DEMO_MODE` | `false` |
| `APP_URL` | Optional exact public URL; by default bootstrap uses `RENDER_EXTERNAL_URL` |
| `DAILY_REQUEST_LIMIT` | `100` by default |
| `GLOBAL_DAILY_REQUEST_LIMIT` | `500` by default |

For manual setup, generate the cookie secret locally with `python -c "import secrets; print(secrets.token_urlsafe(48))"` and paste it directly into Render. Do not rotate it on every deploy; rotation signs users out.

Streamlit binds to `0.0.0.0` and Render's `PORT` automatically. The embedded store needs one instance. Monitor memory on Starter; this build has not yet been measured on Render under concurrent load.

## 6. Verify the funnel before launch

Use Stripe sandbox only:

1. Open the live Render URL in Incognito and check the sample preview.
2. Sign in with a test Google user. Confirm “1 free scenario available.”
3. Generate a subnetting scenario. Choose an answer and verify the explanation against a manual calculation.
4. Try another scenario: it must be blocked. Refresh, open another tab, and sign in again: it must remain blocked.
5. Press “Subscribe · $9/month.” Complete test checkout using the **same Google email**, test card `4242 4242 4242 4242`, any future expiry, and any valid test CVC. Do not use real card details in test mode.
6. Return and refresh payment status. The sidebar must show subscriber access.
7. Generate one OSPF/routing scenario to exercise real Gemini retrieval and structured generation; check the answer and sources.
8. Ask a supported CCNA question in tutor chat and confirm text streams.
9. Open “Manage subscription” and verify the Stripe portal works. Test canceling immediately and verify new requests stop. Test cancellation at period end separately: access should remain while Stripe still reports the subscription as active.
10. Use a second Google account with no purchase; it must not get subscriber access. A subscription for another price must not unlock access either.
11. Restart/redeploy the Render service. Verify saved trials/scenarios survive, then verify backup and recovery of the data disk.
12. Compare local funnel counts with Stripe test subscription reports. Outgoing button clicks and completed paid conversions are different metrics.

These live checks are still pending. Local automated tests do not establish that external credentials, OAuth callbacks, model entitlement, or customer portal settings are configured correctly.

## 7. Before real payments and Reddit

Create and verify separate live Stripe product/price/payment-link objects and a live secret key, then set `BILLING_MODE=live`. Publish support contact details, privacy terms, subscription/cancellation terms and a clear description of the six-topic scope. Review the reference and generated questions with a qualified networking reviewer. Do not describe the tool as hallucination-free or as official Cisco exam material.

Only launch after the live test funnel passes and the service URL is available. Check the current `r/ccna` community rules and request moderator permission if they require it. Use a candid feedback request describing what is implemented and what is still limited; do not claim paid demand from test purchases. No Reddit post has been sent.
