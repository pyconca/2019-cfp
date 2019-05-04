from typing import Generator, Iterable
import json
import os.path

from flask import abort, redirect
from flask_login import login_user
from werkzeug.test import Client
from werkzeug.wrappers import Response
import jinja2
import mock
import pytest

from yakbak import mail
from yakbak.auth import load_user
from yakbak.core import APP_CACHE, create_app
from yakbak.models import Conference, db, User
from yakbak.settings import load_settings_file
from yakbak.types import Application


@pytest.fixture
def app() -> Iterable[Application]:
    APP_CACHE.clear()

    here = os.path.dirname(__file__)
    test_toml = os.path.join(here, "yakbak.toml-test")

    settings = load_settings_file(test_toml)
    flask_config = {
        "TESTING": True,
        "MAIL_SUPPRESS_SEND": True,
    }
    app = create_app(settings, flask_config)

    db.create_all()

    # views will expect that there's a conference object in the DB
    conference_json = os.path.join(here, "conference.json-test")
    with open(conference_json) as fp:
        conference_fields = json.load(fp)

    conference = Conference(**conference_fields)
    db.session.add(conference)
    db.session.commit()

    test_templates_dir = os.path.join(here, "templates")
    my_loader = jinja2.ChoiceLoader([
        app.jinja_loader,
        jinja2.FileSystemLoader(test_templates_dir),
    ])
    setattr(app, "jinja_loader", my_loader)

    # cheeky: add a /test-login endpoint to the app,
    # logging in with social auth in tests is tough
    @app.route("/test-login/<user_id>")
    def test_login(user_id: str) -> Response:
        user = load_user(user_id)
        if not user:
            abort(401)
        login_user(user)
        return redirect("/")

    yield app

    # remove() clears any in-process state; because of where we
    # define the session, a new one is not created when we call
    # create_app()
    db.session.remove()
    db.drop_all()


@pytest.fixture
def client(app: Application) -> Client:
    return app.test_client()


@pytest.yield_fixture
def send_mail() -> Generator[mock.Mock, None, None]:
    with mock.patch.object(mail, "send_mail") as send_mail:
        yield send_mail


@pytest.fixture
def user(app: Application) -> User:
    user = User(fullname="Test User", email="test@example.com")
    db.session.add(user)
    db.session.commit()

    return user
