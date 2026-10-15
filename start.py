"""Render entry point: construct Streamlit OIDC secrets from server env, then exec."""
import os
import argparse
from pathlib import Path
import sys
from dotenv import load_dotenv
import tomli_w
from tutor.config import Settings

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def configure_auth(settings=None):
    settings = settings or Settings.from_env()
    if settings.preview:
        errors = settings.errors()
        if errors:
            raise ValueError("\n".join(errors))
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


def main(argv=None):
    parser = argparse.ArgumentParser(description="Start the CCNA tutor")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--local-ai", action="store_true", help="Real Ollama answers on localhost; no login or payment calls")
    modes.add_argument("--demo", action="store_true", help="Offline interface preview")
    args = parser.parse_args(argv)
    if args.local_ai:
        os.environ.update(LOCAL_AI_TEST="true", DEMO_MODE="false", AI_PROVIDER="ollama")
    elif args.demo:
        os.environ.update(DEMO_MODE="true", LOCAL_AI_TEST="false")
    try:
        settings = Settings.from_env()
        configure_auth(settings)
        port = int(os.getenv("PORT", "8501"))
        if not 1 <= port <= 65535:
            raise ValueError("Invalid PORT")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    os.chdir(ROOT)
    address = "127.0.0.1" if settings.preview else "0.0.0.0"
    os.execv(sys.executable, [sys.executable, "-m", "streamlit", "run", "app.py", f"--server.address={address}", f"--server.port={port}", "--server.headless=true"])


if __name__ == "__main__":
    main()
