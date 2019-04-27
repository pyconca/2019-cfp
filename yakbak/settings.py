from operator import attrgetter
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar
import os
import os.path
import os.getenv

from dotenv import load_dotenv
from attr import attrib, attrs, fields
from attr.validators import instance_of, optional
from flask import url_for
import toml

load_dotenv()

ValidationFunc = Callable[[Any, Any, Any], None]


class InvalidSettings(Exception):
    pass


T = TypeVar("T", bound="Section")


class Section:
    @classmethod
    def populate_from(
        cls: Type[T], toml: Dict[str, Any], environment: Dict[str, str]
    ) -> T:
        """
        Populate the section using settings the TOML and environment.

        Settings present in the environment take precedence over settings
        set only in the toml; and required fields must be set in at least
        one of the locations.

        """
        section_name = cls.__name__
        if section_name.endswith("Settings"):
            section_name = section_name[: -len("Settings")]

        kwargs = {}
        for field in fields(cls):
            env_var = f"YAK_BAK_{section_name}_{field.name}".upper()
            if env_var in environment:
                value = environment[env_var]
                if "%(" in value and ")s" in value:
                    value = value % environment
                kwargs[field.name] = value
            elif field.name in toml:
                kwargs[field.name] = toml[field.name]

        return cls(**kwargs)  # type: ignore  # too many args for type Section


@attrs
class AuthMethod(Section):
    name: str = attrib()
    display_name: str = attrib()
    view: str = attrib()
    view_kwargs: Dict[str, Any] = attrib()

    def url(self) -> str:
        return url_for(self.view, **self.view_kwargs)


@attrs(frozen=True)
class DbSettings(Section):
    url: str = attrib(validator=instance_of(str))


@attrs(frozen=True)
class FlaskSettings(Section):
    secret_key: str = attrib(validator=instance_of(str))
    templates_auto_reload: bool = attrib(validator=instance_of(bool), default=False)


@attrs(frozen=True)
class LoggingSettings(Section):
    level: str = attrib(validator=instance_of(str), default="INFO")


@attrs(frozen=True)
class AuthSettings(Section):
    # these are initialized in core.py
    github: bool = attrib()
    google: bool = attrib()
    no_social_auth: bool = attrib()

    github_key_id: Optional[str] = attrib(validator=optional(instance_of(str)))
    github_secret: Optional[str] = attrib(validator=optional(instance_of(str)))

    google_key_id: Optional[str] = attrib(validator=optional(instance_of(str)))
    google_secret: Optional[str] = attrib(validator=optional(instance_of(str)))

    email_magic_link: Optional[bool] = attrib(
        validator=instance_of(bool), default=False
    )
    email_magic_link_expiry: Optional[int] = attrib(
        validator=optional(instance_of(int)), default=None
    )

    signing_key: Optional[str] = attrib(
        validator=optional(instance_of(str)), default=None
    )

    def auth_methods(self) -> List[AuthMethod]:
        """
        Get a list of social auth methods.

        """
        # any which are not name.title()
        display_names = {"github": "GitHub"}
        # any which are not name
        backend_names = {"google": "google-oauth2"}
        # any which are not social-auth
        view_and_kwargs: Dict[str, Tuple[str, Dict[str, Any]]] = {
            "email": ("views.magic_link_begin", {})
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
            email = AuthMethod(
                "email", "Email Magic Link", "views.email_magic_link", {}
            )
            methods.insert(0, email)
        return methods


@attrs(frozen=True)
class SMTPSettings(Section):
    host: Optional[str] = attrib(validator=optional(instance_of(str)), default=None)
    port: Optional[int] = attrib(validator=optional(instance_of(int)), default=None)
    username: Optional[str] = attrib(validator=optional(instance_of(str)), default=None)
    use_tls: bool = attrib(default=True)
    password: Optional[str] = attrib(validator=optional(instance_of(str)), default=None)
    sender: Optional[str] = attrib(validator=optional(instance_of(str)), default=None)


@attrs(frozen=True)
class SentrySettings(Section):
    dsn: Optional[str] = attrib(validator=optional(instance_of(str)), default=None)


@attrs(frozen=True)
class Settings:
    auth: AuthSettings = attrib()
    db: DbSettings = attrib()
    flask: FlaskSettings = attrib()
    logging: LoggingSettings = attrib()
    smtp: SMTPSettings = attrib()
    sentry: SentrySettings = attrib()


def find_settings_file() -> str:
    """
    Returns the canonical location of ``yakbak.toml`` in the project root.

    """
    here = os.path.dirname(__file__)
    toml = os.path.join(here, "..", "yakbak.toml")
    return os.path.abspath(toml)


def load_settings_file(settings_path: str) -> Settings:
    with open(settings_path) as fp:
        return load_settings(dict(toml.load(fp)))


def load_settings_from_env() -> Settings:
    settings_data = {
        "db": {
            "url": os.getenv("DATABASE_URL")
        },
        "logging": {
            "level": os.getenv("LOGGING_LEVEL", "INFO")
        },
        "smtp": {
            "host": os.getenv("MAILGUN_SMTP_SERVER"),
            "port": os.getenv("MAILGUN_SMTP_PORT"),
            "username": os.getenv("MAILGUN_SMTP_LOGIN"),
            "password": os.getenv("MAILGUN_SMTP_PASSWORD"),
            "sender": os.getenv("SMPT_SENDER", "Yak-Bak <yakbak@example.com>")
        },
        "flask": {
            "secret_key": os.getenv("FLASK_SECRET_KEY"),
            "templates_auto_reload": os.getenv("FLASK_TEMPLATES_AUTO_RELOAD", False)
        },
        "auth": {
            "github_key_id": os.getenv("AUTH_GITHUB_KEY_ID"),
            "github_secret": os.getenv("AUTH_GITHUB_SECRET"),
            "google_key_id": os.getenv("AUTH_GOOGLE_KEY_ID"),
            "google_secret": os.getenv("AUTH_GOOGLE_SECRET"),
            "email_magic_link": os.getenv("AUTH_EMAIL_MAGIC_LINK", True),
            "email_magic_link_expiry": os.getenv("AUTH_EMAIL_MAGIC_LINK_EXPIRY", 28800),
            "signing_key": os.getenv("AUTH_SIGNING_KEY")
        },
        "sentry": {
            "dsn": os.getenv("SENTRY_DSN")
        }
    }

    return load_settings(settings_data)


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
            social_methods = set(
                [
                    f.name[:-7]
                    for f in fields(AuthSettings)
                    if f.name.endswith("_key_id")
                ]
            )

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

        assert field.type is not None
        top_level[section] = field.type.populate_from(data, os.environ)

    if settings_dict:
        raise InvalidSettings(
            f"settings has unexpected sections: {settings_dict.keys()}"
        )

    return Settings(**top_level)  # type: ignore
