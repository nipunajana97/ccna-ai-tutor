from dataclasses import replace
import pytest
from tutor.config import Settings


@pytest.fixture
def local_settings(monkeypatch, tmp_path):
    for key, value in {
        "DATA_DIR": str(tmp_path), "AI_PROVIDER": "ollama", "DEMO_MODE": "false", "LOCAL_AI_TEST": "true",
        "APP_URL": "http://localhost:8501", "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
        "OLLAMA_MODEL": "qwen3:1.7b", "OLLAMA_EMBEDDING_MODEL": "nomic-embed-text:v1.5",
        "GEMINI_API_KEY": "", "STRIPE_SECRET_KEY": "",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("RENDER", raising=False)
    return Settings.from_env()


def test_local_ollama_test_needs_no_google_or_stripe_keys(local_settings):
    assert local_settings.preview
    assert not local_settings.errors()
    assert local_settings.ai_provider == "ollama"
    assert local_settings.model == "qwen3:1.7b"


def test_preview_cannot_run_on_render(local_settings, monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    assert any("local only" in error for error in local_settings.errors())


@pytest.mark.parametrize("change", [
    {"ollama_url": "https://remote.example"}, {"app_url": "https://public.example"},
    {"ai_provider": "gemini"}, {"demo": True}, {"ollama_model": "example-cloud"},
])
def test_local_test_rejects_remote_or_conflicting_configuration(local_settings, change):
    assert replace(local_settings, **change).errors()


def test_production_still_requires_billing(local_settings):
    production = replace(local_settings, local_test=False)
    assert any("STRIPE_SECRET_KEY" in error for error in production.errors())
    assert not any("GEMINI_API_KEY" in error for error in production.errors())


def test_remote_ollama_requires_authenticated_https_proxy(local_settings):
    settings = replace(local_settings, local_test=False, ollama_url="http://host.example")
    assert any("HTTPS" in error for error in settings.errors())
    secure = replace(settings, ollama_url="https://host.example", ollama_token="test-proxy-token")
    assert not any("remote Ollama" in error for error in secure.errors())


def test_local_launch_overrides_old_demo_flag_and_binds_loopback(local_settings, monkeypatch):
    import start
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("PORT", "8517")
    executed = []
    monkeypatch.setattr(start.os, "execv", lambda executable, args: executed.append(args))
    start.main(["--local-ai"])
    settings = Settings.from_env()
    assert settings.local_test and not settings.demo
    assert "--server.address=127.0.0.1" in executed[0]
    assert "--server.port=8517" in executed[0]


def test_production_launch_cannot_silently_skip_google_auth(local_settings, monkeypatch):
    import start
    monkeypatch.setenv("LOCAL_AI_TEST", "false")
    for key in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "AUTH_COOKIE_SECRET"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValueError, match="authentication settings"):
        start.configure_auth(Settings.from_env())
