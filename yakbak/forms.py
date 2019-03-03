from typing import Iterable, Tuple

from flask import g
from flask_wtf import FlaskForm
from wtforms.fields import Field, SelectField, StringField
from wtforms.validators import DataRequired, Email, NoneOf
from wtforms_alchemy import model_form_factory

from yakbak.models import Talk, User


ModelForm = model_form_factory(FlaskForm)  # type: FlaskForm


class TalkLengthChoices:
    """
    Defer the determination of choices for talk lengths to runtime.

    Because each conference might have different talk lengths, we can't
    pre-define the choices in the way WTF usually wants for a select field,
    so we use this trickery instead.
    """
    def __iter__(self) -> Iterable[Tuple[int, str]]:
        return iter([
            (length, f"{length} Minutes")
            for length in g.conference.talk_lengths
        ])


class TalkForm(ModelForm):
    class Meta:
        model = Talk

    length = SelectField(
        coerce=int,
        choices=TalkLengthChoices(),
        validators=[DataRequired()],
    )


class UserForm(ModelForm):
    class Meta:
        model = User
        exclude = {"email"}


class EmailAddressForm(FlaskForm):
    email = StringField(validators=[Email()])


class SpeakerEmailForm(EmailAddressForm):

    def __init__(self, excluded_emails: Iterable[str]) -> None:
        self.excluded_emails = excluded_emails
        super().__init__()

    def validate_email(self, field: Field) -> None:
        validator = NoneOf(
            self.excluded_emails,
            message="Already a speaker",
        )
        validator(self, field)
