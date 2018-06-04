from operator import itemgetter
from typing import Any, Callable, Dict, List, Optional, Tuple
import os.path

from attr import attrib, attrs, fields
from attr.validators import instance_of, optional
import toml


class InvalidSettings(Exception):
    pass


ValidationFunc = Callable[[Any, Any, Any], None]


def list_of(validator: ValidationFunc) -> ValidationFunc:
    def list_validator(instance: Any, attribute: Any, value: Any) -> None:
        if not isinstance(value, (list, tuple)):
            raise TypeError("value must be a list or tuple")
        for element in value:
            validator(instance, attribute, element)

    return list_validator


@attrs(frozen=True)
class CfpSettings:
    talk_lengths: List[int] = attrib(validator=list_of(instance_of(int)))


@attrs(frozen=True)
class DbSettings:
    uri: str = attrib(validator=instance_of(str))


@attrs(frozen=True)
class FlaskSettings:
    secret_key: str = attrib(validator=instance_of(str))


@attrs(frozen=True)
class LoggingSettings:
    level: str = attrib(validator=instance_of(str))


@attrs(frozen=True)
class SiteSettings:
    title: str = attrib(validator=instance_of(str))


@attrs(frozen=True)
class SocialAuthSettings:
    github_key: Optional[str] = attrib(validator=optional(instance_of(str)))
    github_secret: Optional[str] = attrib(validator=optional(instance_of(str)))

    google_key: Optional[str] = attrib(validator=optional(instance_of(str)))
    google_secret: Optional[str] = attrib(validator=optional(instance_of(str)))

    # these are initialized in core.py
    github: bool = attrib()
    google: bool = attrib()
    none: bool = attrib()

    @classmethod
    def social_auth_methods(cls) -> List[Tuple[str, str]]:
        """
        Get a list of social auth methods as (``name``, ``display_name``) tuples.

        The ``name`` is the base for the keys used in the TOML file and in this
        object. The ``display_name`` is the properly-capitalized name for use in
        templates and so on.

        """
        # any which are not .title()
        special_display_names = {
            "github": "GitHub",
        }
        methods = []
        for field in fields(cls):
            if not field.name.endswith("_key"):
                continue
            name = field.name[:-4]
            display_name = special_display_names.get(name, name.title())
            methods.append((name, display_name))
        methods.sort(key=itemgetter(1))
        return methods


@attrs(frozen=True)
class Settings:
    cfp: CfpSettings = attrib()
    db: DbSettings = attrib()
    flask: FlaskSettings = attrib()
    logging: LoggingSettings = attrib()
    site: SiteSettings = attrib()
    social_auth: SocialAuthSettings = attrib()


def find_settings_file() -> str:
    """
    Returns the canonical location of ``yakbak.toml`` in the project root.

    """
    here = os.path.dirname(__file__)
    toml = os.path.join(here, "..", "yakbak.toml")
    return os.path.abspath(toml)


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

        # For each social auth method, set a setting named eg "github"
        # if that method is configured; if none are configured, set
        # a field "none" to True
        if section == "social_auth":
            social_methods = set([
                f.name[:-4]
                for f in fields(SocialAuthSettings)
                if f.name.endswith("_key")
            ])

            data["none"] = True
            for social_method in social_methods:
                key_field = "{}_key".format(social_method)
                secret_field = "{}_secret".format(social_method)
                data.setdefault(key_field, None)
                data.setdefault(secret_field, None)
                data[social_method] = data.get(key_field) and data.get(secret_field)
                if data[social_method]:
                    data["none"] = False

        top_level[section] = field.type(**data)

    if settings_dict:
        raise InvalidSettings(
            f"settings has unexpected sections: {settings_dict.keys()}")

    return Settings(**top_level)  # type: ignore
