"""Chat-first CCNA tutor. Run with python start.py; keep credentials out of Git."""
import html
import time
import uuid
import streamlit as st
from tutor.config import ROOT, Settings
from tutor.identity import Identity, IdentityError, verified_identity
from tutor.billing import BillingUnavailable, Entitlement, StripeBilling
from tutor.store import AccessDenied, UsageStore
from tutor.engine import GenerationError, GeminiTutor
from tutor.knowledge import KnowledgeIndex, read_chunks
from tutor.chat import preview_response, stream_reply

st.set_page_config(page_title="CCNA Tutor", page_icon="◈", layout="wide")
settings = Settings.from_env()
st.markdown("""
<style>
:root {--ink:#172b29;--muted:#6b7876;--accent:#16796a;--line:#e9eeec;}
.stApp {background:#fff;color:var(--ink);}
[data-testid="stMainBlockContainer"] {max-width:920px;padding:2.8rem 2.5rem 6rem;}
[data-testid="stSidebar"] {background:#f7f9f8;border-right:1px solid var(--line);}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {padding-top:1.2rem;}
[data-testid="stHeader"] {background:rgba(255,255,255,.92);}
h1,h2,h3 {letter-spacing:-.035em;}
h1 {font-weight:650!important;}
.brand {display:flex;align-items:center;gap:11px;margin:0 0 22px;font-size:1.18rem;font-weight:700;letter-spacing:-.03em;}
.brand-mark {display:grid;place-items:center;width:35px;height:35px;border-radius:11px;background:#16796a;color:white;font-size:25px;}
.brand small {display:block;color:#85918e;font-size:.65rem;letter-spacing:.14em;font-weight:600;}
.chat-heading {display:flex;justify-content:space-between;align-items:center;gap:12px;padding:0 0 24px;border-bottom:1px solid var(--line);margin-bottom:26px;}
.chat-heading strong {font-size:1rem;font-weight:600;}
.status-pill {border:1px solid #dde9e4;background:#f5faf7;color:#3d6b5b;border-radius:20px;font-size:.73rem;padding:5px 11px;white-space:nowrap;}
.hero {text-align:center;padding:55px 0 22px;}
.hero-mark {display:grid;place-items:center;margin:0 auto 22px;width:59px;height:59px;border-radius:19px;background:#eaf5ef;color:#16796a;font-size:38px;}
.hero .eyebrow {font-size:.72rem;letter-spacing:.17em;color:#76837d;font-weight:650;margin-bottom:12px;}
.hero h1 {font-size:clamp(2rem,4vw,2.8rem);line-height:1.16;margin:0 auto 12px;max-width:640px;}
.hero p {color:var(--muted);font-size:1.02rem;line-height:1.7;max-width:490px;margin:0 auto;}
.st-key-starters {margin:10px 0 18px;}
.st-key-starters [data-testid="stVerticalBlockBorderWrapper"] {border-radius:16px;}
.st-key-starters button {justify-content:flex-start;text-align:left;font-weight:600;min-height:44px;}
.st-key-starters [data-testid="stCaptionContainer"] {padding:0 9px 5px;line-height:1.6;}
.st-key-history button {justify-content:flex-start;text-align:left;border-radius:9px;font-size:.88rem;overflow:hidden;}
.st-key-history button p {overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
[data-testid="stChatMessage"] {background:white;border-radius:18px;padding:1.2rem 1.1rem;margin-bottom:16px;}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {background:#f3f6f5;}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {background:white;}
[data-testid="stChatMessage"] p {line-height:1.8;}
[data-testid="stBottomBlockContainer"] {max-width:920px;padding:0 2.5rem 1.4rem;}
[data-testid="stChatInput"] {border-radius:21px;border:1px solid #dce4e0;box-shadow:0 5px 24px #16362b08;background:#f9fbfa;}
[data-testid="stChatInput"] textarea {font-size:.97rem;}
.st-key-subscription_gate {background:#f2f8f4;border:1px solid #dcebe1;border-radius:18px;padding:22px!important;margin:14px 0 24px;}
.st-key-subscription_gate h3 {font-size:1.25rem;}
.st-key-plan {background:white;border-radius:13px;padding:15px!important;border:1px solid var(--line);}
.small-note {color:#85918b;text-align:center;font-size:.76rem;margin-top:16px;}
@media(max-width:640px) {
 [data-testid="stMainBlockContainer"] {padding:2.2rem 1rem 4rem;}
 [data-testid="stBottomBlockContainer"] {padding:0 1rem .8rem;}
 .hero {padding-top:26px;}
 .chat-heading {align-items:flex-start;}
}
</style>
""", unsafe_allow_html=True)

errors = settings.errors()
if errors:
    st.title("CCNA Tutor")
    st.info("The tutor is being configured. Please return shortly.")
    if not __import__("os").getenv("RENDER"):
        st.code("\n".join(errors))
    st.stop()


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


@st.cache_data(ttl=30, show_spinner=False)
def display_entitlement(email, price_id, mode, _billing):
    return _billing.entitlement(email)


def brand():
    st.markdown('<div class="brand"><span class="brand-mark">◈</span><div>CCNA Tutor<small>YOUR NETWORKING STUDY SPACE</small></div></div>', unsafe_allow_html=True)


def hero():
    st.markdown("""<div class="hero"><div class="hero-mark">◈</div>
    <div class="eyebrow">CCNA 200-301 · SCENARIOS & EXPLANATIONS</div>
    <h1>What are we learning today?</h1>
    <p>Untangle a tricky concept, work through a network problem, or practice your next exam scenario.</p></div>""", unsafe_allow_html=True)


store_dir = settings.data_dir / "demo" if settings.demo else settings.data_dir
store = usage_store(str(store_dir / "usage.sqlite3"), settings.daily_limit, settings.global_daily_limit, settings.cooldown_seconds)
if "visit_logged" not in st.session_state:
    store.event("visit")
    st.session_state.visit_logged = True

if settings.demo:
    identity = Identity(st.session_state.get("demo_viewer", "local-demo"), "demo@example.invalid")
else:
    if "auth" not in st.secrets:
        st.info("Sign-in is being configured. Please return shortly.")
        st.stop()
    if not st.user.is_logged_in:
        with st.sidebar:
            brand()
            st.caption("A focused workspace for understanding networks.")
            st.divider()
            st.markdown("**One prompt on us.**")
            st.caption("Then $9/month for continued practice.")
        hero()
        with st.container(border=True):
            st.subheader("Start your first conversation")
            st.write("Sign in with Google for one free AI response. Your chats and trial stay attached to your account.")
            if st.button("Continue with Google", type="primary", icon=":material/login:"):
                st.login("google")
            st.caption(f"Then $9/month · Up to {settings.daily_limit} prompts/day · Manage or cancel through Stripe.")
        st.caption("Independent study tool. Focused coverage: subnetting, routing, OSPF, VLANs/STP, ACLs, and automation.")
        st.stop()
    try:
        identity = verified_identity(st.user.to_dict())
    except IdentityError as exc:
        st.warning(str(exc))
        if st.button("Sign out"):
            st.logout()
        st.stop()

conversations = store.conversations(identity.user_id)
if st.session_state.get("viewer") != identity.user_id:
    st.session_state.viewer = identity.user_id
    st.session_state.conversation_id = conversations[0]["id"] if conversations else None
    st.session_state.pop("paywall_seen", None)
    store.event("login", identity.user_id)

billing = None if settings.demo else stripe_service(settings.stripe_price_id, settings.billing_mode, settings.stripe_key)
entitlement = Entitlement()
billing_error = None
if billing:
    try:
        entitlement = display_entitlement(identity.email, settings.stripe_price_id, settings.billing_mode, billing)
    except BillingUnavailable as exc:
        billing_error = str(exc)
used = store.trial_used(identity.user_id)
locked = used and not entitlement.active
disabled = locked or bool(billing_error)


def checkout_button(key, width="stretch"):
    if settings.demo:
        st.button("Subscribe · $9/month", key=key, type="primary", disabled=True, width=width,
                  help="Subscriptions are disabled in this offline local preview.")
    else:
        st.link_button("Subscribe · $9/month", settings.payment_link, key=key, type="primary", width=width,
                       on_click=store.event, args=("checkout_click", identity.user_id))


def refresh_payment(key):
    if st.button("I've paid · Refresh access", key=key, width="stretch", icon=":material/refresh:"):
        if time.time() - st.session_state.get("last_billing_refresh", 0) >= 15:
            display_entitlement.clear()
            st.session_state.last_billing_refresh = time.time()
            store.event("billing_refresh", identity.user_id)
            st.rerun()
        else:
            st.info("Please wait a few seconds before refreshing again.")


with st.sidebar:
    brand()
    if st.button("New chat", icon=":material/edit_square:", width="stretch"):
        st.session_state.conversation_id = None
        st.rerun()
    st.space("small")
    st.caption("RECENT CHATS")
    with st.container(key="history"):
        if not conversations:
            st.caption("Your conversations will appear here.")
        for conversation in conversations:
            selected = conversation["id"] == st.session_state.conversation_id
            if st.button(conversation["title"], key="chat-" + conversation["id"],
                         type="secondary" if selected else "tertiary", width="stretch", icon=":material/chat_bubble_outline:"):
                st.session_state.conversation_id = conversation["id"]
                st.rerun()
    st.space("medium")
    with st.container(key="plan"):
        if entitlement.active:
            st.markdown("**CCNA Tutor Pass**")
            st.caption(f"Subscriber access · Up to {settings.daily_limit} prompts/day")
            if st.button("Manage subscription", width="stretch"):
                try:
                    portal_url = billing.portal(entitlement.customer_id, settings.app_url)
                    st.link_button("Open secure billing portal", portal_url)
                except BillingUnavailable as exc:
                    st.warning(str(exc))
        else:
            st.markdown("**Keep the conversation going**")
            st.caption("1 free response used" if used else "1 free response available")
            st.caption(f"$9/month · Up to {settings.daily_limit} prompts/day")
            checkout_button("sidebar-checkout")
        if billing:
            refresh_payment("sidebar-refresh")
    if billing_error:
        st.warning(billing_error)
    st.divider()
    st.caption("LOCAL PREVIEW" if settings.demo else "SIGNED IN")
    st.write("Demo account" if settings.demo else identity.email)
    if settings.demo:
        # A deliberate preview reset uses a separate local identity, never a real account.
        if st.button("Restart local preview", type="tertiary", icon=":material/restart_alt:",
                     help="Start a new offline preview trial. Real account trials cannot be reset here."):
            st.session_state.demo_viewer = "local-preview-" + uuid.uuid4().hex
            st.rerun()
    elif st.button("Sign out", type="tertiary"):
        st.logout()
    with st.expander("About & privacy"):
        st.caption("Independent CCNA study tool. The six-topic reference does not cover the entire exam.")
        st.caption("Google verifies sign-in. We store a hashed account ID, usage, and chat messages with their references. Questions, recent conversation, and excerpts are sent to Gemini for AI replies. Avoid secrets in prompts.")
        st.caption("Stripe processes payments. Use the same Google email at checkout. Manage or cancel from the subscription panel. Request allowances reset at 00:00 UTC.")
        st.caption("AI answers may be incorrect. Check the linked references.")

conversation_id = st.session_state.conversation_id
messages = store.messages(conversation_id, identity.user_id) if conversation_id else []
current_title = next((c["title"] for c in conversations if c["id"] == conversation_id), "New conversation")
status = "Tutor Pass" if entitlement.active else ("Free prompt used" if used else "1 free prompt")
st.markdown(f'<div class="chat-heading"><strong>{html.escape(current_title)}</strong><span class="status-pill">{status}</span></div>', unsafe_allow_html=True)
if settings.demo:
    st.caption("LOCAL PREVIEW · Curated offline examples, not Gemini responses. No sign-in or payments are made.")
elif settings.billing_mode == "test":
    st.caption("STRIPE SANDBOX · Test subscriptions only. No real payments.")

starter_question = None
if not messages:
    hero()
    with st.container(key="starters"):
        prompts = [
            ("Work through a subnet", "Explain the network and broadcast addresses for 192.168.10.77/26.", "Find boundaries and usable hosts.", ":material/lan:"),
            ("Troubleshoot OSPF", "Why might OSPF neighbors get stuck in ExStart?", "Reason through a neighbor problem.", ":material/hub:"),
            ("Compare routing decisions", "Explain longest prefix match versus administrative distance.", "Understand which route wins.", ":material/alt_route:"),
            ("Practice a switching scenario", "Give me an original CCNA practice scenario about STP root bridge election, with an answer and explanation.", "Put VLAN and STP knowledge to work.", ":material/account_tree:"),
        ]
        for row in range(2):
            columns = st.columns(2)
            for column, (title, prompt, subtitle, icon) in zip(columns, prompts[row * 2:row * 2 + 2]):
                with column:
                    with st.container(border=True):
                        if st.button(title, key="starter-" + title, type="tertiary", icon=icon, width="stretch", disabled=disabled):
                            starter_question = prompt
                        st.caption(subtitle)
    if not used:
        st.markdown('<p class="small-note">Choose a starter or type your question below. Your first response is free.</p>', unsafe_allow_html=True)

for message_number, message in enumerate(messages):
    with st.chat_message(message["role"], avatar="user" if message["role"] == "user" else ":material/auto_awesome:"):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            if message.get("interrupted"):
                st.caption("This response was interrupted. The text delivered so far is saved.")
            if message.get("references"):
                with st.expander("Sources & reference excerpts", icon=":material/menu_book:"):
                    for ref in message["references"]:
                        st.markdown(f"**[{ref['id']}] {ref['title']}**")
                        st.text(ref["text"])
                        st.link_button("Read reference", ref["url"], key=f"ref-{conversation_id}-{message_number}-{ref['id']}")

if locked:
    with st.container(key="subscription_gate"):
        st.subheader("Continue with CCNA Tutor")
        st.write("Your first response is saved. Subscribe for **$9/month** to ask follow-up questions and start more conversations.")
        st.caption(f"Up to {settings.daily_limit} prompts per day · Manage or cancel through Stripe")
        checkout_button("main-checkout", "content")
        if settings.demo:
            st.caption("The subscription gate is shown for testing. To try the interface again, use “Restart local preview” in the sidebar.")
        else:
            st.caption(f"Use {identity.email} at checkout, then return to this conversation.")
            refresh_payment("main-refresh")
    if st.session_state.get("paywall_seen") != identity.user_id:
        store.event("paywall_view", identity.user_id)
        st.session_state.paywall_seen = identity.user_id

notice = st.session_state.pop("chat_notice", None)
if notice:
    st.warning(notice)

placeholder = "Subscribe to continue the conversation" if locked else "Ask CCNA Tutor anything about the six supported topics…"
question = st.chat_input(placeholder, max_chars=1200, disabled=disabled, key="composer") or starter_question
if question:
    active_conversation = conversation_id or str(uuid.uuid4())

    def check_subscription():
        return billing.entitlement(identity.email).active if billing else False

    def prepare_response():
        if settings.demo:
            section, answer = preview_response(question)
            _, all_chunks = read_chunks(ROOT / "ccna_knowledge.txt", ROOT / "docs/sources.json")
            chunks = [chunk for chunk in all_chunks if chunk.section == section]
            tokens = iter(answer.splitlines(keepends=True))
        else:
            tutor, index = model_services(str(settings.data_dir / "chroma"), settings.gemini_model, settings.embedding_model, settings.gemini_key)
            # Include the previous question so short follow-ups retrieve the relevant topic.
            prior_questions = [m["content"] for m in messages[-4:] if m["role"] == "user"]
            chunks = index.retrieve("\n".join(prior_questions + [question])[-3600:])
            tokens = tutor.stream_answer(question, chunks, history=messages)
        references = [{"id": c.id, "title": c.title, "text": c.text, "url": c.url} for c in chunks]
        return tokens, references

    with st.chat_message("user", avatar="user"):
        st.markdown(question)
    try:
        with st.chat_message("assistant", avatar=":material/auto_awesome:"):
            with st.spinner("Thinking through the network…"):
                st.write_stream(stream_reply(store, identity.user_id, active_conversation, question, check_subscription, prepare_response))
    except AccessDenied as exc:
        display_entitlement.clear()
        st.session_state.chat_notice = str(exc)
    except (BillingUnavailable, GenerationError) as exc:
        st.session_state.chat_notice = str(exc)
    except Exception:
        st.session_state.chat_notice = "The tutor is temporarily unavailable. Please try again."
    # Re-render from the ledger: saved history and paywall update together.
    if store.messages(active_conversation, identity.user_id, limit=1):
        st.session_state.conversation_id = active_conversation
    st.rerun()
