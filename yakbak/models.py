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

from attr import attrib, attrs
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Query, synonym
from sqlalchemy.types import Enum, JSON
from sqlalchemy_postgresql_json import JSONMutableList

db = SQLAlchemy()
logger = logging.getLogger("models")


class InvitationStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    DELETED = "deleted"


class TalkStatus(enum.Enum):
    PROPOSED = "proposed"
    WITHDRAWN = "withdrawn"
    # REJECTED = "rejected"
    # ACCEPTED = "deleted"
    # CONFIRMED = "confirmed"
    # WAITLISTED = "waitlisted"


@attrs
class TimeWindow:
    start: datetime = attrib()
    end: datetime = attrib()

    def includes_now(self) -> bool:
        now = datetime.utcnow()
        return self.start <= now <= self.end

    def after_now(self) -> bool:
        now = datetime.utcnow()
        return now < self.start


class Conference(db.Model):  # type: ignore
    conference_id: int = db.Column(db.Integer, primary_key=True)

    full_name: str = db.Column(db.String(256), nullable=False)
    informal_name: str = db.Column(db.String(256), nullable=False)
    website: str = db.Column(db.String(512), nullable=False)

    talk_lengths: List[int] = db.Column(
        JSONMutableList.as_mutable(JSON), nullable=False
    )

    recording_release_url: str = db.Column(db.String(1024), nullable=False)
    cfp_email: str = db.Column(db.String(256), nullable=False)

    # Proposals window -- populate with naive datetimes in UTC
    proposals_begin: datetime = db.Column(db.DateTime)
    proposals_end: datetime = db.Column(db.DateTime)

    # Voting window -- populate with naive datetimes in UTC
    voting_begin: datetime = db.Column(db.DateTime)
    voting_end: datetime = db.Column(db.DateTime)

    created = db.Column(db.TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated = db.Column(
        db.TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "(proposals_begin IS NOT NULL and proposals_end IS NOT NULL) "
            "OR (proposals_begin IS NULL AND proposals_end IS NULL)",
            name="ck_proposals_window",
        ),
        CheckConstraint(
            "(voting_begin IS NOT NULL and voting_end IS NOT NULL) "
            "OR (voting_begin IS NULL AND voting_end IS NULL)",
            name="ck_voting_window",
        ),
    )

    @property
    def proposal_window(self) -> Optional[TimeWindow]:
        if self.proposals_begin and self.proposals_end:
            return TimeWindow(self.proposals_begin, self.proposals_end)
        return None

    @property
    def voting_window(self) -> Optional[TimeWindow]:
        if self.voting_begin and self.voting_end:
            return TimeWindow(self.voting_begin, self.voting_end)
        return None

    @property
    def creating_proposals_allowed(self) -> bool:
        # TODO: stop considering proposals open if there is no window,
        # but want to be cautious about installs that might not have
        # updated their windows yet
        return self.proposal_window is None or self.proposal_window.includes_now()

    @property
    def editing_proposals_allowed(self) -> bool:
        # TODO: allow edits to accepted talks after proposal and voting windows
        return self.creating_proposals_allowed and not self.voting_allowed

    @property
    def voting_allowed(self) -> bool:
        return self.voting_window is not None and self.voting_window.includes_now()

    @property
    def voting_window_after_now(self) -> bool:
        return self.voting_window is not None and self.voting_window.after_now()


class User(db.Model):  # type: ignore
    user_id: int = db.Column(db.Integer, primary_key=True)

    fullname: str = db.Column(db.String(256), nullable=False)
    email: str = db.Column(db.String(256), nullable=False, unique=True)

    twitter_username: str = db.Column(db.String(15), nullable=True)
    speaker_bio: str = db.Column(db.Text, nullable=True)

    site_admin: bool = db.Column(
        db.Boolean, default=False, server_default="false", nullable=False
    )

    created = db.Column(db.TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated = db.Column(
        db.TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

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


class TalkCategory(db.Model):  # type: ignore
    talk_id = db.Column(db.Integer, db.ForeignKey("talk.talk_id"), primary_key=True)
    category_id = db.Column(
        db.Integer, db.ForeignKey("category.category_id"), primary_key=True
    )


class Category(db.Model):  # type: ignore
    category_id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(64), nullable=False, unique=True)

    talks = db.relationship("Talk", secondary=TalkCategory.__table__)

    def __str__(self) -> str:
        return self.name


class Talk(db.Model):  # type: ignore
    talk_id: int = db.Column(db.Integer, primary_key=True)
    state: TalkStatus = db.Column(
        Enum(TalkStatus), server_default=TalkStatus.PROPOSED.name
    )

    title: str = db.Column(db.String(512), nullable=False)
    length: int = db.Column(db.Integer, nullable=False)
    description: Optional[str] = db.Column(db.Text)
    outline: Optional[str] = db.Column(db.Text)
    requirements: Optional[str] = db.Column(db.Text)
    take_aways: Optional[str] = db.Column(db.Text)

    # anonymization support
    is_anonymized: bool = db.Column(
        db.Boolean, nullable=False, default=False, server_default="false"
    )
    has_anonymization_changes: bool = db.Column(
        db.Boolean, nullable=False, default=False, server_default="false"
    )
    anonymized_title: Optional[str] = db.Column(db.String(512))
    anonymized_description: Optional[str] = db.Column(db.Text)
    anonymized_outline: Optional[str] = db.Column(db.Text)

    accepted_recording_release: bool = db.Column(db.Boolean)

    categories = db.relationship("Category", secondary=TalkCategory.__table__)

    created = db.Column(db.TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated = db.Column(
        db.TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __str__(self) -> str:
        return self.title

    @classmethod
    def active(cls) -> Query:
        return cls.query.filter(cls.state != TalkStatus.WITHDRAWN)

    def add_speaker(self, speaker: User, state: InvitationStatus) -> None:
        ts = TalkSpeaker(state=state)
        ts.talk = self
        ts.user = speaker
        self.speakers.append(ts)

    def reset_after_edits(self) -> None:
        # prompt admins to re-categorize
        del self.categories[:]

        # prompt admins to re-anonymize
        self.is_anonymized = False
        self.anonymized_title = None
        self.anonymized_description = None
        self.anonymized_outline = None
        self.has_anonymization_changes = False


class TalkSpeaker(db.Model):  # type: ignore
    talk_id = db.Column(db.Integer, db.ForeignKey("talk.talk_id"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), primary_key=True)
    state = db.Column(Enum(InvitationStatus), nullable=False)

    talk = db.relationship("Talk", backref=db.backref("speakers"))
    user = db.relationship("User", backref=db.backref("talks"))

    created = db.Column(db.TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated = db.Column(
        db.TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Gender(enum.Enum):
    WOMAN = "Woman"
    MAN = "Man"
    NONBINARY = "Non-binary / third gender person"
    OTHER = "Other"


class Ethnicity(enum.Enum):
    ASIAN = "Asian"
    BLACK_AFRICAN_AMERICAN = "Black / African-American"
    HISPANIC_LATINX = "Hispanic / Latinx"
    NATIVE_AMERICAN = "Native American"
    PACIFIC_ISLANDER = "Pacific Islander"
    WHITE_CAUCASIAN = "White / Caucasian"
    OTHER = "Other"


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
        "User", backref=db.backref("demographic_survey", uselist=False)
    )

    # These fields are multi-select fields, some with "other" options;
    # the choices are defined in the DemographicSurveyForm in forms.py
    gender: Optional[List[str]] = db.Column(JSONMutableList.as_mutable(JSON))
    ethnicity: Optional[List[str]] = db.Column(JSONMutableList.as_mutable(JSON))
    past_speaking: Optional[List[str]] = db.Column(JSONMutableList.as_mutable(JSON))

    # These fields are single-select and have choices defined above
    age_group: Optional[AgeGroup] = db.Column(Enum(AgeGroup))
    programming_experience: Optional[ProgrammingExperience] = db.Column(
        Enum(ProgrammingExperience)
    )

    created = db.Column(db.TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated = db.Column(
        db.TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def clear(self) -> None:
        self.gender = None
        self.ethnicity = None
        self.past_speaking = None
        self.age_group = None
        self.programming_experience = None

    def doesnt_have_gender(self, gender: Gender) -> bool:
        if not self.gender:
            return False
        return gender.name not in self.gender

    def doesnt_have_ethnicity(self, ethnicity: Ethnicity) -> bool:
        if not self.ethnicity:
            return False
        return ethnicity.name not in self.ethnicity


class UsedMagicLink(db.Model):  # type: ignore
    token: str = db.Column(db.String(512), primary_key=True)

    used_on: datetime = db.Column(
        db.TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
