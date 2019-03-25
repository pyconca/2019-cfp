from typing import List
import re

from werkzeug.test import Client
import bs4
import mock

from yakbak import mail
from yakbak.models import db, InvitationStatus, Talk, User
from yakbak.tests.util import (
    assert_html_response,
    assert_html_response_contains,
    assert_html_response_doesnt_contain,
    extract_csrf_from,
)


def assert_talk_has_speakers(talk: Talk, speaker_emails: List[str]) -> None:
    # check on the state of the talk in the DB, rather than the in-memory copy
    talk = Talk.query.filter_by(talk_id=talk.talk_id).one()

    talk_speaker_emails = set(ts.user.email for ts in talk.speakers)
    for email in speaker_emails:
        assert email in talk_speaker_emails


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

    _, kwargs = send_mail.call_args
    assert kwargs["talk"].talk_id == talk.talk_id

    assert_talk_has_speakers(talk, ["alice@example.com"])


def test_inviting_a_speaker_emails_the_speaker(client: Client, user: User) -> None:
    talk = Talk(title="My Talk", length=25)
    talk.add_speaker(user, InvitationStatus.CONFIRMED)
    db.session.add(talk)
    db.session.commit()

    assert User.query.filter_by(email="alice@example.com").one_or_none() is None

    # reload from DB to avoid "not attached to session" error
    talk = Talk.query.filter_by(title="My Talk").one()

    client.get("/test-login/{}".format(user.user_id))
    resp = client.get("/talks/{}/speakers".format(talk.talk_id))
    assert_html_response(resp)
    csrf_token = extract_csrf_from(resp)

    # this speaker doesn't exist, but we should still send the email
    postdata = {"email": "alice@example.com", "csrf_token": csrf_token}
    with mock.patch.object(mail, "send_mail") as send_mail:
        resp = client.post(
            "/talks/{}/speakers".format(talk.talk_id),
            data=postdata,
            follow_redirects=True,
        )

    assert_html_response_contains(resp, "alice@example.com")

    send_mail.assert_called_once_with(
        to=["alice@example.com"],
        template="email/speaker-invite",
        talk=mock.ANY,
    )

    _, kwargs = send_mail.call_args
    assert kwargs["talk"].talk_id == talk.talk_id

    # this also implies a user with that email was created
    assert_talk_has_speakers(talk, ["alice@example.com"])


def test_talks_list_shows_invitations(client: Client, user: User) -> None:
    alice = User(email="alice@example.com", fullname="Alice Example")
    db.session.add(alice)

    talk = Talk(title="My Talk", length=25)
    talk.add_speaker(alice, InvitationStatus.CONFIRMED)  # original speaker
    talk.add_speaker(user, InvitationStatus.PENDING)
    db.session.add(talk)
    db.session.commit()

    client.get("/test-login/{}".format(user.user_id))
    resp = client.get("/talks")

    assert_html_response_contains(
        resp,
        "Speaker Invitations:",
        "My Talk",
        "(25 Minutes, Alice Example and You)",
        '<a href="/talks/1/speakers/reject" class="btn btn-outline-danger btn-sm">Reject</a>',   # noqa: E501
        '<a href="/talks/1/speakers/accept" class="btn btn-outline-primary btn-sm">Accept</a>',  # noqa: E501
    )


def test_accept_button_accepts_the_talk(client: Client, user: User) -> None:
    alice = User(email="alice@example.com", fullname="Alice Example")
    db.session.add(alice)

    talk = Talk(title="My Talk", length=25)
    talk.add_speaker(alice, InvitationStatus.CONFIRMED)  # original speaker
    talk.add_speaker(user, InvitationStatus.PENDING)
    db.session.add(talk)
    db.session.commit()

    client.get("/test-login/{}".format(user.user_id))
    client.get("/talks/1/speakers/accept")
    resp = client.get("/talks")

    assert_html_response_contains(
        resp,
        "My Talk",
        "(25 Minutes, Alice Example and You)",
    )
    assert_html_response_doesnt_contain(
        resp,
        "Speaker Invitations:",
        "Reject",
        "Accept",
    )


def test_accept_button_rejects_the_talk(client: Client, user: User) -> None:
    alice = User(email="alice@example.com", fullname="Alice Example")
    db.session.add(alice)

    talk = Talk(title="My Talk", length=25)
    talk.add_speaker(alice, InvitationStatus.CONFIRMED)  # original speaker
    talk.add_speaker(user, InvitationStatus.PENDING)
    db.session.add(talk)
    db.session.commit()

    client.get("/test-login/{}".format(user.user_id))
    client.get("/talks/1/speakers/reject")
    resp = client.get("/talks")

    assert_html_response_contains(
        resp,
        "My Talk",
        "(25 Minutes, Alice Example and You)",
        "Speaker Invitations:",
        "Accept",
    )
    assert_html_response_doesnt_contain(
        resp,
        "Reject",
    )
