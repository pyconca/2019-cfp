from typing import Any, Dict

import pytest

from yakbak.settings import InvalidSettings, load_settings


def valid_settings_dict() -> Dict[str, Any]:
    return {
        "auth": {},
        "db": {
            "url": "sqlite://",
        },
        "flask": {
            "secret_key": "abcd",
        },
        "logging": {
            "level": "ERROR",
        },
        "smtp": {},
    }


def test_it_parses_settings() -> None:
    settings_dict = valid_settings_dict()
    settings = load_settings(settings_dict)

    # spot check a few things
    assert settings.db.url == "sqlite://"
    assert settings.logging.level == "ERROR"


def test_it_fails_with_extra_fields() -> None:
    settings_dict = valid_settings_dict()
    settings_dict["extra"] = {"foo": "bar"}

    with pytest.raises(InvalidSettings):
        load_settings(settings_dict)


def test_it_fails_with_missing_fields() -> None:
    settings_dict = valid_settings_dict()
    del settings_dict["db"]

    with pytest.raises(InvalidSettings):
        load_settings(settings_dict)


def test_it_sets_auth_summary_fields() -> None:
    settings_dict = valid_settings_dict()
    settings_dict["auth"].update(
        github_key_id="the-key-id",
        github_secret="the-secret",
    )
    settings_dict["auth"].pop("google_key_id", None)
    settings_dict["auth"].pop("google_secret", None)

    settings = load_settings(settings_dict)

    assert settings.auth.github
    assert not settings.auth.google
    assert not settings.auth.no_social_auth


def test_social_auth_methods() -> None:
    settings_dict = valid_settings_dict()
    settings_dict["auth"].update(
        github_key_id="the-key-id",
        github_secret="the-secret",
        email_magic_link=True,
    )
    settings_dict["auth"].pop("google_key_id", None)
    settings_dict["auth"].pop("google_secret", None)

    settings = load_settings(settings_dict)

    methods = settings.auth.auth_methods()
    assert len(methods) == 2

    # spot check
    assert methods[0].name == "email"
    assert methods[1].name == "github"
