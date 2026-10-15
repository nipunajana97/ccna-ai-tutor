from dataclasses import dataclass
import hashlib
import time


class IdentityError(ValueError):
    pass


@dataclass(frozen=True)
class Identity:
    user_id: str
    email: str


def verified_identity(claims, now=None):
    """Only Google-issued, verified identities can spend a trial or claim a payment."""
    issuer = claims.get("iss")
    subject = claims.get("sub")
    email = claims.get("email", "")
    if issuer not in {"https://accounts.google.com", "accounts.google.com"}:
        raise IdentityError("Sign in with a verified Google account.")
    if not subject or not isinstance(email, str) or "@" not in email or len(email) > 254:
        raise IdentityError("Google did not return a valid account identity.")
    if claims.get("email_verified") is not True:
        raise IdentityError("Your Google email address must be verified.")
    try:
        expiry = float(claims["exp"])
    except (KeyError, ValueError, TypeError) as exc:
        raise IdentityError("Please sign out and sign in again.") from exc
    if expiry <= (time.time() if now is None else now):
        raise IdentityError("Your sign-in has expired. Please sign out and sign in again.")
    # Normalize the issuer spelling so the same Google subject never gets two trials.
    user_id = hashlib.sha256(f"https://accounts.google.com|{subject}".encode()).hexdigest()
    return Identity(user_id=user_id, email=email.strip().lower())
