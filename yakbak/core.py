import logging
import sys

from attr import asdict
from flask import Flask
from flask_bootstrap import Bootstrap

from yakbak.auth import login_manager
from yakbak.models import db
from yakbak.settings import Settings
from yakbak.types import Application
from yakbak import views


def create_app(settings: Settings) -> Application:
    """
    Bootstrap the application.

    """
    set_up_logging(settings)

    app = Application(settings)

    set_up_flask(app)
    set_up_database(app)
    set_up_auth(app)
    set_up_bootstrap(app)

    app.register_blueprint(views.app)

    return app


def set_up_logging(settings: Settings) -> None:
    log_level_name = settings.logging.level
    log_level = getattr(logging, log_level_name)
    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(name)s:%(levelname)s] %(message)s"),
    )
    stream_handler.setLevel(log_level)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.NOTSET)
    root_logger.addHandler(stream_handler)


def set_up_flask(app: Application) -> None:
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


def set_up_database(app: Application) -> None:
    app.config["SQLALCHEMY_DATABASE_URI"] = app.settings.db.uri

    # Disable signals (callbacks) on model changes
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.app = app
    db.init_app(app)


def set_up_auth(app: Flask) -> None:
    login_manager.init_app(app)


def set_up_bootstrap(app: Flask) -> None:
    Bootstrap(app)
