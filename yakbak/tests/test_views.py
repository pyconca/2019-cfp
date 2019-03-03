from typing import Pattern, Union
import re

from flask import Response
from werkzeug.test import Client
import bs4
import mock

from yakbak import mail, views
from yakbak.models import db, InvitationStatus, Talk, User


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


def assert_html_response_doesnt_contain(resp: Response, *snippets: Union[str, Pattern], status: int = 200) -> None:  # noqa: E501
    """
    Ensure that none of the ``snippets`` is in the body of ``resp``.

    """
    content = assert_html_response(resp, status)
    for snippet in snippets:
        if isinstance(snippet, Pattern):
            assert not re.search(snippet, content), f"{snippet!r} should not match {content!r}"  # noqa: E501
        else:
            assert snippet not in content


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


def test_root_shows_cfp_description_when_logged_out(client: Client) -> None:
    resp = client.get("/")
    assert_html_response_contains(resp, "Our Call for Proposals is open through")


def test_root_redirects_to_dashboard_when_logged_in(client: Client, user: User) -> None:
    resp = client.get("/test-login/{}".format(user.user_id), follow_redirects=True)

    resp = client.get("/")
    assert_redirected(resp, "/dashboard")


def test_dashboard_shows_user_name(client: Client, user: User) -> None:
    resp = client.get("/test-login/{}".format(user.user_id), follow_redirects=True)
    assert_html_response_contains(resp, f"Log Out ({user.fullname})")


def test_logout_logs_you_out(client: Client, user: User) -> None:
    resp = client.get("/test-login/{}".format(user.user_id), follow_redirects=True)
    assert_html_response_contains(resp, f"Log Out ({user.fullname})")

    resp = client.get("/logout", follow_redirects=True)
    assert_html_response_contains(resp, "Log In")


def test_login_shows_auth_methods(client: Client) -> None:
    # only the email auth method is enabled in test config :\
    resp = client.get("/login")
    assert_html_response_contains(resp, "Magic Link")


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

    one_talk = Talk(title="My Talk", length=25)
    one_talk.add_speaker(user, InvitationStatus.CONFIRMED)

    two_talk = Talk(title="Our Talk", length=40)
    two_talk.add_speaker(user, InvitationStatus.CONFIRMED)
    two_talk.add_speaker(alice, InvitationStatus.CONFIRMED)

    all_talk = Talk(title="All Our Talk", length=25)
    all_talk.add_speaker(user, InvitationStatus.CONFIRMED)
    all_talk.add_speaker(alice, InvitationStatus.CONFIRMED)
    all_talk.add_speaker(bob, InvitationStatus.CONFIRMED)

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

    talk_row_texts = [re.sub(r"\s+", " ", talk.get_text()).strip() for talk in talks]
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


def test_talk_form_uses_select_field_for_length(client: Client, user: User) -> None:
    client.get("/test-login/{}".format(user.user_id))
    resp = client.get("/talks/new")

    assert_html_response_contains(
        resp,
        re.compile(
            '<select[^>]*(?:name="length"[^>]*required|required[^>]*name="length")',
        ),
    )


def test_speakers_button_shows_up_on_existing_talks(client: Client, user: User) -> None:
    talk = Talk(title="My Talk", length=25)
    talk.add_speaker(user, InvitationStatus.CONFIRMED)
    db.session.add(talk)
    db.session.commit()

    # reload from DB to avoid "not attached to session" error
    talk = Talk.query.filter_by(title="My Talk").one()

    client.get("/test-login/{}".format(user.user_id))
    resp = client.get("/talks/{}".format(talk.talk_id))

    assert_html_response_contains(
        resp,
        re.compile(
            '<a href="/talks/{}/speakers".*class=".*btn.*">'
            "Manage Speakers</a>".format(talk.talk_id),
        ),
    )


def test_speakers_button_doesnt_show_up_on_new_talks(client: Client, user: User) -> None:
    client.get("/test-login/{}".format(user.user_id))
    resp = client.get("/talks/new")

    assert_html_response_doesnt_contain(
        resp,
        re.compile("<a href=[^>]*>Manage Speakers</a>"),
    )


def test_manage_speakers_page_shows_primary_speaker(client: Client, user: User) -> None:
    talk = Talk(title="My Talk", length=25)
    talk.add_speaker(user, InvitationStatus.CONFIRMED)
    db.session.add(talk)
    db.session.commit()

    # reload from DB to avoid "not attached to session" error
    talk = Talk.query.filter_by(title="My Talk").one()

    client.get("/test-login/{}".format(user.user_id))
    resp = client.get("/talks/{}/speakers".format(talk.talk_id))

    body = assert_html_response(resp)
    soup = bs4.BeautifulSoup(body, "html.parser")

    speakers = soup.find_all("div", class_="speaker")
    assert len(speakers) == 1

    row_texts = [re.sub(r"\s+", " ", row.get_text()).strip() for row in speakers]
    assert row_texts == ["{} ({}) Confirmed".format(user.fullname, user.email)]


def test_manage_speakers_page_shows_other_speakers(client: Client, user: User) -> None:
    alice = User(email="alice@example.com", fullname="Alice Example")
    bob = User(email="bob@example.com", fullname="Bob Example")
    charlie = User(email="charlie@example.com", fullname="Charlie Example")
    db.session.add(alice)
    db.session.add(bob)
    db.session.add(charlie)

    talk = Talk(title="My Talk", length=25)
    talk.add_speaker(user, InvitationStatus.CONFIRMED)
    talk.add_speaker(alice, InvitationStatus.PENDING)
    talk.add_speaker(bob, InvitationStatus.REJECTED)
    talk.add_speaker(charlie, InvitationStatus.DELETED)
    db.session.add(talk)
    db.session.commit()

    # reload from DB to avoid "not attached to session" error
    talk = Talk.query.filter_by(title="My Talk").one()

    client.get("/test-login/{}".format(user.user_id))
    resp = client.get("/talks/{}/speakers".format(talk.talk_id))

    body = assert_html_response(resp)
    soup = bs4.BeautifulSoup(body, "html.parser")

    speakers = soup.find_all("div", class_="speaker")
    assert len(speakers) == 4

    row_texts = [re.sub(r"\s+", " ", row.get_text()).strip() for row in speakers]
    assert sorted(row_texts) == sorted([
        "{} ({}) Confirmed".format(user.fullname, user.email),
        "Alice Example (alice@example.com) Pending Uninvite",
        "Bob Example (bob@example.com) Rejected",
        "Charlie Example (charlie@example.com) Deleted Reinvite",
    ])


def test_inviting_a_speaker_adds_the_speaker(client: Client, user: User) -> None:
    talk = Talk(title="My Talk", length=25)
    talk.add_speaker(user, InvitationStatus.CONFIRMED)
    db.session.add(talk)

    alice = User(email="alice@example.com", fullname="Alice Example")
    db.session.add(alice)
    db.session.commit()

    # reload from DB to avoid "not attached to session" error
    talk = Talk.query.filter_by(title="My Talk").one()

    client.get("/test-login/{}".format(user.user_id))
    resp = client.get("/talks/{}/speakers".format(talk.talk_id))
    assert_html_response(resp)
    csrf_token = extract_csrf_from(resp)

    postdata = {"email": "alice@example.com", "csrf_token": csrf_token}
    with mock.patch.object(mail, "send_mail") as send_mail:
        resp = client.post(
            "/talks/{}/speakers".format(talk.talk_id),
            data=postdata,
            follow_redirects=True,
        )

    assert_html_response_contains(resp, "Alice Example")

    send_mail.assert_called_once_with(
        to=["alice@example.com"],
        template="email/speaker-invite",
        talk=mock.ANY,
    )

    # the Talk instances are not ==, but make sure it's the right one
    _, kwargs = send_mail.call_args
    assert kwargs["talk"].talk_id == talk.talk_id

    talk = Talk.query.filter_by(title="My Talk").one()
    alice = User.query.filter_by(email="alice@example.com").one()

    for talk_speaker in talk.speakers:
        if talk_speaker.user == alice:
            assert talk_speaker.state == InvitationStatus.PENDING
            break
    else:
        assert False, "alice@example.com did not get attached to the talk"
