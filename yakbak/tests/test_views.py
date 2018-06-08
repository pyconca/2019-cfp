from typing import Pattern, Union
import re

from flask import Response
from werkzeug.test import Client
import bs4
import mock

from yakbak import mail, views
from yakbak.models import db, Talk, User


def assert_html_response(resp: Response, status: int = 200) -> str:
    """
    Ensure ``resp`` has certain common HTTP headers for HTML responses.

    Returns the decoded HTTP response body.

    """
    assert resp.status_code == status
    assert resp.headers["Content-Type"].startswith("text/html")
    if status == 200:
        assert "charset" in resp.headers["Content-Type"]

    data = resp.data
    assert resp.content_length == len(data)

    return data.decode(resp.charset or "utf8")


def assert_html_response_contains(resp: Response, *snippets: Union[str, Pattern], status: int = 200) -> None:  # noqa: E501
    """
    Ensure that each of the ``snippets`` is in the body of ``resp``.

    """
    content = assert_html_response(resp, status)
    for snippet in snippets:
        if isinstance(snippet, Pattern):
            assert re.search(snippet, content), f"{snippet!r} does not match {content!r}"
        else:
            assert snippet in content


def assert_redirected(resp: Response, to: str) -> None:
    assert_html_response(resp, 302)

    landing_url = f"http://localhost{to}"
    assert resp.headers["Location"] == landing_url


def extract_csrf_from(resp: Response) -> str:
    data = resp.data
    body = data.decode(resp.mimetype_params["charset"])
    tags = re.findall('(<input[^>]*type="hidden"[^>]*>)', body)
    assert len(tags) == 1
    match = re.search('value="([^"]*)"', tags[0])
    assert match, "CSRF hidden input had no value"
    return match.group(1)


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


def test_email_magic_link_form(client: Client) -> None:
    resp = client.get("/login/email")
    assert_html_response_contains(resp, re.compile('<input.*name="email"'))
    csrf_token = extract_csrf_from(resp)

    postdata = {"email": "jane@example.com", "csrf_token": csrf_token}
    with mock.patch.object(mail, "send_mail") as send_mail:
        resp = client.post("/login/email", data=postdata, follow_redirects=True)

    assert_html_response_contains(resp, "We have sent a link to you")
    send_mail.assert_called_once_with(
        to=["jane@example.com"],
        template="email/magic-link",
        magic_link=mock.ANY,
        magic_link_expiration="30 minutes",
    )


def test_email_magic_link_login_for_new_user(client: Client) -> None:
    with mock.patch.object(views, "parse_magic_link_token") as parse:
        parse.return_value = "jane@example.com"
        resp = client.get("/login/token/any-token-here", follow_redirects=True)

    assert_html_response_contains(resp, "User Profile")


def test_email_magic_link_login_for_returning_user(client: Client, user: User) -> None:
    with mock.patch.object(views, "parse_magic_link_token") as parse:
        parse.return_value = user.email
        resp = client.get("/login/token/any-token-here", follow_redirects=True)

    assert_html_response_contains(resp, "Dashboard")


def test_invalid_email_magic_link_login(client: Client) -> None:
    with mock.patch.object(views, "parse_magic_link_token") as parse:
        parse.return_value = None
        resp = client.get("/login/token/any-token-here", follow_redirects=True)

    assert_html_response(resp, status=404)


def test_profile_updates_name_not_email(client: Client, user: User) -> None:
    resp = client.get("/test-login/{}".format(user.user_id), follow_redirects=True)
    resp = client.get("/profile")
    assert_html_response_contains(
        resp,
        re.compile('<input[^>]*name="fullname"'),
        re.compile('<input[^>]*id="email"[^>]*disabled'),
    )

    csrf_token = extract_csrf_from(resp)
    postdata = {
        "email": "jane@example.com",
        "fullname": "Jane Doe",
        "csrf_token": csrf_token,
    }
    resp = client.post("/profile", data=postdata, follow_redirects=True)
    assert_html_response_contains(resp, "Dashboard")

    db.session.add(user)
    db.session.refresh(user)
    assert user.fullname == "Jane Doe"
    assert user.email == "test@example.com"  # the old address


def test_dashboard_lists_talks(client: Client, user: User) -> None:
    alice = User(email="alice@example.com", fullname="Alice Example")
    bob = User(email="bob@example.com", fullname="Bob Example")
    db.session.add(alice)
    db.session.add(bob)
    db.session.commit()

    one_talk = Talk(title="My Talk", speakers=[user], length=25)
    two_talk = Talk(title="Our Talk", speakers=[user, alice], length=40)
    all_talk = Talk(title="All Our Talk", speakers=[user, alice, bob], length=25)
    db.session.add(one_talk)
    db.session.add(two_talk)
    db.session.add(all_talk)
    db.session.commit()

    client.get("/test-login/{}".format(user.user_id))
    resp = client.get("/dashboard")
    body = assert_html_response(resp)
    soup = bs4.BeautifulSoup(body, "html.parser")

    talks = soup.find_all("div", class_="talk")
    assert len(talks) == 3

    talk_row_texts = [re.sub("\s+", " ", talk.get_text()).strip() for talk in talks]
    assert sorted(talk_row_texts) == sorted([
        "My Talk (25 Minutes)",
        "Our Talk (40 Minutes, Alice Example and You)",
        "All Our Talk (25 Minutes, Alice Example, Bob Example, and You)",
    ])


def test_create_talk_goes_to_preview(client: Client, user: User) -> None:
    client.get("/test-login/{}".format(user.user_id))
    resp = client.get("/talks/new")
    csrf_token = extract_csrf_from(resp)

    postdata = {
        "title": "My Awesome Talk",
        "length": "25",
        "csrf_token": csrf_token,
    }

    resp = client.post("/talks/new", data=postdata, follow_redirects=True)
    assert_html_response_contains(
        resp,
        "Reviewers will see voting instructions here",
        "Save &amp; Return",
        "Edit Again",
    )

    # but at this point the talk is saved
    speakers_predicate = Talk.speakers.any(user_id=user.user_id)  # type: ignore
    talks = Talk.query.filter(speakers_predicate).all()
    assert len(talks) == 1
    assert talks[0].title == "My Awesome Talk"
