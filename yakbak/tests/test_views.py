import os.path

from flask import Response
from werkzeug.test import Client
import pytest

from yakbak.core import create_app
from yakbak.models import db, User
from yakbak.settings import load_settings_file
from yakbak.types import Application


@pytest.fixture
def app() -> Application:
    here = os.path.dirname(__file__)
    root = os.path.join(here, "..", "..")
    test_toml = os.path.join(root, "yakbak.toml-test")

    settings = load_settings_file(test_toml)
    app = create_app(settings)
    app.config["TESTING"] = True

    db.create_all()

    return app


@pytest.fixture
def client(app: Application) -> Client:
    return app.test_client()


def assert_html_response(resp: Response) -> str:
    """
    Ensure ``resp`` has certain common HTTP headers for HTML responses.

    Returns the decoded HTTP response body.
    """
    assert resp.headers["Content-Type"].startswith("text/html")
    assert "charset" in resp.headers["Content-Type"]

    data = resp.data
    assert resp.content_length == len(data)

    return data.decode(resp.mimetype_params["charset"])


def assert_html_response_contains(resp: Response, *snippets: str) -> None:
    """
    Ensure that each of the ``snippets`` is in the body of ``resp``.

    """
    content = assert_html_response(resp)
    for snippet in snippets:
        assert snippet in content


def test_login_with_existing_user_id_redirects_to_homepage(client: Client) -> None:
    db.session.add(User(user_id=1, name="Test User", email="test@example.com"))
    db.session.commit()

    resp = client.get("/")
    assert_html_response_contains(resp, "You are anonymous")

    resp = client.post("/login", data=dict(user_id="1"), follow_redirects=True)
    assert_html_response_contains(resp, "You are Test User")


def test_login_with_missing_user_id(client: Client) -> None:
    resp = client.get("/")
    assert_html_response_contains(resp, "You are anonymous")

    resp = client.post("/login", data=dict(user_id="1"), follow_redirects=True)
    assert_html_response_contains(resp, "User ID not found")  # the flash message


def test_logout_logs_you_out(client: Client) -> None:
    db.session.add(User(user_id=1, name="Test User", email="test@example.com"))
    db.session.commit()

    resp = client.get("/")
    assert_html_response_contains(resp, "You are anonymous")

    resp = client.post("/login", data=dict(user_id="1"), follow_redirects=True)
    assert_html_response_contains(resp, "You are Test User")

    resp = client.get("/logout", follow_redirects=True)
    assert_html_response_contains(resp, "You are anonymous")
