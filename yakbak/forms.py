from typing import Any, Iterable, List, Optional, Tuple
import enum

from bunch import Bunch
from flask import g
from flask_wtf import FlaskForm
from jinja2.utils import Markup
from wtforms import Form
from wtforms.fields import (
    Field,
    IntegerField,
    RadioField,
    SelectField,
    SelectMultipleField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, InputRequired, NoneOf
from wtforms.validators import Optional as OptionalValidator
from wtforms.validators import ValidationError
from wtforms.widgets import HiddenInput, html_params
from wtforms_alchemy import model_form_factory

from yakbak.models import (
    AgeGroup,
    Category,
    DemographicSurvey,
    Ethnicity,
    Gender,
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
        return iter(
            [(length, f"{length} Minutes") for length in g.conference.talk_lengths]
        )


class TalkForm(ModelForm):
    class Meta:
        model = Talk

    length = SelectField(
        coerce=int, choices=TalkLengthChoices(), validators=[DataRequired()]
    )


class VoteForm(FlaskForm):
    VOTE_VALUE_CHOICES = {
        1: "Definitely yes!",
        0: "I'm impartial.",
        -1: "Definitely not.",
    }

    action = StringField()
    value = RadioField(
        choices=list(VOTE_VALUE_CHOICES.items()),
        coerce=int,
        validators=[OptionalValidator()],
    )

    def validate(self) -> bool:
        """Validate that a value is provided if the actions is vote."""
        if not super().validate():
            return False

        if self.action.data not in ("skip", "vote"):
            self.action.errors.append("Action must be vote or skip.")
            return False

        if self.action.data == "vote" and self.value.data is None:
            self.value.errors.append("Please cast a vote.")
            return False

        return True


class ConductReportForm(FlaskForm):
    """Information required for a code of conduct report."""

    ANONYMOUS_CHOICES = (
        (1, "I wish to remain anonymous."),
        (
            0,
            " ".join(
                (
                    "Share my identity with the code of conduct team.",
                    "It will not be shared with anyone else.",
                )
            ),
        ),
    )

    talk_id = IntegerField(widget=HiddenInput())
    text = TextAreaField(
        "Please describe why this talk may violate the code of conduct.",
        validators=[InputRequired()],
    )
    anonymous = RadioField(
        choices=ANONYMOUS_CHOICES, coerce=lambda data: bool(int(data))
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
        validator = NoneOf(self.excluded_emails, message="Already a speaker")
        validator(self, field)


class PastSpeaking(enum.Enum):
    NEVER = "I have never spoken at a conference before"
    PYGOTHAM = "I have spoken at PyGotham in the past"
    OTHER_PYTHON = "I have spoken at another Python-related conference in the past"
    OTHER_NONPYTHON = (
        "I have spoken at another non-Python-related conference in the past"
    )


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
        options = dict(
            kwargs, type="checkbox", name=field.name, value=value, id=field_id
        )
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
            kwargs, type="text", name=field.name, value=other_value, id=other_id
        )
        html.append(f'<li class="other"><label for="{field_id}">{label}:</label> ')
        html.append("<input %s /></li>" % html_params(**options))

    html.append("</ul>")
    return Markup("".join(html))


class SelectMultipleOrOtherField(SelectMultipleField):
    def __init__(self, choices: FormChoices, **kwargs: Any):
        super().__init__(choices=choices, widget=select_multi_checkbox, **kwargs)

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
        "age_group", choices=enum_choices(AgeGroup), validators=[OptionalValidator()]
    )
    programming_experience = RadioField(
        "programming_experience",
        choices=enum_choices(ProgrammingExperience),
        validators=[OptionalValidator()],
    )

    def __init__(self, obj: DemographicSurvey):
        # make a fake obj to pass in that adapts the enum values to their
        # names which the select fields are more happy to work with
        data = dict(
            (col.name, getattr(obj, col.name, None)) for col in obj.__table__.columns
        )
        if data["age_group"]:
            data["age_group"] = data["age_group"].name
        if data["programming_experience"]:
            data["programming_experience"] = data["programming_experience"].name

        # unfortunately, the obj must be a thing that supports attribute
        # access, so use a bunch (see https://github.com/dsc/bunch)
        super().__init__(obj=Bunch(data))

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
                obj.programming_experience = ProgrammingExperience[
                    self.programming_experience.data
                ]


class CategoryChoices:
    """
    Defer the determination of choices for categories to runtime.

    Because each conference might have different talk lengths, we can't
    pre-define the choices in the way WTF usually wants for a select field,
    so we use this trickery instead.
    """

    def __iter__(self) -> Iterable[Tuple[int, str]]:
        return iter(
            [
                (category.category_id, category.name)
                for category in Category.query.order_by(Category.name).all()
            ]
        )


class CategorizeForm(FlaskForm):
    category_ids = SelectMultipleField(
        coerce=int, choices=CategoryChoices(), widget=select_multi_checkbox
    )

    def validate_category_ids(self, field: Field) -> None:
        if len(field.data) > 2:
            raise ValidationError("You may pick up to 2 categories")
