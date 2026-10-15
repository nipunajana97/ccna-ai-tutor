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

st.set_page_config(page_title="CCNA Tutor", page_icon="🌐", layout="wide")
settings = Settings.from_env()
st.markdown("""
<style>
:root {
 --ink:#142538;--muted:#687c90;--accent:#0b8b91;--line:#e2eaf1;
 --canvas:#f7f9fc;--sidebar:#101f30;--mint:#bcf4da;
}
.stApp {
 color:var(--ink);
 background:radial-gradient(ellipse at 55% 0%,#e8f5f6 0,transparent 48%),var(--canvas);
 font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}
h1,h2,h3,h4,button,input,textarea,[data-testid="stMarkdownContainer"] {
 font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}
h1,h2,h3 {letter-spacing:-.045em;}
[data-testid="stMainBlockContainer"] {max-width:1000px;padding:1.4rem 2.6rem 8rem;}
[data-testid="stHeader"] {background:transparent;}
.stAppDeployButton {display:none;}
/* The native reopen button lives inside this toolbar; keep its container visible. */
[data-testid="stToolbar"] {display:flex;}
[data-testid="stExpandSidebarButton"] {
 visibility:visible!important;opacity:1!important;pointer-events:auto!important;
 background:#fff!important;border:1px solid #ccdce4!important;color:#17434a!important;
 border-radius:10px;min-width:40px;min-height:40px;box-shadow:0 2px 9px #18394b0a;
}
[data-testid="stExpandSidebarButton"] * {color:#17434a!important;-webkit-text-fill-color:#17434a!important;}
[data-testid="stExpandSidebarButton"]:hover {background:#e9f5f1!important;border-color:#68a89c!important;}
[data-testid="stExpandSidebarButton"]:focus-visible {outline:3px solid #0b8b91;outline-offset:3px;}
[data-testid="stSidebarCollapseButton"] {visibility:visible!important;opacity:1!important;}
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarCollapseButton"] button * {color:#d5f5e9!important;-webkit-text-fill-color:#d5f5e9!important;}
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {gap:.8rem;}
.brand {display:flex;align-items:center;gap:12px;margin:0 0 22px;color:#f3f8ff;}
.brand-name {font-size:1.17rem;font-weight:720;letter-spacing:-.045em;line-height:1.2;}
.brand small {display:block;color:#829ab2;font-size:.64rem;letter-spacing:.17em;font-weight:650;margin-top:5px;}
.brand-mark {
 display:grid;place-items:center;flex-shrink:0;width:39px;height:39px;border-radius:12px;
 background:linear-gradient(140deg,#b9f5d9,#67cdd8);color:#103c48;box-shadow:0 5px 16px #0002;
}
.brand-mark svg {width:26px;height:26px;}
[data-testid="stSidebar"] {background:var(--sidebar);border-right:1px solid #203246;}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {padding-top:.4rem;}
[data-testid="stSidebarUserContent"] {padding:1.15rem 1.05rem 1rem;}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {color:#e3ecf6;}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {color:#8fa6bd;font-size:.74rem;line-height:1.55;}
[data-testid="stSidebar"] h3 {color:#f1f7fd;}
[data-testid="stSidebar"] hr {border-color:#293b4e;margin:.85rem 0;}
[data-testid="stSidebar"] button {
 border-color:#314357;background:#182d42;color:#e5eef9;border-radius:10px;min-height:39px;
 transition:background .18s,border-color .18s,transform .18s;
}
[data-testid="stSidebar"] button p {color:inherit;font-size:.8rem;}
[data-testid="stSidebar"] button:hover {background:#233d55;border-color:#5d8398;}
[data-testid="stSidebar"] button:focus-visible {outline:3px solid #89dccb;outline-offset:2px;}
[data-testid="stSidebar"] button[kind="tertiary"] {background:transparent;border-color:transparent;color:#a4bbce;}
[data-testid="stSidebar"] button[kind="tertiary"]:hover {background:#1c3248;color:white;}
.st-key-new-chat button {background:#bcf4da!important;border:0!important;color:#123b3a!important;font-weight:700;min-height:42px;}
.st-key-new-chat button * {color:#123b3a!important;-webkit-text-fill-color:#123b3a!important;}
.st-key-new-chat button:hover {background:#d1ffe9!important;transform:translateY(-1px);}
.st-key-restart-preview button {min-height:30px!important;font-size:.73rem;}
.st-key-history {min-height:60px;margin:0 0 8px;}
.st-key-history button {justify-content:flex-start;text-align:left;border-radius:9px;overflow:hidden;margin:1px 0;}
.st-key-history button p {overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.77rem;}
.st-key-history button[kind="secondary"] {background:#203c51;border-color:#34596a;color:#d5f5e9;}
.history-empty {border:1px dashed #31465a;border-radius:12px;padding:15px 12px;margin:0 0 12px;}
.history-empty strong {display:block;color:#b7c9d8;font-size:.75rem;font-weight:550;margin-bottom:4px;}
.history-empty span {display:block;color:#778fa6;font-size:.69rem;line-height:1.5;}
.sidebar-label {font-size:.62rem;font-weight:700;letter-spacing:.15em;color:#7791a9;margin:18px 0 10px;}
.st-key-plan {
 border:1px solid #325267;border-radius:15px;padding:16px!important;
 background:radial-gradient(ellipse at 100% 0%,#21485b 0,transparent 65%),#192e42;
}
.plan-kicker {color:#a8edcf;font-weight:700;font-size:.61rem;letter-spacing:.14em;}
.plan-title {font-size:.95rem;font-weight:650;color:#f0f7fd;margin:6px 0 8px;letter-spacing:-.02em;}
.plan-price {color:white;font-size:1.7rem;letter-spacing:-.06em;font-weight:650;margin:6px 0;}
.plan-price span {font-size:.72rem;font-weight:400;letter-spacing:0;color:#a5b8c9;}
.plan-trial {font-size:.7rem;color:#9fd8c7;margin:0 0 8px;}
.st-key-plan button[kind="primary"],.st-key-plan a[kind="primary"] {
 background:#bcf4da!important;border-color:#bcf4da!important;color:#103f38!important;border-radius:9px;
}
.st-key-plan button[kind="primary"] *,.st-key-plan a[kind="primary"] * {
 color:#103f38!important;-webkit-text-fill-color:#103f38!important;
}
.st-key-plan button[kind="primary"]:disabled {
 opacity:1!important;background:#9dbeb1!important;border-color:#9dbeb1!important;color:#183e35!important;cursor:not-allowed;
}
.st-key-plan button[kind="primary"]:disabled * {color:#183e35!important;-webkit-text-fill-color:#183e35!important;}
.st-key-plan a p {font-size:.78rem;}
.st-key-plan button[kind="secondary"] {background:transparent;font-size:.72rem;min-height:32px;}
.account {display:flex;align-items:center;gap:10px;margin:4px 0 9px;}
.account-avatar {display:grid;place-items:center;width:32px;height:32px;border-radius:50%;background:#2c4357;color:#d9e8f4;font-size:.78rem;font-weight:650;}
.account strong {font-size:.75rem;color:#e2ebf4;font-weight:550;display:block;overflow-wrap:anywhere;}
.account small {font-size:.65rem;color:#7f98ad;display:block;margin-top:3px;}
[data-testid="stSidebar"] [data-testid="stExpander"] {background:transparent;border-color:#2b4055;color:#9bb0c4;border-radius:10px;}
[data-testid="stSidebar"] [data-testid="stExpander"] details summary p {color:#9bb0c4;font-size:.73rem;}
.chat-heading {display:flex;justify-content:space-between;align-items:center;gap:16px;margin:12px 0 5px;}
.heading-kicker {font-size:.62rem;letter-spacing:.16em;color:#8394a5;font-weight:700;margin-bottom:6px;}
.chat-heading strong {font-size:.91rem;font-weight:650;letter-spacing:-.02em;display:block;}
.status-pill {display:flex;align-items:center;gap:7px;flex-shrink:0;border:1px solid #d0e8dd;background:#eef8f3;color:#32705c;border-radius:20px;font-size:.68rem;padding:7px 12px;font-weight:550;}
.status-pill::before {content:"";height:5px;width:5px;border-radius:50%;background:#28a77b;}
.status-pill.used {border-color:#eadfce;background:#fcf8ef;color:#8d6a2d;}
.status-pill.used::before {background:#ca9a49;}
.mode-banner {display:flex;align-items:center;flex-wrap:wrap;gap:7px 10px;padding:8px 12px;border-radius:9px;background:#edf2f7;border:1px solid #e0e8ef;color:#7b8c9d;font-size:.67rem;margin:0;}
.mode-banner strong {font-weight:650;color:#50677e;}
.hero {text-align:center;padding:20px 0 12px;}
.hero-network {display:flex;align-items:center;justify-content:center;gap:8px;margin-bottom:12px;}
.network-node {width:10px;height:10px;border-radius:3px;background:#c4dbe2;box-shadow:0 0 0 4px #edf5f7;transform:rotate(45deg);}
.network-node.main {height:36px;width:36px;border-radius:12px;background:linear-gradient(135deg,#139c9c,#1b697f);transform:rotate(0);box-shadow:0 7px 20px #0b848023;display:grid;place-items:center;color:#d8fff0;}
.network-node.main svg {width:25px;height:25px;}
.network-link {height:1px;width:25px;background:linear-gradient(90deg,#d6e4ea,#8dbcc6);}
.hero .eyebrow {font-size:.62rem;letter-spacing:.15em;color:#637c8e;font-weight:700;margin-bottom:10px;}
.hero h1 {font-size:clamp(1.95rem,3.3vw,2.55rem);font-weight:720;line-height:1.1;padding:0!important;margin:0 auto 12px!important;max-width:760px;}
.hero h1 span {background:linear-gradient(105deg,#0f887d,#3486ad);background-clip:text;-webkit-background-clip:text;color:transparent;}
.hero p {color:#657b8e;font-size:.82rem;line-height:1.65;max-width:470px;margin:0 auto!important;}
.hero.locked {padding:24px 0 8px;}
.hero.locked h1 {font-size:2.15rem;}
.topic-strip {display:flex;justify-content:center;flex-wrap:wrap;gap:7px;margin:12px 0 2px;}
.topic-strip span {font-size:.61rem;color:#6d8394;border:1px solid #dee8ee;background:#ffffffa8;border-radius:6px;padding:4px 8px;}
.st-key-starters {margin:0 0 5px;}
.st-key-starters [data-testid="stHorizontalBlock"] {gap:14px;}
.st-key-starters [data-testid="stVerticalBlock"] {gap:5px;}
[class*="st-key-prompt-"] {
 background:#ffffffd9;border:1px solid #e0e8f0;border-radius:16px;padding:15px!important;
 box-shadow:0 3px 10px #172c4203;transition:border-color .2s,box-shadow .2s,transform .2s;
}
[class*="st-key-prompt-"]:hover {border-color:#a5c9cd;box-shadow:0 8px 22px #173b5510;transform:translateY(-2px);}
.card-top {display:flex;align-items:center;justify-content:space-between;margin-bottom:7px;}
.card-icon {display:grid;place-items:center;width:31px;height:31px;border-radius:10px;background:#e5f4f1;color:#248974;font-size:.78rem;font-weight:700;letter-spacing:-.05em;}
.card-topic {font-size:.57rem;text-transform:uppercase;letter-spacing:.12em;color:#637b8f;font-weight:650;}
.st-key-prompt-ospf .card-icon {background:#e9effd;color:#5e76b8;}
.st-key-prompt-routing .card-icon {background:#f0ebfa;color:#8b6abd;}
.st-key-prompt-switching .card-icon {background:#fcf0e4;color:#bb8a46;}
.st-key-starters button {background:transparent;border:0;padding:0!important;justify-content:flex-start;text-align:left;min-height:29px;color:#1d344a;}
.st-key-starters button p {font-size:.84rem;font-weight:650;letter-spacing:-.02em;color:inherit;}
.st-key-starters button:hover {color:#0b8b91;background:transparent;}
.st-key-starters button:focus-visible {outline:3px solid #8bc9c6;outline-offset:5px;}
.st-key-starters [data-testid="stCaptionContainer"] p {font-size:.71rem;line-height:1.5;color:#667b8f;margin:0;}
.small-note {color:#6f8395;text-align:center;font-size:.66rem;margin:10px 0 0;}
[data-testid="stChatMessage"] {background:transparent;border-radius:16px;padding:1.2rem .8rem;margin:4px 0 12px;}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {background:#eaf0f6;border:1px solid #e2e9f0;margin-left:9%;}
[data-testid="stChatMessage"] p {line-height:1.75;font-size:.9rem;}
[data-testid="stChatMessage"] [data-testid="stChatMessageAvatarCustom"] {background:#dff2ed;color:#107f76;}
[data-testid="stChatMessage"] [data-testid="stExpander"] {border:1px solid #e1e9ef;border-radius:10px;background:#ffffffb5;}
[data-testid="stChatMessage"] table {font-size:.8rem;}
[data-testid="stBottom"] {background:linear-gradient(0deg,#f7f9fc 75%,#f7f9fc00);}
[data-testid="stBottomBlockContainer"] {max-width:1000px;padding:.4rem 2.6rem 1rem;}
[data-testid="stBottomBlockContainer"]::after {content:"Independent CCNA study tool · Check AI answers against the references";display:block;text-align:center;font-size:10px;color:#97a6b4;margin-top:9px;}
[data-testid="stChatInput"] {border-radius:18px;border:1px solid #ccdce4;box-shadow:0 7px 30px #1a405a0c;background:#fff;min-height:58px;}
[data-testid="stChatInput"]:focus-within {border-color:#66b8b0;box-shadow:0 0 0 3px #a6dcd72b,0 7px 30px #1a405a0c;}
[data-testid="stChatInput"] textarea {font-size:.86rem;line-height:1.55;}
.st-key-subscription_gate {
 background:radial-gradient(ellipse at 100% 0%,#e2f4ed,transparent 65%),#fff;
 border:1px solid #d6e6e2;border-radius:20px;padding:25px!important;margin:7px 0 12px;
 box-shadow:0 7px 30px #24473d07;
}
.st-key-subscription_gate h3 {font-size:1.35rem;font-weight:670;letter-spacing:-.04em;padding-top:0;}
.st-key-subscription_gate [data-testid="stMarkdownContainer"] p {font-size:.82rem;color:#768b94;line-height:1.7;}
.gate-kicker {font-size:.61rem;color:#249579;letter-spacing:.14em;font-weight:750;margin-bottom:9px;}
.gate-features {display:flex;flex-wrap:wrap;gap:8px 15px;margin:14px 0 12px;}
.gate-features span {font-size:.68rem;color:#4f796a;}
.gate-features span::before {content:"✓";margin-right:5px;font-weight:700;color:#279779;}
.gate-price {font-size:2.7rem;line-height:1.1;letter-spacing:-.07em;font-weight:700;color:#193e3d;margin:5px 0 8px;}
.gate-price span {font-size:.75rem;letter-spacing:0;font-weight:400;color:#7c9890;}
.st-key-subscription_gate button[kind="primary"],.st-key-subscription_gate a[kind="primary"] {
 background:#087a70!important;border-color:#087a70!important;color:#fff!important;border-radius:10px;min-height:42px;
}
.st-key-subscription_gate button[kind="primary"] *,.st-key-subscription_gate a[kind="primary"] * {
 color:#fff!important;-webkit-text-fill-color:#fff!important;
}
.st-key-subscription_gate button[kind="primary"]:disabled {
 opacity:1!important;background:#d8e5e1!important;border-color:#d8e5e1!important;color:#244c42!important;cursor:not-allowed;
}
.st-key-subscription_gate button[kind="primary"]:disabled * {color:#244c42!important;-webkit-text-fill-color:#244c42!important;}
.st-key-subscription_gate [data-testid="stCaptionContainer"] p {font-size:.65rem;color:#8a9a9d;line-height:1.6;}
@media(min-width:1024px) {
 [data-testid="stSidebar"][aria-expanded="true"] {width:280px!important;min-width:280px!important;max-width:280px!important;}
}
@media(max-height:800px) and (min-width:768px) {
 .hero {padding-top:16px;padding-bottom:10px;}
 .hero-network {margin-bottom:12px;}
 .topic-strip {margin-top:12px;}
 .brand {margin-bottom:15px;}
 .sidebar-label {margin-top:14px;}
}
@media(max-width:640px) {
 [data-testid="stMainBlockContainer"] {padding:1.2rem 1rem 7rem;}
 [data-testid="stBottomBlockContainer"] {padding:.4rem 1rem .8rem;}
 .hero {padding-top:20px;}
 .hero h1 {font-size:1.95rem;}
 .hero.locked h1 {font-size:1.8rem;}
 .hero p {font-size:.8rem;}
 .topic-strip {gap:5px;}
 .chat-heading {align-items:flex-start;}
 .status-pill {font-size:.6rem;padding:6px 8px;}
 [class*="st-key-prompt-"] {padding:12px!important;}
 .st-key-starters [data-testid="stHorizontalBlock"] {gap:10px;}
 .st-key-starters button p {font-size:.79rem;}
 .st-key-subscription_gate {padding:19px!important;}
}
@media(prefers-reduced-motion:reduce) {
 [class*="st-key-prompt-"],[data-testid="stSidebar"] button {transition:none!important;transform:none!important;}
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
def model_services(path, provider, model, embedding_model, ollama_url, embedding_profile, _key, _token):
    if provider == "ollama":
        from tutor.ollama_backend import OllamaTutor
        tutor = OllamaTutor(ollama_url, model, embedding_model, _token)
    else:
        tutor = GeminiTutor(_key, model, embedding_model)
    index = KnowledgeIndex(path, ROOT / "ccna_knowledge.txt", ROOT / "docs/sources.json", embedding_model, tutor.embed,
                           embedding_profile=embedding_profile, top_k=2 if provider == "ollama" else 4)
    return tutor, index


@st.cache_data(ttl=30, show_spinner=False)
def display_entitlement(email, price_id, mode, _billing):
    return _billing.entitlement(email)


NETWORK_ICON = '<svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><path d="M10 10L22 10M10 10L16 23M22 10L16 23" stroke="currentColor" stroke-width="1.5"/><rect x="5" y="5" width="9" height="9" rx="2.5" fill="currentColor"/><rect x="18" y="5" width="9" height="9" rx="2.5" fill="currentColor"/><rect x="11.5" y="19" width="9" height="9" rx="2.5" fill="currentColor"/></svg>'


def brand():
    st.markdown(f'<div class="brand"><span class="brand-mark">{NETWORK_ICON}</span><div class="brand-name">CCNA Tutor<small>YOUR NETWORKING STUDY SPACE</small></div></div>', unsafe_allow_html=True)


def hero(locked=False):
    title = 'Keep your curiosity.<br><span>Continue the conversation.</span>' if locked else 'Build confidence.<br><span>One network at a time.</span>'
    description = 'Your next question, clearer explanations, and more practice — all in one study space.' if locked else 'Make sense of tricky concepts. Work through real-world scenarios. Find the reasoning behind every answer.'
    st.markdown(f'''<div class="hero{' locked' if locked else ''}">
    <div class="hero-network"><span class="network-node"></span><span class="network-link"></span><span class="network-node main">{NETWORK_ICON}</span><span class="network-link"></span><span class="network-node"></span></div>
    <div class="eyebrow">YOUR CCNA 200-301 STUDY PARTNER</div>
    <h1>{title}</h1><p>{description}</p>
    <div class="topic-strip"><span>Subnetting</span><span>Routing</span><span>OSPF</span><span>VLANs & STP</span><span>Security</span><span>Automation</span></div></div>''', unsafe_allow_html=True)


store_dir = settings.data_dir / ("local-ai" if settings.local_test else "demo") if settings.preview else settings.data_dir
store = usage_store(str(store_dir / "usage.sqlite3"), settings.daily_limit, settings.global_daily_limit, settings.cooldown_seconds)
if "visit_logged" not in st.session_state:
    store.event("visit")
    st.session_state.visit_logged = True

preview_key = "local_ai_viewer" if settings.local_test else "demo_viewer"
if settings.preview:
    default_viewer = "local-ai-test" if settings.local_test else "local-demo"
    identity = Identity(st.session_state.get(preview_key, default_viewer), "preview@example.invalid")
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

billing = None if settings.preview else stripe_service(settings.stripe_price_id, settings.billing_mode, settings.stripe_key)
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
    if settings.preview:
        st.button("Subscribe · $9/month", key=key, type="primary", disabled=True, width=width,
                  help="Subscriptions are disabled in local testing.")
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
    with st.container(key="new-chat"):
        if st.button("New chat", icon=":material/add:", width="stretch"):
            st.session_state.conversation_id = None
            st.rerun()
    if settings.preview:
        with st.container(key="restart-preview"):
            # A local preview reset cannot alter a real account's trial or history.
            if st.button("Restart local AI trial" if settings.local_test else "Restart local preview", type="tertiary", icon=":material/restart_alt:", width="stretch",
                         help="Start another local test trial. Real account trials cannot be reset here."):
                st.session_state[preview_key] = "local-preview-" + uuid.uuid4().hex
                st.rerun()
    st.markdown('<div class="sidebar-label">RECENT CONVERSATIONS</div>', unsafe_allow_html=True)
    with st.container(key="history"):
        if not conversations:
            st.markdown('<div class="history-empty"><strong>A fresh space for your questions</strong><span>Your saved conversations will appear here.</span></div>', unsafe_allow_html=True)
        for conversation in conversations:
            selected = conversation["id"] == st.session_state.conversation_id
            if st.button(conversation["title"], key="chat-" + conversation["id"],
                         type="secondary" if selected else "tertiary", width="stretch", icon=":material/chat_bubble_outline:"):
                st.session_state.conversation_id = conversation["id"]
                st.rerun()
    with st.container(key="plan"):
        if entitlement.active:
            st.markdown('<div class="plan-kicker">YOUR MEMBERSHIP</div><div class="plan-title">CCNA Tutor Pass</div>', unsafe_allow_html=True)
            st.caption(f"Subscriber access · Up to {settings.daily_limit} prompts/day")
            if st.button("Manage subscription", width="stretch"):
                try:
                    portal_url = billing.portal(entitlement.customer_id, settings.app_url)
                    st.link_button("Open secure billing portal", portal_url)
                except BillingUnavailable as exc:
                    st.warning(str(exc))
        else:
            trial_label = "Your free response has been used" if used else "Your first response is on us"
            st.markdown(f'<div class="plan-kicker">A LITTLE PRACTICE, EVERY DAY</div><div class="plan-title">Go further with Tutor Pass</div><div class="plan-price">$9<span> / month</span></div><div class="plan-trial">{trial_label}</div>', unsafe_allow_html=True)
            checkout_button("sidebar-checkout")
            st.caption(f"Up to {settings.daily_limit} prompts daily · Cancel anytime")
        if billing:
            refresh_payment("sidebar-refresh")
    if billing_error:
        st.warning(billing_error)
    st.divider()
    account_name = ("Local AI account" if settings.local_test else "Demo account") if settings.preview else html.escape(identity.email)
    account_status = ("Local AI test" if settings.local_test else "Local preview") if settings.preview else ("Tutor Pass member" if entitlement.active else "Free account")
    initial = "L" if settings.preview else html.escape(identity.email[0].upper())
    st.markdown(f'<div class="account"><div class="account-avatar">{initial}</div><div><strong>{account_name}</strong><small>{account_status}</small></div></div>', unsafe_allow_html=True)
    if not settings.preview and st.button("Sign out", type="tertiary"):
        st.logout()
    with st.expander("About & privacy"):
        st.caption("Independent CCNA study tool. The six-topic reference does not cover the entire exam.")
        st.caption("We store chat messages, source excerpts, and usage with your account ID.")
        if settings.preview:
            st.caption("Local tests use a separate test identity and database. Login and payment calls are disabled.")
        else:
            st.caption("Google verifies sign-in. Stripe processes subscription payments.")
        if settings.ai_provider == "ollama":
            st.caption("Questions, recent conversation, and excerpts are processed by the configured Ollama server. Avoid secrets in prompts.")
        else:
            st.caption("Questions, recent conversation, and excerpts are sent to Google Gemini. Avoid secrets in prompts.")
        st.caption("Stripe processes payments. Use the same Google email at checkout. Manage or cancel from the subscription panel. Request allowances reset at 00:00 UTC.")
        st.caption("AI answers may be incorrect. Check the linked references.")

conversation_id = st.session_state.conversation_id
messages = store.messages(conversation_id, identity.user_id) if conversation_id else []
current_title = next((c["title"] for c in conversations if c["id"] == conversation_id), "New conversation")
status = "Tutor Pass" if entitlement.active else ("Free prompt used" if used else "1 free prompt")
status_class = "status-pill used" if locked else "status-pill"
st.markdown(f'<div class="chat-heading"><div><div class="heading-kicker">YOUR STUDY WORKSPACE</div><strong>{html.escape(current_title)}</strong></div><span class="{status_class}">{status}</span></div>', unsafe_allow_html=True)
if settings.local_test:
    st.markdown(f'<div class="mode-banner"><strong>Local AI test</strong><span>Real Ollama answers · {html.escape(settings.model)} · Login and payments disabled</span></div>', unsafe_allow_html=True)
elif settings.demo:
    st.markdown('<div class="mode-banner"><strong>Local preview</strong><span>Curated offline examples · AI and payments are disabled</span></div>', unsafe_allow_html=True)
elif settings.billing_mode == "test":
    st.markdown('<div class="mode-banner"><strong>Stripe sandbox</strong><span>Test subscriptions only · No real payments</span></div>', unsafe_allow_html=True)

starter_question = None
if not messages:
    hero(locked=locked)
if not messages and not locked:
    with st.container(key="starters"):
        prompts = [
            ("Work through a subnet", "Explain the network and broadcast addresses for 192.168.10.77/26.", "Find boundaries and usable hosts.", "subnet", "IP", "IP ADDRESSING"),
            ("Troubleshoot OSPF", "Why might OSPF neighbors get stuck in ExStart?", "Reason through a neighbor problem.", "ospf", "O", "TROUBLESHOOTING"),
            ("Compare routing decisions", "Explain longest prefix match versus administrative distance.", "Understand which route wins.", "routing", "R", "ROUTING LOGIC"),
            ("Practice a switching scenario", "Give me an original CCNA practice scenario about STP root bridge election, with an answer and explanation.", "Put VLAN and STP knowledge to work.", "switching", "S", "SCENARIO PRACTICE"),
        ]
        for row in range(2):
            columns = st.columns(2)
            for column, (title, prompt, subtitle, slug, symbol, category) in zip(columns, prompts[row * 2:row * 2 + 2]):
                with column:
                    with st.container(key="prompt-" + slug):
                        st.markdown(f'<div class="card-top"><span class="card-icon">{symbol}</span><span class="card-topic">{category}</span></div>', unsafe_allow_html=True)
                        if st.button(title, key="starter-" + title, type="tertiary", icon=":material/arrow_outward:", icon_position="right", width="stretch", disabled=disabled):
                            starter_question = prompt
                        st.caption(subtitle)
    if not used and not entitlement.active:
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
        details, action = st.columns([1.65, 1], gap="large")
        with details:
            st.markdown('<div class="gate-kicker">KEEP BUILDING YOUR UNDERSTANDING</div>', unsafe_allow_html=True)
            st.subheader("Continue with CCNA Tutor")
            st.write("You've used your free response. Unlock follow-up questions, fresh scenarios, and a study space that keeps your progress.")
            st.markdown('<div class="gate-features"><span>Step-by-step explanations</span><span>Original practice scenarios</span><span>Saved chats & references</span></div>', unsafe_allow_html=True)
        with action:
            st.markdown('<div class="gate-price">$9<span> / month</span></div>', unsafe_allow_html=True)
            checkout_button("main-checkout")
            st.caption(f"Up to {settings.daily_limit} prompts per day · Cancel anytime")
        if settings.preview:
            reset_name = "Restart local AI trial" if settings.local_test else "Restart local preview"
            st.caption(f"The subscription gate is shown for testing. To try another local prompt, use “{reset_name}” in the sidebar.")
        else:
            st.caption(f"Use {identity.email} at checkout, then return to this conversation.")
            refresh_payment("main-refresh")
    if st.session_state.get("paywall_seen") != identity.user_id:
        store.event("paywall_view", identity.user_id)
        st.session_state.paywall_seen = identity.user_id

notice = st.session_state.pop("chat_notice", None)
if notice:
    st.warning(notice)

placeholder = "Subscribe to continue the conversation" if locked else "Ask a CCNA question or describe a network problem…"
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
            tutor, index = model_services(str(store_dir / "chroma"), settings.ai_provider, settings.model,
                                          settings.embedding_model, settings.ollama_url, settings.embedding_profile,
                                          settings.gemini_key, settings.ollama_token)
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
    except BillingUnavailable as exc:
        st.session_state.chat_notice = str(exc)
    except GenerationError as exc:
        st.session_state.chat_notice = (str(exc) if settings.preview or settings.ai_provider == "gemini" else
                                       "The tutor could not finish this response. Please retry. Any partial response is saved.")
    except Exception:
        st.session_state.chat_notice = "The tutor is temporarily unavailable. Please try again."
    # Re-render from the ledger: saved history and paywall update together.
    if store.messages(active_conversation, identity.user_id, limit=1):
        st.session_state.conversation_id = active_conversation
    st.rerun()
