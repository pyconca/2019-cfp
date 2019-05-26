"""Test voting functionality."""

from datetime import datetime, timedelta
from typing import Optional
from unittest.mock import Mock

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


def test_choose_vote(
    *, authenticated_client: Client, conference: Conference, user: User
) -> None:
    """Test that votes are created correctly for a category."""
    talk1 = Talk(title="", length=1, is_anonymized=True)
    category1 = Category(conference=conference, name="1")
    category1.talks.append(talk1)

    talk2 = Talk(title="", length=1, is_anonymized=True)
    category2 = Category(conference=conference, name="2")
    category2.talks.append(talk2)

    db.session.add_all((talk1, talk2, category1, category2))
    db.session.commit()

    resp = authenticated_client.get(f"/vote/category/{category2.category_id}")

    vote = Vote.query.filter_by(talk_id=2).first()
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(f"/vote/cast/{vote.public_id}")
    assert Vote.query.filter_by(talk_id=1).count() == 0
    assert Vote.query.filter_by(talk_id=2).count() == 1


def test_vote_balance(
    *, authenticated_client: Client, conference: Conference, user: User
) -> None:
    """Test that votes are balanced correctly for a category."""
    talk1 = Talk(title="", length=1, is_anonymized=True)
    talk2 = Talk(title="", length=1, is_anonymized=True)
    category = Category(conference=conference, name="")
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


def test_vote_gating(
    *, authenticated_client: Client, conference: Conference, user: User
) -> None:
    """Test that votes are gated correctly for a category."""
    talk1 = Talk(title="", length=1, is_anonymized=True)
    talk2 = Talk(title="", length=1, is_anonymized=True)
    category = Category(conference=conference, name="")
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


@pytest.mark.parametrize(
    "category_name,commit,ending_count",
    (
        ("Second Category", True, 1),
        (None, True, 0),
        ("Second Category", False, 2),
        (None, False, 2),
    ),
)
def test_clear_skipped_votes(
    *,
    category_name: Optional[str],
    commit: bool,
    conference: Conference,
    ending_count: int,
    user: User,
) -> None:
    """Test that skipped votes can be cleared for a uesr."""
    talk1 = Talk(title="", length=1, is_anonymized=True)
    talk2 = Talk(title="", length=1, is_anonymized=True)
    category1 = Category(conference=conference, name="First Category")
    category2 = Category(conference=conference, name="Second Category")
    vote1 = Vote(talk=talk1, user=user, skipped=True)
    vote2 = Vote(talk=talk2, user=user, skipped=True)
    category1.talks.append(talk1)
    category2.talks.append(talk2)
    db.session.add_all((category1, category2, talk1, talk2, vote1, vote2))
    db.session.commit()

    # Choose the category to delete skipped votes from based on the
    # provided category name.
    if category_name is None:
        target_category = None
    else:
        target_category = Category.query.filter_by(name=category_name).first()

    # Clear the skipped votes as configured.
    Vote.clear_skipped(category=target_category, commit=commit, user=user)

    # Rollback the session to clear any uncommitted changes.
    db.session.rollback()

    # Check for the desired skipped vote count.
    assert Vote.query.count() == ending_count
