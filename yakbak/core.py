import logging
import sys

from flask import Flask

from yakbak.settings import Settings


def create_app(settings: Settings) -> Flask:
    """
    Bootstrap the application.

    """
    set_up_logging(settings)

    app = Flask("yakbak")
    app.settings = settings
    set_up_flask_defaults(app)

    # TODO: set_up_database(app)

    from . import views
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


def set_up_flask_defaults(app: Flask) -> None:
    """
    Some of Flask's default settings make no sense for us.

    See http://flask.pocoo.org/docs/0.11/config/ for a complete list.
    """
    # Flask adds a StreamHandler to its own logger which duplicates
    # messages that we'd rather log through our own handler at the root
    for handler in list(app.logger.handlers):
        app.logger.removeHandler(handler)
