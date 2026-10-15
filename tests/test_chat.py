import pytest
from tutor.billing import BillingUnavailable
from tutor.chat import stream_reply
from tutor.engine import GenerationError
from tutor.store import AccessDenied, UsageStore


def test_paid_followup_and_new_chat_cannot_reset_free_trial(tmp_path):
    store = UsageStore(tmp_path / "db", cooldown_seconds=0)
    calls = []
    def prepare():
        calls.append("generated")
        return iter(["A useful ", "answer."]), [{"id": "s1-c0"}]
    def ask(conversation, active=False):
        return "".join(stream_reply(store, "u", conversation, "A question?", lambda: active, prepare))
    assert ask("first") == "A useful answer."
    for conversation in ("first", "new"):
        with pytest.raises(AccessDenied, match="Subscribe"):
            ask(conversation)
    assert len(calls) == 1, "Gate before invoking the model or embeddings"
    assert ask("first", active=True) == "A useful answer."
    messages = UsageStore(tmp_path / "db").messages("first", "u")
    assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]
    assert messages[1]["references"] == [{"id": "s1-c0"}]
    with pytest.raises(AccessDenied):
        ask("first")  # cancellation stops the next request
    assert store.messages("first", "another-user") == []
    assert store.conversations("another-user") == []


@pytest.mark.parametrize("failure", ["empty", "prepare", "stream"])
def test_failure_before_text_releases_trial_and_allows_retry(tmp_path, failure):
    store = UsageStore(tmp_path / "db", cooldown_seconds=0)
    def broken_stream():
        raise GenerationError("Model unavailable")
        yield
    def prepare():
        if failure == "prepare":
            raise GenerationError("Reference search unavailable")
        return iter(["  "]) if failure == "empty" else broken_stream(), []
    with pytest.raises(GenerationError):
        list(stream_reply(store, "u", "chat", "Question", lambda: False, prepare))
    assert not store.trial_used("u")
    assert not store.messages("chat", "u")
    assert not store.conversations("u")
    assert "".join(stream_reply(store, "u", "chat", "Retry", lambda: False,
                                lambda: (iter(["Success"]), []))) == "Success"


def test_partial_output_is_saved_and_consumes_trial(tmp_path):
    store = UsageStore(tmp_path / "db", cooldown_seconds=0)
    def interrupted():
        yield "The response so far."
        raise GenerationError("Interrupted")
    with pytest.raises(GenerationError):
        list(stream_reply(store, "u", "chat", "Question", lambda: False, lambda: (interrupted(), [])))
    assert store.trial_used("u")
    saved = store.messages("chat", "u")[1]
    assert saved["content"] == "The response so far."
    assert saved["interrupted"]
    with pytest.raises(AccessDenied):
        store.reserve("u", False, "chat")


def test_billing_failure_cannot_reach_generation(tmp_path):
    store = UsageStore(tmp_path / "db", cooldown_seconds=0)
    def check():
        raise BillingUnavailable("Cannot verify subscription")
    def prepare():
        pytest.fail("Must not call a model when billing verification fails")
    with pytest.raises(BillingUnavailable):
        list(stream_reply(store, "u", "chat", "Question", check, prepare))
    assert not store.trial_used("u")


def test_atomic_chat_save_and_ownership(tmp_path):
    store = UsageStore(tmp_path / "db", cooldown_seconds=0)
    own = store.reserve("owner", False, "chat")
    store.complete_chat(own, "owner", "conversation", "My question", "My answer", [])
    other = store.reserve("other", False, "chat")
    with pytest.raises(AccessDenied):
        store.complete_chat(other, "other", "conversation", "Injected", "Other answer", [])
    assert not store.trial_used("other")
    assert len(store.messages("conversation", "owner")) == 2
    assert store.messages("conversation", "other") == []
    with pytest.raises(AccessDenied):
        store.complete_chat(own, "owner", "conversation", "Duplicate", "Duplicate", [])
    assert len(store.messages("conversation", "owner")) == 2
    # A rejected save rolled back, so the other account can still finish its own trial.
    store.complete_chat(other, "other", "own-conversation", "Own question", "Own answer", [])
    assert store.trial_used("other")
