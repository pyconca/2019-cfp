from typing import Any, Iterable, List, Optional, Tuple
import enum

from flask import g
from flask_wtf import FlaskForm
from jinja2.utils import Markup
from wtforms import Form
from wtforms.fields import (
    Field,
    RadioField,
    SelectField,
    SelectMultipleField,
    StringField,
)
from wtforms.validators import DataRequired, Email, NoneOf, Optional as OptionalValidator
from wtforms.widgets import html_params
from wtforms_alchemy import model_form_factory

from yakbak.models import (
    AgeGroup,
    DemographicSurvey,
    ProgrammingExperience,
    Talk,
    User,
)


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


class PastSpeaking(enum.Enum):
    NEVER = "I have never spoken at a conference before"
    PYGOTHAM = "I have spoken at PyGotham in the past"
    OTHER_PYTHON = "I have spoken at another Python-related conference in the past"
    OTHER_NONPYTHON = "I have spoken at another non-Python-related conference in the past"


FormChoices = Iterable[Tuple[str, str]]


def enum_choices(an_enum: Iterable[enum.Enum]) -> FormChoices:
    return [(choice.name, choice.value) for choice in an_enum]


def select_multi_checkbox(field: Field, **kwargs: Any) -> str:
    html = ["<ul {}>".format(html_params(id=field.id, class_="multi-select"))]
    show_other = False
    for value, label, _ in field.iter_choices():
        if value == "OTHER":
            show_other = True
            continue

        field_id = f"{field.id}-{value}"
        options = dict(kwargs, type="checkbox", name=field.name, value=value, id=field_id)
        if value in (field.data or ()):
            options["checked"] = "checked"
        html.append("<li><input %s /> " % html_params(**options))
        html.append('<label for="%s">%s</label></li>' % (field_id, label))

    if show_other:
        data = field.data or ()
        all_choices = set(value for value, _, _ in field.iter_choices())
        other_value = [v for v in data if v not in all_choices]
        other_value = other_value[0] if other_value else ""
        other_id = f"{field_id}-{value}"
        options = dict(
            kwargs,
            type="text",
            name=field.name,
            value=other_value,
            id=other_id,
        )
        html.append(f'<li class="other"><label for="{field_id}">{label}:</label> ')
        html.append("<input %s /></li>" % html_params(**options))

    html.append("</ul>")
    return Markup("".join(html))


class SelectMultipleOrOtherField(SelectMultipleField):
    def __init__(self, choices: FormChoices, **kwargs: Any):
        super().__init__(
            choices=choices,
            widget=select_multi_checkbox,
            **kwargs,
        )

    def process_formdata(self, valuelist: List[Any]) -> None:
        # no validation, the value will go in "other"
        self.data = list(self.coerce(x) for x in valuelist)

    def pre_validate(self, form: Form) -> None:
        # no validation, the value will go in "other"
        pass


class DemographicSurveyForm(FlaskForm):
    gender = SelectMultipleOrOtherField(choices=enum_choices(Gender))
    ethnicity = SelectMultipleOrOtherField(choices=enum_choices(Ethnicity))
    past_speaking = SelectMultipleOrOtherField(choices=enum_choices(PastSpeaking))

    age_group = RadioField(
        "age_group",
        choices=enum_choices(AgeGroup),
        validators=[OptionalValidator()],
    )
    programming_experience = RadioField(
        "programming_experience",
        choices=enum_choices(ProgrammingExperience),
        validators=[OptionalValidator()],
    )

    def __init__(self, obj: DemographicSurvey):
        # do this before calling super __init__, since we don't want
        # to overwrite values that __init__ parses from the request
        if obj.age_group:
            self.age_group.data = obj.age_group.name
        if obj.programming_experience:
            self.programming_experience.data = obj.programming_experience.name

        super().__init__(obj=obj)

    def populate_obj(self, obj: DemographicSurvey) -> None:
        # all sorts of weird hackery because I can't figure out how to make
        # wtforms work well with enums right now, and the CFP start date
        # is looming. see https://gitlab.com/bigapplepy/yak-bak/issues/22
        def clean_list(values: Optional[List[str]]) -> Optional[List[str]]:
            if values:
                values = [v for v in values if v]
            return values or None

        obj.gender = clean_list(self.gender.data)
        obj.ethnicity = clean_list(self.ethnicity.data)
        obj.past_speaking = clean_list(self.past_speaking.data)

        if self.age_group.data:
            if self.age_group.data == "None":
                obj.age_group = None
            else:
                obj.age_group = AgeGroup[self.age_group.data]
        if self.programming_experience.data:
            if self.programming_experience.data == "None":
                obj.programming_experience = None
            else:
                obj.programming_experience = ProgrammingExperience[self.programming_experience.data]  # noqa: E501
