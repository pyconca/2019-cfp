from typing import Iterable
import os.path

from flask import abort, redirect, Response
from flask_login import login_user
from werkzeug.test import Client
import pytest

from yakbak.auth import load_user
from yakbak.core import APP_CACHE, create_app
from yakbak.models import db, User
from yakbak.settings import load_settings_file
from yakbak.types import Application


@pytest.fixture
def app() -> Iterable[Application]:
    APP_CACHE.clear()

    here = os.path.dirname(__file__)
    test_toml = os.path.join(here, "yakbak.toml-test")

    settings = load_settings_file(test_toml)
    app = create_app(settings)
    app.config["TESTING"] = True

    # cheeky: add a /test-login endpoint to the app,
    # logging in with social auth in tests is tough
    @app.route("/test-login/<user_id>")
    def test_login(user_id: str) -> Response:
        user = load_user(user_id)
        if not user:
            abort(401)
        login_user(user)
        return redirect("/")

    db.create_all()
    yield app
    db.drop_all()


@pytest.fixture
def client(app: Application) -> Client:
    return app.test_client()


@pytest.fixture
def user() -> User:
    user = User(fullname="Test User", email="test@example.com")
    db.session.add(user)
    db.session.commit()

    # TODO: This avoids an error where SQLAlchemy says that the user
    # is not associated with a session. I don't understand why.
    list(User.query.all())

    return user


def assert_html_response(resp: Response, status: int = 200) -> str:
    """
    Ensure ``resp`` has certain common HTTP headers for HTML responses.

    Returns the decoded HTTP response body.

    """
    assert resp.status_code == status
    assert resp.headers["Content-Type"].startswith("text/html")
    assert "charset" in resp.headers["Content-Type"]

    data = resp.data
    assert resp.content_length == len(data)

    return data.decode(resp.mimetype_params["charset"])


def assert_html_response_contains(resp: Response, *snippets: str, status: int = 200) -> None:  # noqa: E501
    """
    Ensure that each of the ``snippets`` is in the body of ``resp``.

    """
    content = assert_html_response(resp, status)
    for snippet in snippets:
        assert snippet in content


def assert_redirected(resp: Response, to: str) -> None:
    assert_html_response(resp, 302)

    landing_url = f"http://localhost{to}"
    assert resp.headers["Location"] == landing_url


def test_homepage_redirects_to_login(client: Client) -> None:
    resp = client.get("/")
    assert_redirected(resp, "/login")


def test_homepage_shows_user_name(client: Client, user: User) -> None:
    resp = client.get("/test-login/{}".format(user.user_id), follow_redirects=True)
    assert_html_response_contains(resp, f"Log Out ({user.fullname})")


def test_logout_logs_you_out(client: Client, user: User) -> None:
    resp = client.get("/test-login/{}".format(user.user_id), follow_redirects=True)
    assert_html_response_contains(resp, f"Log Out ({user.fullname})")

    resp = client.get("/logout", follow_redirects=True)
    assert_html_response_contains(resp, "Log In")
