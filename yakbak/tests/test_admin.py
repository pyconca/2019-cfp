from werkzeug.test import Client
import mock

from yakbak import mail
from yakbak.models import db, InvitationStatus, Talk, User
from yakbak.tests.util import (
    assert_html_response,
    assert_html_response_contains,
    extract_csrf_from,
)


def test_anonymous_users_cant_access_admin(client: Client) -> None:
    resp = client.get("/manage/")
    assert_html_response(resp, status=404)


def test_ordinary_users_cant_access_admin(client: Client, user: User) -> None:
    client.get("/test-login/{}".format(user.user_id), follow_redirects=True)
    resp = client.get("/manage/")
    assert_html_response(resp, status=404)


def test_site_admins_can_access_admin(client: Client, user: User) -> None:
    client.get("/test-login/{}".format(user.user_id), follow_redirects=True)

    user.site_admin = True
    db.session.add(user)
    db.session.commit()

    resp = client.get("/manage/")
    assert_html_response(resp, status=200)


def test_talk_anonymization(client: Client, user: User) -> None:
    user.site_admin = True
    db.session.add(user)

    talk = Talk(
        title="Alice's Identifying Talk",
        description="This talk is by Alice",
        outline="Alice!",
        length=25,
    )
    talk.add_speaker(user, InvitationStatus.CONFIRMED)
    db.session.add(talk)
    db.session.commit()

    db.session.refresh(talk)

    client.get("/test-login/{}".format(user.user_id), follow_redirects=True)
    resp = client.get(f"/manage/anonymize/{talk.talk_id}")
    assert_html_response_contains(resp, "Alice&#x27;s Identifying Talk")

    postdata = {
        "title": "(Speaker name redacted)'s Identifying Talk",
        "description": "This talk is by (Speaker name redacted)",
        "outline": "(Speaker name redacted)!",
        "csrf_token": extract_csrf_from(resp),
    }
    with mock.patch.object(mail, "send_mail") as send_mail:
        client.post(f"/manage/anonymize/{talk.talk_id}", data=postdata)

    talk = Talk.query.get(talk.talk_id)
    assert talk.is_anonymized is True
    assert talk.has_anonymization_changes is True
    assert talk.anonymized_title == "(Speaker name redacted)'s Identifying Talk"
    assert talk.anonymized_description == "This talk is by (Speaker name redacted)"
    assert talk.anonymized_outline == "(Speaker name redacted)!"
    assert talk.title == "Alice's Identifying Talk"
    assert talk.description == "This talk is by Alice"
    assert talk.outline == "Alice!"

    send_mail.assert_called_once_with(
        to=[user.email],
        template="email/talk-anonymized",
        talk_id=talk.talk_id,
        title=talk.title,  # the original title
    )


def test_talk_anonymization_doesnt_set_is_anonymized_if_no_changes(client: Client, user: User) -> None:  # noqa: E501
    user.site_admin = True
    db.session.add(user)

    talk = Talk(
        title="Alice's Identifying Talk",
        description="This talk is by Alice",
        outline="Alice!",
        length=25,
    )
    talk.add_speaker(user, InvitationStatus.CONFIRMED)
    db.session.add(talk)
    db.session.commit()

    db.session.refresh(talk)

    client.get("/test-login/{}".format(user.user_id), follow_redirects=True)
    resp = client.get(f"/manage/anonymize/{talk.talk_id}")
    assert_html_response_contains(resp, "Alice&#x27;s Identifying Talk")

    postdata = {
        "title": talk.title,
        "description": talk.description,
        "outline": talk.outline,
        "csrf_token": extract_csrf_from(resp),
    }
    with mock.patch.object(mail, "send_mail") as send_mail:
        client.post(f"/manage/anonymize/{talk.talk_id}", data=postdata)

    talk = Talk.query.get(talk.talk_id)
    assert talk.is_anonymized is True
    assert talk.has_anonymization_changes is False
    assert talk.anonymized_title == talk.title
    assert talk.anonymized_description == talk.anonymized_description
    assert talk.anonymized_outline == talk.outline

    assert not send_mail.called
