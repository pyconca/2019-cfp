from datetime import datetime, timedelta
from typing import Optional

from werkzeug.test import Client
import pytest

from yakbak.models import Category, Conference, db, Talk, User, Vote
from yakbak.tests.util import assert_html_response_contains
from yakbak.types import Application


@pytest.fixture(autouse=True)
def enable_talk_review(app: Application) -> None:
    """Enable talk review for the test conference."""
    conference = Conference.query.first()
    conference.review_begin = datetime.utcnow() - timedelta(days=1)
    conference.review_end = datetime.utcnow() + timedelta(days=2)
    db.session.commit()


@pytest.mark.parametrize(
    "vote_value,skipped,vote_note",
    (
        (1, False, "You voted: Definitely yes!"),
        (0, False, "You voted: I&#39;m impartial."),
        (-1, False, "You voted: Definitely not."),
        (None, True, "You skipped voting on this talk."),
        (None, False, "You did not vote on this talk."),
    ),
)
def test_vote_review_shows_your_vote_and_conduct_form(
    *,
    vote_value: Optional[int],
    skipped: bool,
    vote_note: str,
    authenticated_client: Client,
    user: User,
) -> None:
    """Show the user's vote results, if present, and the conduct report form."""
    talk = Talk(
        title="",
        length=1,
        is_anonymized=True,
        anonymized_title="",
        anonymized_description="",
        anonymized_outline="",
        anonymized_take_aways="",
    )
    conference = Conference.query.first()
    category = Category(name="", conference=conference)
    category.talks.append(talk)
    db.session.add_all((category, talk))
    if vote_value is not None:
        vote = Vote(talk=talk, user=user, value=vote_value, skipped=False)
        db.session.add(vote)
    elif skipped:
        vote = Vote(talk=talk, user=user, value=None, skipped=True)
        db.session.add(vote)
    db.session.commit()

    resp = authenticated_client.get(f"/review/{talk.talk_id}")
    assert_html_response_contains(resp, vote_note)
    assert_html_response_contains(resp, '<form method="POST" action="/conduct-report">')
