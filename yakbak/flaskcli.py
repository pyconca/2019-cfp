from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING
from urllib.parse import urlparse
import csv
import os.path
import sys

from flask import url_for
import click

from yakbak.core import create_app
from yakbak.models import Category, Conference, db, UsedMagicLink, TalkSpeaker, Talk
from yakbak.settings import find_settings_file, load_settings_from_env

# TODO: remove once https://github.com/python/typeshed/pull/2958 is merged
if TYPE_CHECKING:

    class DateTime:
        pass


else:
    from click.types import DateTime


app = create_app(load_settings_from_env())


@app.cli.command()
def sync_db() -> None:
    here = os.path.dirname(__file__)
    root = os.path.join(here, "..")
    alembic_ini = os.path.abspath(os.path.join(root, "alembic.ini"))

    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config(alembic_ini)
    command.upgrade(alembic_cfg, "head")

    # Social-Auth needs to have the User model already in existence,
    # so do this second to creating the yakbak-specific models
    from social_flask_sqlalchemy import models

    models.PSABase.metadata.create_all(db.engine)


@app.cli.command()
@click.argument("full_name")
@click.argument("informal_name")
@click.argument("website")
@click.argument("talk_lengths")
@click.argument("recording_release_url")
@click.argument("cfp_email")
@click.argument("twitter_username")
@click.argument("conduct_email")
@click.option("--proposals-begin", type=DateTime(), help="interpreted as UTC")
@click.option("--proposals-end", type=DateTime(), help="interpreted as UTC")
@click.option("--voting-begin", type=DateTime(), help="interpreted as UTC")
@click.option("--voting-end", type=DateTime(), help="interpreted as UTC")
def add_conference(
    full_name: str,
    informal_name: str,
    website: str,
    talk_lengths: str,
    recording_release_url: str,
    cfp_email: str,
    twitter_username: str,
    conduct_email: str,
    proposals_begin: Optional[datetime],
    proposals_end: Optional[datetime],
    voting_begin: Optional[datetime],
    voting_end: Optional[datetime],
) -> None:
    # TODO: Remove this check once multiple conferences are supported.
    if db.session.query(Conference.query.exists()).scalar():
        print("WARNING: Adding a second conference is not supported at this time.")
        sys.exit(1)
    if twitter_username.startswith("@"):
        print("Twitter username should not start with '@'")
        sys.exit(1)

    lengths = [int(l) for l in talk_lengths.split(",")]
    conf = Conference(
        full_name=full_name,
        informal_name=informal_name,
        website=website,
        talk_lengths=lengths,
        recording_release_url=recording_release_url,
        cfp_email=cfp_email,
        twitter_username=twitter_username,
        conduct_email=conduct_email,
        proposals_begin=proposals_begin,
        proposals_end=proposals_end,
        voting_begin=voting_begin,
        voting_end=voting_end,
    )
    db.session.add(conf)
    db.session.commit()


@app.cli.command()
@click.argument("older_than_days")
def clean_magic_links(older_than_days: str) -> None:
    now = datetime.utcnow()
    threshold = now - timedelta(days=int(older_than_days))
    UsedMagicLink.query.filter(UsedMagicLink.used_on <= threshold).delete()
    db.session.commit()


@app.cli.command()
@click.option("--base-url", type=str, help="Root URL of the Yak-Bak instance")
def export_review_spreadsheet(base_url: Optional[str]) -> None:
    """
    Prepare CSV files for program committee review.

    Each file is named after a category, and contains a row for each talk in
    that category. Each row contains fields for talk ID, title, length, a link
    to review the proposal, and a summary of votes.

    The CSV is written to stdout.

    """

    if base_url is not None:
        parsed = urlparse(base_url)
        app.config["PREFERRED_URL_SCHEME"] = parsed.scheme
        app.config["SERVER_NAME"] = parsed.netloc

    writer = csv.writer(sys.stdout)
    writer.writerow(
        [
            "Talk ID",
            "Title",
            "Length",
            "Link",
            "Speakers",
            "Category",
            "Vote Count",
            "Vote Score",
        ]
    )
    with app.test_request_context():
        for talk in Talk.query.all():
            talk_speakers = (
                TalkSpeaker.query
                .filter(TalkSpeaker.talk_id==str(talk.talk_id))
                .all()
            )

            url = url_for(
                "views.review_talk",
                talk_id=talk.talk_id,
                _external=(base_url is not None),
            )

            writer.writerow(
                [
                    str(talk.talk_id),
                    talk.title,
                    str(talk.length),
                    ' // '.join(ts.user.fullname for ts in talk_speakers),
                    ' // '.join(ts.user.email for ts in talk_speakers),
                    ' // '.join(c.name for c in talk.categories),
                    f"https://cfp.pycon.ca{url}",
                    f"{talk.vote_count:.2f}" if talk.vote_count else None,
                    f"{talk.vote_score:.2f}" if talk.vote_score else None,
                ]
            )
