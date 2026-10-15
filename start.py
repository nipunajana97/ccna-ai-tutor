"""Render entry point: construct Streamlit OIDC secrets from server env, then exec."""
import os
from pathlib import Path
import sys
from dotenv import load_dotenv
import tomli_w

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def configure_auth():
    if os.getenv("DEMO_MODE", "false").lower() == "true":
        return
    required = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "AUTH_COOKIE_SECRET"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise ValueError("Missing authentication settings: " + ", ".join(missing))
    if len(os.environ["AUTH_COOKIE_SECRET"]) < 32:
        raise ValueError("AUTH_COOKIE_SECRET must contain at least 32 random characters.")
    app_url = os.getenv("APP_URL") or os.getenv("RENDER_EXTERNAL_URL") or "http://localhost:8501"
    os.environ["APP_URL"] = app_url.rstrip("/")
    auth = {"auth": {
        "redirect_uri": app_url.rstrip("/") + "/oauth2callback",
        "cookie_secret": os.environ["AUTH_COOKIE_SECRET"],
        "google": {"client_id": os.environ["GOOGLE_CLIENT_ID"],
                   "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
                   "server_metadata_url": "https://accounts.google.com/.well-known/openid-configuration"}
    }}
    target = ROOT / ".streamlit/secrets.toml"
    target.parent.mkdir(exist_ok=True)
    with os.fdopen(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as handle:
        os.chmod(target, 0o600)
        handle.write(tomli_w.dumps(auth))


if __name__ == "__main__":
    try:
        configure_auth()
        port = int(os.getenv("PORT", "8501"))
        if not 1 <= port <= 65535:
            raise ValueError("Invalid PORT")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    os.chdir(ROOT)
    os.execv(sys.executable, [sys.executable, "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", f"--server.port={port}", "--server.headless=true"])
