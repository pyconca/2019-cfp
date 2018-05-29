from typing import Any, Dict

from attr import attrib, attrs, fields
from attr.validators import instance_of
import toml


class InvalidSettings(Exception):
    pass


@attrs(frozen=True)
class DbSettings:
    uri: str = attrib(validator=[instance_of(str)])


@attrs(frozen=True)
class LoggingSettings:
    level: str = attrib(validator=[instance_of(str)])


@attrs(frozen=True)
class Settings:
    db: DbSettings = attrib()
    logging: LoggingSettings = attrib()


def load_settings_file(settings_path: str) -> Settings:
    with open(settings_path) as fp:
        return load_settings(toml.load(fp))


def load_settings(settings_dict: Dict[str, Any]) -> Settings:
    top_level = {}
    for field in fields(Settings):
        section = field.name
        data = settings_dict.pop(section, None)
        if data is None:
            raise InvalidSettings(f"settings missing section: {section}")
        top_level[section] = field.type(**data)

    if settings_dict:
        raise InvalidSettings(
            f"settings has unexpected sections: {settings_dict.keys()}")

    return Settings(**top_level)
