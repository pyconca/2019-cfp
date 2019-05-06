from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING
import os.path

# TODO: remove once https://github.com/python/typeshed/pull/2958 is merged
if TYPE_CHECKING:
    class DateTime: pass
else:
    from click.types import DateTime
import click

from yakbak.core import create_app
from yakbak.models import Conference, db, UsedMagicLink
from yakbak.settings import find_settings_file, load_settings_file


app = create_app(load_settings_file(find_settings_file()))


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
@click.argument("talk_lengths")
@click.argument("recording_release_url")
@click.argument("cfp_email")
@click.option("--proposals-begin", type=DateTime(), help="interpreted as UTC")
@click.option("--proposals-end", type=DateTime(), help="interpreted as UTC")
@click.option("--voting-begin", type=DateTime(), help="interpreted as UTC")
@click.option("--voting-end", type=DateTime(), help="interpreted as UTC")
def add_conference(
    full_name: str,
    informal_name: str,
    talk_lengths: str,
    recording_release_url: str,
    cfp_email: str,
    proposals_begin: Optional[datetime],
    proposals_end: Optional[datetime],
    voting_begin: Optional[datetime],
    voting_end: Optional[datetime],
) -> None:
    lengths = [int(l) for l in talk_lengths.split(",")]
    conf = Conference(
        full_name=full_name,
        informal_name=informal_name,
        talk_lengths=lengths,
        recording_release_url=recording_release_url,
        cfp_email=cfp_email,
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
    UsedMagicLink.query.filter(
        UsedMagicLink.used_on <= threshold,
    ).delete()
    db.session.commit()
