from dataclasses import dataclass
from pathlib import Path
import os

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

    @classmethod
    def from_env(cls):
        return cls(
            data_dir=Path(os.getenv("DATA_DIR", str(ROOT / "data"))),
            gemini_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            embedding_model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
            stripe_key=os.getenv("STRIPE_SECRET_KEY", ""),
            stripe_price_id=os.getenv("STRIPE_PRICE_ID", "price_1UQdZaCvG4xAhKW62tQteiuU"),
            payment_link=os.getenv("STRIPE_PAYMENT_LINK", "https://buy.stripe.com/test_aFa7sKfRceuj6BsfQk6wE00"),
            billing_mode=os.getenv("BILLING_MODE", "test"),
            app_url=os.getenv("APP_URL", "http://localhost:8501").rstrip("/"),
            demo=os.getenv("DEMO_MODE", "false").lower() == "true",
            daily_limit=int(os.getenv("DAILY_REQUEST_LIMIT", "100")),
            global_daily_limit=int(os.getenv("GLOBAL_DAILY_REQUEST_LIMIT", "500")),
            cooldown_seconds=int(os.getenv("REQUEST_COOLDOWN_SECONDS", "10")),
        )

    def errors(self):
        if self.demo:
            if os.getenv("RENDER"):
                return ["Demo mode is local only. Disable DEMO_MODE before deployment."]
            return []
        errors = []
        for name, value in [("GEMINI_API_KEY", self.gemini_key), ("STRIPE_SECRET_KEY", self.stripe_key),
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
