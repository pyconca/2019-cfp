from typing import Any, Dict

import pytest

from yakbak.settings import InvalidSettings, load_settings


def valid_settings_dict() -> Dict[str, Any]:
    return {
        "db": {"uri": "sqlite://:memory:"},
        "logging": {"level": "ERROR"},
    }


def test_it_fails_with_extra_fields():
    settings_dict = valid_settings_dict()
    settings_dict["extra"] = {"foo": "bar"}

    with pytest.raises(InvalidSettings):
        load_settings(settings_dict)


def test_it_fails_with_missing_fields():
    settings_dict = valid_settings_dict()
    del settings_dict["db"]

    with pytest.raises(InvalidSettings):
        load_settings(settings_dict)
