from dataclasses import dataclass
from pathlib import Path
import os
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    gemini_key: str
    gemini_model: str
    embedding_model: str
    stripe_key: str
    stripe_price_id: str
    payment_link: str
    billing_mode: str
    app_url: str
    demo: bool = False
    daily_limit: int = 100
    global_daily_limit: int = 500
    cooldown_seconds: int = 10
    ai_provider: str = "ollama"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:1.7b"
    ollama_token: str = ""
    local_test: bool = False

    @property
    def preview(self):
        return self.demo or self.local_test

    @property
    def model(self):
        return self.ollama_model if self.ai_provider == "ollama" else self.gemini_model

    @property
    def embedding_profile(self):
        return "ollama|768|nomic-prefix-v1" if self.ai_provider == "ollama" else "768|v1"

    @classmethod
    def from_env(cls):
        provider = os.getenv("AI_PROVIDER", "ollama").lower()
        return cls(
            data_dir=Path(os.getenv("DATA_DIR", str(ROOT / "data"))),
            gemini_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            embedding_model=(os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:v1.5") if provider == "ollama"
                             else os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")),
            stripe_key=os.getenv("STRIPE_SECRET_KEY", ""),
            stripe_price_id=os.getenv("STRIPE_PRICE_ID", "price_1UQdZaCvG4xAhKW62tQteiuU"),
            payment_link=os.getenv("STRIPE_PAYMENT_LINK", "https://buy.stripe.com/test_aFa7sKfRceuj6BsfQk6wE00"),
            billing_mode=os.getenv("BILLING_MODE", "test"),
            app_url=os.getenv("APP_URL", "http://localhost:8501").rstrip("/"),
            demo=os.getenv("DEMO_MODE", "false").lower() == "true",
            daily_limit=int(os.getenv("DAILY_REQUEST_LIMIT", "100")),
            global_daily_limit=int(os.getenv("GLOBAL_DAILY_REQUEST_LIMIT", "500")),
            cooldown_seconds=int(os.getenv("REQUEST_COOLDOWN_SECONDS", "10")),
            ai_provider=provider,
            ollama_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen3:1.7b"),
            ollama_token=os.getenv("OLLAMA_AUTH_TOKEN", ""),
            local_test=os.getenv("LOCAL_AI_TEST", "false").lower() == "true",
        )

    def errors(self):
        errors = []
        if self.preview and os.getenv("RENDER"):
            errors.append("Preview modes are local only. Disable DEMO_MODE and LOCAL_AI_TEST before deployment.")
        if self.demo and self.local_test:
            errors.append("Choose either DEMO_MODE or LOCAL_AI_TEST, not both.")
        if self.local_test and urlsplit(self.app_url).hostname not in {"localhost", "127.0.0.1", "::1"}:
            errors.append("LOCAL_AI_TEST requires a localhost APP_URL.")
        if self.demo:
            return errors
        if self.ai_provider not in {"ollama", "gemini"}:
            errors.append("AI_PROVIDER must be ollama or gemini.")
        if self.ai_provider == "ollama":
            url = urlsplit(self.ollama_url)
            loopback = url.hostname in {"localhost", "127.0.0.1", "::1"}
            if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}:
                errors.append("OLLAMA_BASE_URL must be an HTTP(S) server origin, without credentials, path, or query.")
            if self.local_test and not loopback:
                errors.append("LOCAL_AI_TEST requires Ollama on localhost.")
            if not loopback and (url.scheme != "https" or not self.ollama_token):
                errors.append("A remote Ollama server requires HTTPS and OLLAMA_AUTH_TOKEN for its authenticated proxy.")
            if os.getenv("RENDER") and loopback:
                errors.append("Render needs a reachable, separately hosted Ollama server; localhost refers to the web service itself.")
            if any("cloud" in name.lower() for name in (self.ollama_model, self.embedding_model)):
                errors.append("Use downloaded local model tags, not cloud models.")
            if not self.embedding_model.startswith("nomic-embed-text"):
                errors.append("This local embedding adapter supports nomic-embed-text with 768 dimensions.")
        elif not self.gemini_key:
            errors.append("Missing GEMINI_API_KEY.")
        if self.local_test:
            if self.ai_provider != "ollama":
                errors.append("LOCAL_AI_TEST uses Ollama only.")
            return errors
        for name, value in [("STRIPE_SECRET_KEY", self.stripe_key),
                            ("STRIPE_PRICE_ID", self.stripe_price_id), ("STRIPE_PAYMENT_LINK", self.payment_link)]:
            if not value:
                errors.append(f"Missing {name}.")
        if self.billing_mode not in {"test", "live"}:
            errors.append("BILLING_MODE must be test or live.")
        prefix = "sk_test_" if self.billing_mode == "test" else "sk_live_"
        if self.stripe_key and not self.stripe_key.startswith(prefix):
            errors.append("Stripe key does not match BILLING_MODE.")
        if not self.payment_link.startswith("https://buy.stripe.com/"):
            errors.append("Use a Stripe-hosted payment link.")
        elif ("/test_" in self.payment_link) != (self.billing_mode == "test"):
            errors.append("Payment link does not match BILLING_MODE.")
        if min(self.daily_limit, self.global_daily_limit) < 1 or self.cooldown_seconds < 0:
            errors.append("Usage limits must be positive and cooldown nonnegative.")
        if os.getenv("RENDER") and not self.app_url.startswith("https://"):
            errors.append("APP_URL must be the HTTPS Render URL.")
        if os.getenv("RENDER") and not str(self.data_dir).startswith("/var/data/"):
            errors.append("Attach a persistent disk at /var/data and set DATA_DIR=/var/data/ccna.")
        return errors
