from hashlib import sha256
from typing import Optional, Tuple

from flask import current_app
from flask_login import LoginManager
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from yakbak.models import User

login_manager = LoginManager()
login_manager.login_view = "views.login"


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    try:
        return User.query.get(int(user_id))
    except (TypeError, ValueError):
        return None


def get_magic_link_serializer() -> URLSafeTimedSerializer:
    # NB: changing this will probably invalidate any magic links in the wild
    return URLSafeTimedSerializer(
        secret_key=current_app.settings.auth.signing_key,
        salt="email-magic-link",
        signer_kwargs=dict(digest_method=sha256),
    )


def get_magic_link_token_and_expiry(email: str) -> Tuple[str, str]:
    authsettings = current_app.settings.auth
    exp = authsettings.email_magic_link_expiry
    years, rem = divmod(exp, 365 * 24 * 60 * 60)
    days, rem = divmod(rem, 24 * 60 * 60)
    hours, rem = divmod(rem, 60 * 60)
    minutes, rem = divmod(rem, 60)
    if years:
        plural = "s" if years > 1 else ""
        expiry = f"{years} year{plural}"
    elif days:
        plural = "s" if days > 1 else ""
        expiry = f"{days} day{plural}"
    elif hours:
        plural = "s" if hours > 1 else ""
        expiry = f"{hours} hour{plural}"
    elif minutes:
        plural = "s" if minutes > 1 else ""
        expiry = f"{minutes} minute{plural}"
    else:
        plural = "s" if rem > 1 else ""
        expiry = f"{rem} second{plural}"

    serializer = get_magic_link_serializer()
    token = serializer.dumps(email)
    if isinstance(token, bytes):
        token = token.decode("us-ascii")

    return token, expiry


def parse_magic_link_token(token: str) -> Optional[str]:
    """
    Try to validate the signature and return the email from a email
    magic link ``token``.

    Returns the email address contained in the token if the signature is
    valid, the message hasn't been tampered with, and the signature
    hasn't expired. Returns ``None`` in all other cases.

    """
    serializer = get_magic_link_serializer()
    expiry = current_app.settings.auth.email_magic_link_expiry
    try:
        email = serializer.loads(token, max_age=expiry)
        return email
    except (BadSignature, SignatureExpired):
        return None
