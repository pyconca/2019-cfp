import os.path

from yakbak.core import create_app
from yakbak.models import db
from yakbak.settings import find_settings_file, load_settings_file


app = create_app(load_settings_file(find_settings_file()))


@app.cli.command()
def sync_db() -> None:
    from social_flask_sqlalchemy import models
    models.PSABase.metadata.create_all(db.engine)

    here = os.path.dirname(__file__)
    root = os.path.join(here, "..")
    alembic_ini = os.path.abspath(os.path.join(root, "alembic.ini"))

    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config(alembic_ini)
    command.upgrade(alembic_cfg, "head")
