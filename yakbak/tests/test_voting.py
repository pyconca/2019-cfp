"""Test voting functionality."""

from datetime import datetime, timedelta

from mock import Mock
from werkzeug.test import Client
import pytest

from yakbak.models import Category, ConductReport, Conference, db, Talk, User, Vote
from yakbak.types import Application


@pytest.fixture(autouse=True)
def enable_voting(app: Application) -> None:
    """Enable voting for the test conference."""
    conference = Conference.query.first()
    conference.voting_begin = datetime.utcnow() - timedelta(days=1)
    conference.voting_end = datetime.utcnow() + timedelta(days=2)
    db.session.commit()


def test_report_conduct_issue(
    *, authenticated_client: Client, send_mail: Mock, user: User
) -> None:
    """Test that a user can successfully report a CoC issue."""
    talk = Talk(title="", length=1)
    db.session.add(talk)
    db.session.commit()
    resp = authenticated_client.post(
        "/conduct-report",
        data={"talk_id": talk.talk_id, "text": "Please review", "anonymous": 0},
    )

    send_mail.assert_called_once()
    assert resp.status_code == 302
    assert ConductReport.query.filter_by(user=user).count() == 1


def test_report_conduct_issue_anonymous(
    *, authenticated_client: Client, send_mail: Mock, user: User
) -> None:
    """Test that a user can successfully report a CoC issue."""
    talk = Talk(title="", length=1)
    db.session.add(talk)
    db.session.commit()
    resp = authenticated_client.post(
        "/conduct-report",
        data={"talk_id": talk.talk_id, "text": "Please review", "anonymous": 1},
    )

    send_mail.assert_called_once()
    assert resp.status_code == 302
    assert ConductReport.query.count() == 1
    assert ConductReport.query.filter_by(user=user).count() == 0


def test_vote_save(*, authenticated_client: Client, user: User) -> None:
    """Test that a vote can be saved."""
    talk = Talk(title="", length=1)
    vote = Vote(talk=talk, user=user)
    db.session.add_all((talk, vote))
    db.session.commit()
    public_id = str(vote.public_id)

    resp = authenticated_client.post(
        f"/vote/cast/{vote.public_id}", data={"action": "vote", "value": 1}
    )

    assert resp.status_code == 302
    assert str(Vote.query.filter_by(value=1).first().public_id) == public_id


def test_choose_vote(*, authenticated_client: Client, user: User) -> None:
    """Test that votes are created correctly for a category."""
    talk1 = Talk(title="", length=1, is_anonymized=True)
    category1 = Category(name="1")
    category1.talks.append(talk1)

    talk2 = Talk(title="", length=1, is_anonymized=True)
    category2 = Category(name="2")
    category2.talks.append(talk2)

    db.session.add_all((talk1, talk2, category1, category2))
    db.session.commit()

    resp = authenticated_client.get(f"/vote/category/{category2.category_id}")

    vote = Vote.query.filter_by(talk_id=2).first()
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(f"/vote/cast/{vote.public_id}")
    assert Vote.query.filter_by(talk_id=1).count() == 0
    assert Vote.query.filter_by(talk_id=2).count() == 1


def test_vote_balance(*, authenticated_client: Client, user: User) -> None:
    """Test that votes are balanced correctly for a category."""
    talk1 = Talk(title="", length=1, is_anonymized=True)
    talk2 = Talk(title="", length=1, is_anonymized=True)
    category = Category(name="")
    vote1 = Vote(talk=talk1, user=user, value=1, skipped=False)
    category.talks.append(talk1)
    category.talks.append(talk2)
    db.session.add_all((category, talk1, talk2, vote1))
    db.session.commit()

    resp = authenticated_client.get(f"/vote/category/{category.category_id}")

    vote2 = Vote.query.filter_by(talk_id=2).first()
    public_id = str(vote2.public_id)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(f"/vote/cast/{public_id}")
    assert Vote.query.count() == 2
    assert Vote.query.filter_by(talk_id=2).count() == 1


def test_vote_gating(*, authenticated_client: Client, user: User) -> None:
    """Test that votes are gated correctly for a category."""
    talk1 = Talk(title="", length=1, is_anonymized=True)
    talk2 = Talk(title="", length=1, is_anonymized=True)
    category = Category(name="")
    vote = Vote(talk=talk1, user=user)
    category.talks.append(talk1)
    category.talks.append(talk2)
    db.session.add_all((category, talk1, talk2, vote))
    db.session.commit()
    public_id = str(vote.public_id)

    resp = authenticated_client.get(f"/vote/category/{category.category_id}")

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(f"/vote/cast/{public_id}")
    assert Vote.query.count() == 1
    assert Vote.query.filter_by(talk_id=2).count() == 0
