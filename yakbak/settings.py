from operator import attrgetter
from typing import Any, Callable, Dict, List, Optional
import os.path

from attr import attrib, attrs, fields
from attr.validators import instance_of, optional
from flask import url_for
import toml


ValidationFunc = Callable[[Any, Any, Any], None]


class InvalidSettings(Exception):
    pass


@attrs
class AuthMethod:
    name: str = attrib()
    display_name: str = attrib()
    view: str = attrib()
    view_kwargs: Dict[str, Any] = attrib()

    def url(self) -> str:
        return url_for(self.view, **self.view_kwargs)


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
    templates_auto_reload: bool = attrib(
        validator=optional(instance_of(bool)), default=False)


@attrs(frozen=True)
class LoggingSettings:
    level: str = attrib(validator=instance_of(str))


@attrs(frozen=True)
class SiteSettings:
    title: str = attrib(validator=instance_of(str))
    conference: str = attrib(validator=instance_of(str))


@attrs(frozen=True)
class AuthSettings:
    github_key_id: Optional[str] = attrib(validator=optional(instance_of(str)))
    github_secret: Optional[str] = attrib(validator=optional(instance_of(str)))

    google_key_id: Optional[str] = attrib(validator=optional(instance_of(str)))
    google_secret: Optional[str] = attrib(validator=optional(instance_of(str)))

    email_magic_link: Optional[bool] = attrib(validator=optional(instance_of(bool)))
    email_magic_link_expiry: Optional[int] = attrib(validator=optional(instance_of(int)))

    signing_key: Optional[str] = attrib(validator=instance_of(str))

    # these are initialized in core.py
    github: bool = attrib()
    google: bool = attrib()
    no_social_auth: bool = attrib()

    def auth_methods(self) -> List[AuthMethod]:
        """
        Get a list of social auth methods.

        """
        # any which are not name.title()
        display_names = {
            "github": "GitHub",
        }
        # any which are not name
        backend_names = {
            "google": "google-oauth2",
        }
        # any which are not social-auth
        view_and_kwargs = {
            "email": ("views.magic_link_begin", {}),
        }

        methods = []
        for field in fields(AuthSettings):
            if not field.name.endswith("_key_id"):
                continue
            name = field.name[:-7]
            if not getattr(self, name, False):
                continue
            display_name = display_names.get(name, name.title())
            backend_name = backend_names.get(name, name)
            default_view_and_kwargs = ("social.auth", {"backend": backend_name})
            view, kwargs = view_and_kwargs.get(name, default_view_and_kwargs)
            methods.append(AuthMethod(name, display_name, view, kwargs))

        methods.sort(key=attrgetter("name"))
        if self.email_magic_link:
            email = AuthMethod("email", "Email Magic Link", "views.email_magic_link", {})
            methods.insert(0, email)
        return methods


@attrs(frozen=True)
class SMTPSettings:
    host: str = attrib()
    port: int = attrib()
    username: str = attrib()
    password: str = attrib()
    sender: str = attrib()


@attrs(frozen=True)
class Settings:
    auth: AuthSettings = attrib()
    cfp: CfpSettings = attrib()
    db: DbSettings = attrib()
    flask: FlaskSettings = attrib()
    logging: LoggingSettings = attrib()
    site: SiteSettings = attrib()
    smtp: SMTPSettings = attrib()


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
        # a field "no_social_auth" to True
        if section == "auth":
            social_methods = set([
                f.name[:-7]
                for f in fields(AuthSettings)
                if f.name.endswith("_key_id")
            ])

            data["no_social_auth"] = True
            for social_method in social_methods:
                key_id_field = "{}_key_id".format(social_method)
                secret_field = "{}_secret".format(social_method)
                data.setdefault(key_id_field, None)
                data.setdefault(secret_field, None)
                data[social_method] = data.get(key_id_field) and data.get(secret_field)
                if data[social_method]:
                    data["no_social_auth"] = False

            data.setdefault("email_magic_link", False)

        top_level[section] = field.type(**data)

    if settings_dict:
        raise InvalidSettings(
            f"settings has unexpected sections: {settings_dict.keys()}")

    return Settings(**top_level)  # type: ignore
