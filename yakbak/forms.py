from typing import Any

from flask_wtf import FlaskForm
from wtforms import Form
from wtforms.ext.sqlalchemy.orm import model_form
from wtforms.fields import StringField
from wtforms.validators import Email

from yakbak.models import Conference, db, Talk, User


_TalkForm: Form = model_form(
    model=Talk,
    db_session=db.session,
    base_class=FlaskForm,
    exclude={"talk_id", "speakers", "updated", "created"},
)


class TalkForm(_TalkForm):
    def __init__(self, conference: Conference, *args: Any, **kwargs: Any) -> None:
        self.length.choices = [
            (length, f"{length} Minutes")
            for length in conference.talk_lengths
        ]
        super().__init__(*args, **kwargs)


UserForm = model_form(
    model=User,
    db_session=db.session,
    base_class=FlaskForm,
    exclude={"user_id", "email", "talks", "created", "updated"},
)


class MagicLinkForm(FlaskForm):
    email = StringField(validators=[Email()])
