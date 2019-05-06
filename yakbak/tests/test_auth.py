from datetime import datetime, timedelta

from werkzeug.test import Client
import mock
import pytest

from yakbak import auth
from yakbak.models import Conference, db, InvitationStatus, Talk, User
from yakbak.tests.util import assert_html_response, extract_csrf_from


@pytest.mark.parametrize("length, expected", [
    (60, "1 minute"),
    (120, "2 minutes"),
    (3600, "1 hour"),
    (7200, "2 hours"),
    (86400, "1 day"),
    (172800, "2 days"),
    (31536000, "1 year"),
    (63072000, "2 years"),

    # test that it doesn't do "2 days, 4 hours, 10 minutes..."
    (187800, "2 days"),
])
def test_get_magic_link_token_expiry(length: int, expected: str) -> None:
    with mock.patch.object(auth, "current_app") as app:
        app.settings.auth.email_magic_link_expiry = length
        app.settings.auth.signing_key = "abcd"

        _, expiry = auth.get_magic_link_token_and_expiry("test@example.com")

    assert expiry == expected


def test_parse_magic_link_token() -> None:
    with mock.patch.object(auth, "current_app") as app:
        app.settings.auth.signing_key = "abcd"
        app.settings.auth.email_magic_link_expiry = 10  # seconds

        token, _ = auth.get_magic_link_token_and_expiry("test@example.com")
        email = auth.parse_magic_link_token(token)

        assert email == "test@example.com"


def test_parse_magic_link_token_is_none_for_garbled_tokens() -> None:
    with mock.patch.object(auth, "current_app") as app:
        app.settings.auth.signing_key = "abcd"
        app.settings.auth.email_magic_link_expiry = 10  # seconds

        token, _ = auth.get_magic_link_token_and_expiry("test@example.com")
        token = token[:-2]
        email = auth.parse_magic_link_token(token)

        assert email is None


def test_parse_magic_link_token_is_none_for_expired_tokens() -> None:
    with mock.patch.object(auth, "current_app") as app:
        app.settings.auth.signing_key = "abcd"
        app.settings.auth.email_magic_link_expiry = -1  # surprisingly this works

        token, _ = auth.get_magic_link_token_and_expiry("test@example.com")
        email = auth.parse_magic_link_token(token)

        assert email is None


def test_talk_creation_allowed_when_no_window(user: User, client: Client) -> None:
    # this behavior is needed for backwards compatibility as we add
    # the fields for the first time to the Conference object
    conf = Conference.query.get(1)
    conf.proposals_begin = None
    conf.proposals_end = None
    db.session.add(conf)
    db.session.commit()

    client.get("/test-login/{}".format(user.user_id), follow_redirects=True)
    resp = client.get("/talks/new")
    assert_html_response(resp, status=200)


def test_talk_creation_only_allowed_in_window(user: User, client: Client) -> None:
    conf = Conference.query.get(1)
    conf.proposals_begin = datetime.utcnow() - timedelta(days=1)
    conf.proposals_end = datetime.utcnow() + timedelta(days=1)
    db.session.add(conf)
    db.session.commit()

    client.get("/test-login/{}".format(user.user_id), follow_redirects=True)
    resp = client.get("/talks/new")
    assert_html_response(resp, status=200)

    conf = Conference.query.get(1)
    conf.proposals_begin = datetime.utcnow() - timedelta(days=3)
    conf.proposals_end = datetime.utcnow() - timedelta(days=1)
    db.session.add(conf)
    db.session.commit()

    resp = client.get("/talks/new")
    assert_html_response(resp, status=400)


def test_talk_editing_not_allowed_while_voting(user: User, client: Client) -> None:
    conf = Conference.query.get(1)
    conf.voting_begin = datetime.utcnow() - timedelta(days=1)
    conf.voting_end = datetime.utcnow() + timedelta(days=1)
    db.session.add(conf)

    talk = Talk(title="My Talk", length=25)
    talk.add_speaker(user, InvitationStatus.CONFIRMED)
    db.session.add(talk)
    db.session.commit()

    db.session.refresh(talk)
    client.get("/test-login/{}".format(user.user_id), follow_redirects=True)
    resp = client.get(f"/talks/{talk.talk_id}")
    assert_html_response(resp, status=200)

    postdata = {"csrf_token": extract_csrf_from(resp)}
    resp = client.post(f"/talks/{talk.talk_id}", data=postdata)
    assert_html_response(resp, status=400)


def test_talk_editing_not_allowed_outside_proposal_window(user: User, client: Client) -> None:  # noqa: E501
    conf = Conference.query.get(1)
    conf.proposals_begin = datetime.utcnow() - timedelta(days=3)
    conf.proposals_end = datetime.utcnow() - timedelta(days=1)
    db.session.add(conf)

    talk = Talk(title="My Talk", length=25)
    talk.add_speaker(user, InvitationStatus.CONFIRMED)
    db.session.add(talk)
    db.session.commit()

    db.session.refresh(talk)
    client.get("/test-login/{}".format(user.user_id), follow_redirects=True)
    resp = client.get(f"/talks/{talk.talk_id}")
    assert_html_response(resp, status=200)

    postdata = {"csrf_token": extract_csrf_from(resp)}
    resp = client.post(f"/talks/{talk.talk_id}", data=postdata)
    assert_html_response(resp, status=400)
