import os.path

import click

from yakbak.core import create_app
from yakbak.models import Conference, db
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
def add_conference(full_name: str, informal_name: str, talk_lengths: str) -> None:
    lengths = [int(l) for l in talk_lengths.split(",")]
    conf = Conference(
        full_name=full_name,
        informal_name=informal_name,
        talk_lengths=lengths,
    )
    db.session.add(conf)
    db.session.commit()
