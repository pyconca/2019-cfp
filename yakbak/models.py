"""
Database models for Yak-Bak.

Some style notes:

- Always name models with the singular noun for the data it contains,
  eg "User" not "Users"
- Always have an opaque primary key (usually an integer), even if a
  surrogate key seems like a good candidate (eg is unique, stable, etc)
- Always name the primary key "<tablename>_id"
- MyPy has some trouble understanding SQLAlchemy, so use `# type: ignore`
  on each model class, but do annotate each column with a type
- Always name foreign keys "<tablename>_id" (for whichever table they
  reference)
- For relationships, use ``back_populates`` rather than ``backref``, and
  explicitly configure the relationship on the other table as well. This
  gives us the ability to type annotate both sides.
- Include ``created`` and ``updated`` columns on all model tables. You can
  omit this on join tables.

"""
from datetime import datetime
from typing import Iterable
import logging

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import synonym


db = SQLAlchemy()
logger = logging.getLogger("models")


talk_speaker = db.Table(
    "talk_speaker",
    db.Column("talk_id", db.Integer, db.ForeignKey("talk.talk_id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("user.user_id"), primary_key=True),
)


class User(db.Model):  # type: ignore
    user_id: int = db.Column(db.Integer, primary_key=True)

    fullname: str = db.Column(db.String(256), nullable=False)
    email: str = db.Column(db.String(256), nullable=False, unique=True)

    talks: Iterable["Talk"] = db.relationship(
        "Talk", secondary=talk_speaker, back_populates="speakers")

    created = db.Column(db.TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated = db.Column(
        db.TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Flask-Social-Auth compatibility
    id: int = synonym("user_id")

    # Flask-Login compatibility
    def get_id(self) -> str:
        return str(self.user_id)

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_active(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False


class Talk(db.Model):  # type: ignore
    talk_id: int = db.Column(db.Integer, primary_key=True)

    speakers: Iterable[User] = db.relationship(
        "User", secondary=talk_speaker, back_populates="talks")

    # talk type = ...

    title: str = db.Column(db.String(512), nullable=False)
    overview: str = db.Column(db.String(1024), nullable=True)
    description: str = db.Column(db.Text, nullable=True)
    outline: str = db.Column(db.Text, nullable=True)

    created = db.Column(db.TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated = db.Column(
        db.TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
