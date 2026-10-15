"""Run with python start.py. Secrets belong in environment variables, never Git."""
import json
import time
import streamlit as st
from tutor.config import ROOT, Settings
from tutor.identity import Identity, IdentityError, verified_identity
from tutor.billing import BillingUnavailable, Entitlement, StripeBilling
from tutor.store import AccessDenied, UsageStore
from tutor.engine import GenerationError, GeminiTutor, Scenario, subnet_scenario
from tutor.knowledge import KnowledgeIndex, read_chunks

st.set_page_config(page_title="CCNA Scenario Tutor", page_icon="🔷", layout="wide")
settings = Settings.from_env()
st.markdown("""<style>
 .block-container {max-width:1120px;padding-top:2rem;}
 .eyebrow {font-size:.78rem;letter-spacing:.14em;font-weight:700;color:#2563eb;}
 div[data-testid='stSidebar'] {background:#f1f5f9;}
 h1 {letter-spacing:-.035em;}
</style>""", unsafe_allow_html=True)
st.markdown('<div class="eyebrow">CCNA 200-301 · FOCUSED PRACTICE</div>', unsafe_allow_html=True)
st.title("Think through the network.")
st.write("Practice one realistic scenario at a time. Choose an answer, understand the reasoning, and find the reference.")
st.caption("Independent study tool · Original practice questions · Six focused topic areas")

errors = settings.errors()
if errors:
    st.info("The tutor is being configured. Please return shortly.")
    if not __import__("os").getenv("RENDER"):
        st.code("\n".join(errors))
    st.stop()
if settings.demo:
    st.warning("LOCAL DEMO — one precomputed sample; no Google, Gemini, or Stripe calls. Paid access cannot be unlocked here.")
elif settings.billing_mode == "test":
    st.info("SANDBOX — subscriptions use Stripe test mode. This version does not collect real payments.")


@st.cache_resource
def usage_store(path, daily, global_daily, cooldown):
    return UsageStore(path, daily, global_daily, cooldown)


@st.cache_resource
def stripe_service(price_id, mode, _secret):
    return StripeBilling(_secret, price_id, mode)


@st.cache_resource
def model_services(path, model, embedding_model, _key):
    tutor = GeminiTutor(_key, model, embedding_model)
    index = KnowledgeIndex(path, ROOT / "ccna_knowledge.txt", ROOT / "docs/sources.json", embedding_model, tutor.embed)
    return tutor, index


store_dir = settings.data_dir / "demo" if settings.demo else settings.data_dir
store = usage_store(str(store_dir / "usage.sqlite3"), settings.daily_limit, settings.global_daily_limit, settings.cooldown_seconds)
if "visit_logged" not in st.session_state:
    store.event("visit")
    st.session_state.visit_logged = True


def sample_preview():
    with st.expander("See a sample before signing in"):
        sample = subnet_scenario(42)
        st.write(sample.scenario)
        st.markdown("**" + sample.question + "**")
        for i, choice in enumerate(sample.choices):
            st.write(f"{'ABCD'[i]}. {choice}")
        st.caption("Your free scenario includes answer feedback and the full explanation.")


if settings.demo:
    identity = Identity("local-demo", "demo@example.invalid")
else:
    if "auth" not in st.secrets:
        st.info("Sign-in is being configured. Please return shortly.")
        st.stop()
    if not st.user.is_logged_in:
        left, right = st.columns([1.5, 1])
        with left:
            st.subheader("Start with one free scenario")
            st.write("Sign in with Google to keep your trial and subscription attached to your account.")
            if st.button("Continue with Google", type="primary"):
                st.login("google")
            sample_preview()
        with right:
            with st.container(border=True):
                st.subheader("Practice pass")
                st.markdown("### $9 / month")
                st.write("One free scenario, then subscriber practice and tutor explanations.")
                st.caption(f"Subscriber allowance: {settings.daily_limit} scenario/explanation requests per day. Cancel through the billing portal.")
        st.stop()
    try:
        identity = verified_identity(st.user.to_dict())
    except IdentityError as exc:
        st.warning(str(exc))
        if st.button("Sign out"):
            st.logout()
        st.stop()

if st.session_state.get("viewer") != identity.user_id:
    st.session_state.viewer = identity.user_id
    st.session_state.chat_messages = []
    store.event("login", identity.user_id)

billing = None if settings.demo else stripe_service(settings.stripe_price_id, settings.billing_mode, settings.stripe_key)


@st.cache_data(ttl=30, show_spinner=False)
def display_entitlement(email, price_id, mode, _billing):
    return _billing.entitlement(email)


entitlement = Entitlement()
billing_error = None
if billing:
    try:
        entitlement = display_entitlement(identity.email, settings.stripe_price_id, settings.billing_mode, billing)
    except BillingUnavailable as exc:
        billing_error = str(exc)

used = store.trial_used(identity.user_id)
with st.sidebar:
    st.subheader("Your practice account")
    st.write(identity.email)
    st.success("Subscriber access") if entitlement.active else st.info("Free scenario used" if used else "1 free scenario available")
    if billing_error:
        st.warning(billing_error)
    if not settings.demo and st.button("Refresh payment status"):
        if time.time() - st.session_state.get("last_billing_refresh", 0) >= 15:
            display_entitlement.clear()
            st.session_state.last_billing_refresh = time.time()
            store.event("billing_refresh", identity.user_id)
            st.rerun()
        else:
            st.info("Please wait a few seconds before refreshing again.")
    if entitlement.active and billing:
        if st.button("Manage subscription"):
            try:
                # The customer ID was obtained using the verified login identity.
                portal_url = billing.portal(entitlement.customer_id, settings.app_url)
                st.link_button("Open secure billing portal", portal_url)
            except BillingUnavailable as exc:
                st.warning(str(exc))
    elif not settings.demo:
        st.markdown("### $9 / month")
        st.caption(f"Up to {settings.daily_limit} scenario/explanation requests daily. Use this same Google email at checkout.")
        st.link_button("Subscribe · $9/month", settings.payment_link, type="primary",
                       on_click=store.event, args=("checkout_click", identity.user_id))
        st.caption("Return here after checkout and refresh payment status.")
    if not settings.demo and st.button("Sign out"):
        st.logout()
    st.divider()
    st.caption("Coverage: subnetting, routing, OSPFv2, switching/STP, ACLs, and automation. This starter reference does not cover the entire CCNA exam.")


def reserve_request(kind):
    # Never authorize an API call using the display cache, a UI flag, or typed email.
    active = billing.entitlement(identity.email).active if billing else False
    return store.reserve(identity.user_id, active, kind), active


if used and not entitlement.active:
    st.info("Your free scenario is saved below. Subscribe in the sidebar to generate another or ask the tutor.")
    if st.session_state.get("paywall_seen") != identity.user_id:
        store.event("paywall_view", identity.user_id)
        st.session_state.paywall_seen = identity.user_id

practice, chat = st.tabs(["Practice scenarios", "Ask the tutor"])
topics = {"Subnetting": "1", "Routing decisions": "2", "OSPFv2": "3", "Switching, VLANs & STP": "4", "ACLs & security": "5", "Automation & AI": "6"}

with practice:
    with st.form("new_scenario"):
        c1, c2 = st.columns([2, 1])
        topic = c1.selectbox("Choose a topic", ["Subnetting"] if settings.demo else list(topics))
        difficulty = c2.selectbox("Difficulty", ["Foundation", "Exam practice", "Challenge"], disabled=topic == "Subnetting")
        focus = st.text_input("Optional focus", max_chars=1200, placeholder="For example: OSPF neighbor troubleshooting", disabled=settings.demo or topic == "Subnetting")
        if topic == "Subnetting":
            st.caption("Subnetting practice uses verified calculations for /25–/30 IPv4 LANs.")
        generate = st.form_submit_button("Generate my scenario", type="primary", disabled=bool(billing_error) or (used and not entitlement.active))
    if generate:
        request_id = None
        try:
            request_id, _ = reserve_request("scenario")
            with st.spinner("Preparing your scenario…"):
                if topic == "Subnetting":
                    scenario = subnet_scenario(42 if settings.demo else None)
                    _, all_chunks = read_chunks(ROOT / "ccna_knowledge.txt", ROOT / "docs/sources.json")
                    chunks = [c for c in all_chunks if c.id in scenario.source_ids]
                else:
                    tutor, index = model_services(str(settings.data_dir / "chroma"), settings.gemini_model, settings.embedding_model, settings.gemini_key)
                    chunks = index.retrieve(f"{topic} {focus}", topics[topic])
                    scenario = tutor.scenario(topic, difficulty, focus, chunks)
                payload = {"scenario": scenario.model_dump(), "references": [{"id": c.id, "title": c.title, "text": c.text, "url": c.url} for c in chunks]}
                store.complete(request_id, identity.user_id, payload)
            st.rerun()
        except (AccessDenied, BillingUnavailable, GenerationError) as exc:
            if request_id:
                store.fail(request_id, identity.user_id)
            st.warning(str(exc))
        except Exception:
            if request_id:
                store.fail(request_id, identity.user_id)
            st.error("The scenario could not be saved. Please retry; your free trial was not consumed.")

    latest = store.latest_scenario(identity.user_id)
    if latest:
        payload = json.loads(latest["payload"])
        current = Scenario.model_validate(payload["scenario"])
        with st.container(border=True):
            st.subheader(current.title)
            st.write(current.scenario)
            st.markdown("**" + current.question + "**")
            answered = latest["selected_answer"] is not None
            with st.form(f"answer-{latest['id']}"):
                answer = st.radio("Your answer", range(4), format_func=lambda n: f"{'ABCD'[n]}. {current.choices[n]}",
                                  index=latest["selected_answer"] if answered else None, disabled=answered)
                submitted = st.form_submit_button("Check my answer", disabled=answered)
            if submitted:
                if answer is None:
                    st.warning("Choose an answer first.")
                else:
                    store.answer(latest["id"], identity.user_id, answer)
                    store.event("answer_submitted", identity.user_id)
                    st.rerun()
            if answered:
                correct = latest["selected_answer"] == current.correct_index
                st.success("Correct — nicely reasoned.") if correct else st.warning(f"The correct answer is {'ABCD'[current.correct_index]}.")
                st.markdown(current.explanation)
                for n, reason in enumerate(current.choice_explanations):
                    st.write(f"**{'ABCD'[n]}:** {reason}")
                st.info(current.takeaway)
                with st.expander("Reference excerpts & further reading"):
                    for ref in payload["references"]:
                        if ref["id"] in current.source_ids:
                            st.markdown(f"**[{ref['id']}] {ref['title']}**")
                            st.text(ref["text"])
                            st.link_button("Read the primary reference", ref["url"])
                st.caption("Subnet calculations are verified by code. Other AI explanations should be checked against the references.")
    else:
        st.write("Choose a topic above to begin your free scenario.")

with chat:
    st.write("Ask for another explanation, compare two concepts, or work through a troubleshooting decision.")
    if not entitlement.active:
        st.caption("Tutor chat is included in the subscription. Your free scenario already includes answer feedback.")
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    question = st.chat_input("Ask about the six supported CCNA topics", max_chars=1200,
                             disabled=not entitlement.active or bool(billing_error) or settings.demo)
    if question:
        request_id = None
        fragments = []
        try:
            request_id, _ = reserve_request("chat")
            tutor, index = model_services(str(settings.data_dir / "chroma"), settings.gemini_model, settings.embedding_model, settings.gemini_key)
            chunks = index.retrieve(question)
            latest = store.latest_scenario(identity.user_id)
            scenario_context = latest["payload"] if latest else ""
            with st.chat_message("user"):
                st.write(question)
            def stream():
                for token in tutor.stream_answer(question, chunks, scenario_context):
                    fragments.append(token)
                    yield token
            with st.chat_message("assistant"):
                st.write_stream(stream())
            if not fragments:
                raise GenerationError("No answer was returned. Please retry.")
            store.complete(request_id, identity.user_id)
            st.session_state.chat_messages = (st.session_state.chat_messages + [
                {"role": "user", "content": question}, {"role": "assistant", "content": "".join(fragments)}])[-12:]
        except (AccessDenied, BillingUnavailable, GenerationError) as exc:
            if request_id:
                # Partial delivered streams count toward usage; empty failures do not consume a trial.
                if fragments:
                    store.complete(request_id, identity.user_id)
                else:
                    store.fail(request_id, identity.user_id)
            st.warning(str(exc))
        except Exception:
            if request_id:
                store.fail(request_id, identity.user_id)
            st.error("The tutor is temporarily unavailable. Please try again.")

with st.expander("Privacy & subscriptions"):
    st.write("Google verifies your sign-in. We store a hashed account ID, trial/usage counts, and generated practice scenarios. "
             "Your question and reference excerpts are sent to Google Gemini for non-numerical AI responses. "
             "Stripe processes payments; your payment card is never collected by this app. "
             "Use the same verified Google email at checkout. Manage or cancel an active subscription from the sidebar.")
    st.caption("Request counters reset at 00:00 UTC. Session chat text is not saved to the usage database. "
               "The operator must publish support contact details and full privacy/subscription terms before collecting real payments.")
