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
from typing import List, Optional
import enum
import logging

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import synonym
from sqlalchemy.types import Enum, JSON
from sqlalchemy_postgresql_json import JSONMutableList


db = SQLAlchemy()
logger = logging.getLogger("models")


class InvitationStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    DELETED = "deleted"


class Conference(db.Model):  # type: ignore
    conference_id: int = db.Column(db.Integer, primary_key=True)

    full_name: str = db.Column(db.String(256), nullable=False)
    informal_name: str = db.Column(db.String(256), nullable=False)

    talk_lengths: List[int] = db.Column(
        JSONMutableList.as_mutable(JSON),
        nullable=False,
    )

    recording_release_url: str = db.Column(db.String(1024), nullable=False)
    cfp_email: str = db.Column(db.String(256), nullable=False)

    created = db.Column(db.TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated = db.Column(
        db.TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(db.Model):  # type: ignore
    user_id: int = db.Column(db.Integer, primary_key=True)

    fullname: str = db.Column(db.String(256), nullable=False)
    email: str = db.Column(db.String(256), nullable=False, unique=True)

    speaker_bio: str = db.Column(db.Text, nullable=True)

    site_admin: bool = db.Column(
        db.Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    created = db.Column(db.TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated = db.Column(
        db.TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Flask-Social-Auth compatibility
    id: int = synonym("user_id")

    def __str__(self) -> str:
        return f"{self.fullname} ({self.email})"

    # Flask-Admin compatibility
    @property
    def is_site_admin(self) -> bool:
        return self.site_admin

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

    # talk type = ...

    title: str = db.Column(db.String(512), nullable=False)
    length: int = db.Column(db.Integer, nullable=False)
    description: Optional[str] = db.Column(db.Text)
    outline: Optional[str] = db.Column(db.Text)
    requirements: Optional[str] = db.Column(db.Text)
    take_aways: Optional[str] = db.Column(db.Text)

    accepted_recording_release: bool = db.Column(db.Boolean)

    created = db.Column(db.TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated = db.Column(
        db.TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __str__(self) -> str:
        return self.title

    def add_speaker(self, speaker: User, state: InvitationStatus) -> None:
        ts = TalkSpeaker(state=state)
        ts.talk = self
        ts.user = speaker
        self.speakers.append(ts)


class TalkSpeaker(db.Model):  # type: ignore
    talk_id = db.Column(db.Integer, db.ForeignKey("talk.talk_id"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), primary_key=True)
    state = db.Column(Enum(InvitationStatus), nullable=False)

    talk = db.relationship("Talk", backref=db.backref("speakers"))
    user = db.relationship("User", backref=db.backref("talks"))

    created = db.Column(db.TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated = db.Column(
        db.TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgeGroup(enum.Enum):
    UNDER_18 = "Under 18"
    UNDER_25 = "18 - 24"
    UNDER_35 = "25 - 34"
    UNDER_45 = "35 - 44"
    UNDER_55 = "45 - 54"
    UNDER_65 = "55 - 64"
    OVER_65 = "65 or older"


class ProgrammingExperience(enum.Enum):
    UNDER_1YR = "Under 1 year"
    UNDER_3YR = "1 - 2 years"
    UNDER_6YR = "3 - 5 years"
    UNDER_10YR = "6 - 9 years"
    UNDER_20YR = "10 - 20 years"
    OVER_20YR = "20 years or more"


class DemographicSurvey(db.Model):  # type: ignore
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), primary_key=True)
    user = db.relationship(
        "User",
        backref=db.backref("demographic_survey", uselist=False),
    )

    # These fields are multi-select fields, some with "other" options;
    # the choices are defined in the DemographicSurveyForm in forms.py
    gender: Optional[List[str]] = db.Column(JSONMutableList.as_mutable(JSON))
    ethnicity: Optional[List[str]] = db.Column(JSONMutableList.as_mutable(JSON))
    past_speaking: Optional[List[str]] = db.Column(JSONMutableList.as_mutable(JSON))

    # These fields are single-select and have choices defined above
    age_group: Optional[AgeGroup] = db.Column(Enum(AgeGroup))
    programming_experience: Optional[ProgrammingExperience] = db.Column(Enum(ProgrammingExperience))  # noqa: E501

    created = db.Column(db.TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated = db.Column(
        db.TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def clear(self) -> None:
        self.gender = None
        self.ethnicity = None
        self.past_speaking = None
        self.age_group = None
        self.programming_experience = None


class UsedMagicLink(db.Model):  # type: ignore
    token: str = db.Column(db.String(512), primary_key=True)

    used_on: datetime = db.Column(
        db.TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
