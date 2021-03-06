from typing import Any, Dict
import logging
import os
import sys

from attr import asdict
from flask import g
from flask_wtf.csrf import CSRFProtect
from sentry_sdk.integrations.flask import FlaskIntegration
from social_flask.routes import social_auth
from social_flask_sqlalchemy.models import init_social
import sentry_sdk

from yakbak import admin, view_helpers, views
from yakbak.auth import login_manager
from yakbak.mail import mail
from yakbak.models import Conference, db
from yakbak.settings import Settings
from yakbak.types import Application

logger = logging.getLogger("core")

# When run with `flask run ...`, Flask loads the application
# several times per process (!) which causes issues with some
# globally-initalized stuff in social auth. Use this cache to
# return singleton instances
APP_CACHE: Dict[int, Application] = {}


def create_app(settings: Settings, flask_config: Dict[str, Any] = None) -> Application:
    """
    Bootstrap the application.

    """
    set_up_logging(settings)
    set_up_sentry(settings)

    app = APP_CACHE.get(os.getpid())
    if app is not None:
        logging.info("Returning %r from APP_CACHE", app)
        return app
    else:
        app = Application(settings)
        # remove any instances from other pids
        APP_CACHE.clear()
        APP_CACHE[os.getpid()] = app

    if flask_config is None:
        flask_config = {}
    set_up_flask(app, flask_config)
    set_up_database(app)
    set_up_auth(app)
    set_up_mail(app)
    set_up_admin(app)
    CSRFProtect(app)

    app.register_blueprint(views.app)
    app.register_blueprint(view_helpers.app)  # filters etc
    app.register_blueprint(social_auth, url_prefix="/login/external")

    set_up_handlers(app)

    return app


def set_up_logging(settings: Settings) -> None:
    log_level_name = settings.logging.level
    log_level = getattr(logging, log_level_name)
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(name)s:%(levelname)s] %(message)s")
    )
    stream_handler.setLevel(log_level)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.NOTSET)
    root_logger.addHandler(stream_handler)


def set_up_sentry(settings: Settings) -> None:
    sentry_sdk.init(dsn=settings.sentry.dsn, integrations=[FlaskIntegration()])


def set_up_flask(app: Application, flask_config: Dict[str, Any]) -> None:
    """
    Some of Flask's default settings make no sense for us.

    See http://flask.pocoo.org/docs/0.11/config/ for a complete list.
    """
    # Flask adds a StreamHandler to its own logger which duplicates
    # messages that we'd rather log through our own handler at the root
    for handler in list(app.logger.handlers):
        app.logger.removeHandler(handler)

    for key, value in asdict(app.settings.flask).items():
        app.config[key.upper()] = value

    app.config.update(flask_config)


def set_up_database(app: Application) -> None:
    app.config["SQLALCHEMY_DATABASE_URI"] = app.settings.db.url

    # Disable signals (callbacks) on model changes
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.app = app
    db.init_app(app)


def set_up_auth(app: Application) -> None:
    login_manager.init_app(app)

    if app.settings.auth.no_social_auth:
        # Should only be true in testing! But it avoids some issues
        # in how social-sqlalchemy defines its models at call time.
        return

    app.config["SOCIAL_AUTH_USER_MODEL"] = "yakbak.models.User"
    app.config["SOCIAL_AUTH_USER_FIELDS"] = ["email", "fullname"]
    app.config["SOCIAL_AUTH_STORAGE"] = "social_flask_sqlalchemy.models.FlaskStorage"
    app.config["SOCIAL_AUTH_PROTECTED_USER_FIELDS"] = ["email", "fullname"]
    app.config["SOCIAL_AUTH_LOGIN_REDIRECT_URL"] = "/talks"

    app.config["SOCIAL_AUTH_AUTHENTICATION_BACKENDS"] = [
        "social_core.backends.google.GoogleOAuth2",
        "social_core.backends.github.GithubOAuth2",
    ]

    # See https://python-social-auth.readthedocs.io/en/latest/pipeline.html for details
    app.config["SOCIAL_AUTH_PIPELINE"] = (
        "social_core.pipeline.social_auth.social_details",
        "social_core.pipeline.social_auth.social_uid",
        "social_core.pipeline.social_auth.auth_allowed",
        "social_core.pipeline.social_auth.social_user",
        "social_core.pipeline.social_auth.associate_by_email",  # <= inserted vs default
        "social_core.pipeline.user.get_username",
        "social_core.pipeline.user.create_user",
        "social_core.pipeline.social_auth.associate_user",
        "social_core.pipeline.social_auth.load_extra_data",
        "social_core.pipeline.user.user_details",
    )

    cfg = app.settings.auth
    if cfg.github:
        app.config["SOCIAL_AUTH_GITHUB_KEY"] = cfg.github_key_id
        app.config["SOCIAL_AUTH_GITHUB_SECRET"] = cfg.github_secret
        app.config["SOCIAL_AUTH_GITHUB_SCOPE"] = ["read:user", "user:email"]

    if cfg.google:
        app.config["SOCIAL_AUTH_GOOGLE_OAUTH2_KEY"] = cfg.google_key_id
        app.config["SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET"] = cfg.google_secret
        app.config["SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE"] = [
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ]

    init_social(app, db.session)


def set_up_mail(app: Application) -> None:
    app.config["MAIL_SERVER"] = app.settings.smtp.host
    app.config["MAIL_PORT"] = app.settings.smtp.port
    app.config["MAIL_USERNAME"] = app.settings.smtp.username
    app.config["MAIL_PASSWORD"] = app.settings.smtp.password
    app.config["MAIL_DEFAULT_SENDER"] = app.settings.smtp.sender
    app.config["MAIL_USE_TLS"] = app.settings.smtp.use_tls
    app.config["MAIL_MAX_EMAILS"] = 10  # guess

    mail.init_app(app)


def set_up_admin(app: Application) -> None:
    app.register_blueprint(admin.app, url_prefix="/manage")
    admin.flask_admin.init_app(app)


def set_up_handlers(app: Application) -> None:
    @app.before_request
    def load_conference() -> None:
        # TODO: load by URL or something
        g.conference = Conference.query.order_by(Conference.created).first()
