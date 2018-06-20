from typing import Any, Dict, Sequence

from attr import attrib, attrs
from attr.validators import instance_of
import pytest

from yakbak.settings import InvalidSettings, list_of, load_settings


def valid_settings_dict() -> Dict[str, Any]:
    return {
        "auth": {},
        "cfp": {
            "talk_lengths": [30, 45],
        },
        "db": {
            "url": "sqlite://",
        },
        "flask": {
            "secret_key": "abcd",
        },
        "logging": {
            "level": "ERROR",
        },
        "site": {
            "title": "A PyConference",
            "conference": "PyConference 2018",
            "copyright": "Copyright (C) 2018 PyConference Organizers",
        },
        "smtp": {},
    }


def test_list_of_validator() -> None:
    @attrs
    class Thing:
        field: Sequence[int] = attrib(validator=list_of(instance_of(int)))

    Thing(field=[1, 2, 3])  # ok
    Thing(field=(1, 2, 3))  # ok

    with pytest.raises(TypeError):
        Thing(field=["foo"])  # type: ignore
    with pytest.raises(TypeError):
        Thing(field=1)        # type: ignore


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
