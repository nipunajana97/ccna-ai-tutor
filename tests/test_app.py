from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def by_label(elements, label):
    return next(element for element in elements if element.label == label)


def demo(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.delenv("RENDER", raising=False)
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()


def test_chat_first_prompt_history_and_durable_paywall(tmp_path, monkeypatch):
    app = demo(tmp_path, monkeypatch)
    assert not app.exception
    assert not app.get("help_info"), "Internal Streamlit objects must not appear in the UI"
    assert not app.chat_input[0].disabled
    app.chat_input[0].set_value("Explain 192.168.10.77/26").run()
    assert not app.exception
    assert len(app.chat_message) == 2
    assert "192.168.10.64/26" in app.chat_message[1].markdown[0].value
    assert app.chat_input[0].disabled
    assert by_label(app.button, "Subscribe · $9/month").disabled
    assert any("Continue with CCNA Tutor" in heading.value for heading in app.subheader)
    assert not app.get("help_info")

    # A new browser session restores the conversation and the trial ledger.
    fresh = demo(tmp_path, monkeypatch)
    assert not fresh.exception
    assert len(fresh.chat_message) == 2
    assert fresh.chat_input[0].disabled
    by_label(fresh.button, "New chat").click().run()
    assert not fresh.chat_message
    assert fresh.chat_input[0].disabled
    assert by_label(fresh.button, "Work through a subnet").disabled

    # The saved conversation remains accessible from the sidebar.
    by_label(fresh.button, "Explain 192.168.10.77/26").click().run()
    assert len(fresh.chat_message) == 2
    assert fresh.chat_input[0].disabled


def test_starter_sends_prompt_and_local_reset_only_changes_preview_identity(tmp_path, monkeypatch):
    app = demo(tmp_path, monkeypatch)
    by_label(app.button, "Troubleshoot OSPF").click().run()
    assert not app.exception
    assert len(app.chat_message) == 2
    assert "MTU" in app.chat_message[1].markdown[0].value
    assert app.chat_input[0].disabled
    by_label(app.button, "Restart local preview").click().run()
    assert not app.exception
    assert not app.chat_input[0].disabled
    assert not app.chat_message
    # Reset does not erase the durable default account's consumed trial/history.
    fresh = demo(tmp_path, monkeypatch)
    assert fresh.chat_input[0].disabled
    assert len(fresh.chat_message) == 2


def test_integrated_chat_subscription_unlock_context_and_cancellation(tmp_path, monkeypatch):
    """Real UI orchestration, with identity/billing/model boundaries stubbed; no external calls."""
    from types import SimpleNamespace
    import streamlit as st
    import tutor.billing
    import tutor.engine
    import tutor.knowledge
    from tutor.billing import Entitlement

    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", "test-placeholder")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_placeholder")
    monkeypatch.setenv("STRIPE_PRICE_ID", "price_" + tmp_path.name)
    monkeypatch.setenv("REQUEST_COOLDOWN_SECONDS", "0")
    monkeypatch.delenv("RENDER", raising=False)
    email = tmp_path.name + "@example.invalid"
    monkeypatch.setattr(st, "user", SimpleNamespace(is_logged_in=True, to_dict=lambda: {
        "iss": "https://accounts.google.com", "sub": tmp_path.name,
        "email": email, "email_verified": True, "exp": 9999999999,
    }))
    state = {"paid": False, "calls": [], "checks": 0}

    class Billing:
        def __init__(self, *args):
            pass
        def entitlement(self, verified_email):
            assert verified_email == email
            state["checks"] += 1
            return Entitlement(state["paid"], "cus_test" if state["paid"] else None)

    class Model:
        def __init__(self, *args):
            pass
        def embed(self, *args):
            pytest.fail("The fake index must not make external embedding calls")
        def stream_answer(self, question, chunks, history=None):
            state["calls"].append((question, history))
            yield "An answer with context."

    class Index:
        def __init__(self, *args):
            pass
        def retrieve(self, question):
            return []

    monkeypatch.setattr(tutor.billing, "StripeBilling", Billing)
    monkeypatch.setattr(tutor.engine, "GeminiTutor", Model)
    monkeypatch.setattr(tutor.knowledge, "KnowledgeIndex", Index)

    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20)
    app.secrets["auth"] = {"configured": True}
    app.run()
    assert not app.exception
    assert not app.chat_input[0].disabled
    app.chat_input[0].set_value("What is a subnet?").run()
    assert not app.exception
    assert app.chat_input[0].disabled
    assert len(state["calls"]) == 1

    state["paid"] = True
    by_label(app.button, "I've paid · Refresh access").click().run()
    assert not app.exception
    assert not app.chat_input[0].disabled
    app.chat_input[0].set_value("Explain that in more detail.").run()
    assert not app.exception
    assert len(state["calls"]) == 2
    assert [m["role"] for m in state["calls"][1][1]] == ["user", "assistant"]
    assert state["calls"][1][1][0]["content"] == "What is a subnet?"
    assert len(app.chat_message) == 4

    # The sidebar cache still shows paid, but cancellation must block before any model call.
    state["paid"] = False
    app.chat_input[0].set_value("One more question").run()
    assert not app.exception
    assert app.chat_input[0].disabled
    assert len(state["calls"]) == 2
    assert len(app.chat_message) == 4
    assert state["checks"] >= 5
