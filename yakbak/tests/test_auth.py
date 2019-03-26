import mock
import pytest

from yakbak import auth


@pytest.mark.parametrize("length, expected", [
    (60, "1 minute"),
    (120, "2 minutes"),
    (3600, "1 hour"),
    (7200, "2 hours"),
    (86400, "1 day"),
    (172800, "2 days"),
    (31536000, "1 year"),
    (63072000, "2 years"),

    # test that it doesn't do "2 days, 4 hours, 10 minutes..."
    (187800, "2 days"),
])
def test_get_magic_link_token_expiry(length: int, expected: str) -> None:
    with mock.patch.object(auth, "current_app") as app:
        app.settings.auth.email_magic_link_expiry = length
        app.settings.auth.signing_key = "abcd"

        _, expiry = auth.get_magic_link_token_and_expiry("test@example.com")

    assert expiry == expected


def test_parse_magic_link_token() -> None:
    with mock.patch.object(auth, "current_app") as app:
        app.settings.auth.signing_key = "abcd"
        app.settings.auth.email_magic_link_expiry = 10  # seconds

        token, _ = auth.get_magic_link_token_and_expiry("test@example.com")
        email = auth.parse_magic_link_token(token)

        assert email == "test@example.com"


def test_parse_magic_link_token_is_none_for_garbled_tokens() -> None:
    with mock.patch.object(auth, "current_app") as app:
        app.settings.auth.signing_key = "abcd"
        app.settings.auth.email_magic_link_expiry = 10  # seconds

        token, _ = auth.get_magic_link_token_and_expiry("test@example.com")
        token = token[:-2]
        email = auth.parse_magic_link_token(token)

        assert email is None


def test_parse_magic_link_token_is_none_for_expired_tokens() -> None:
    with mock.patch.object(auth, "current_app") as app:
        app.settings.auth.signing_key = "abcd"
        app.settings.auth.email_magic_link_expiry = -1  # surprisingly this works

        token, _ = auth.get_magic_link_token_and_expiry("test@example.com")
        email = auth.parse_magic_link_token(token)

        assert email is None
