from flask_wtf import FlaskForm
from wtforms.ext.sqlalchemy.orm import model_form, ModelConverter
from wtforms.fields import SelectField

from yakbak.types import Application
from yakbak.models import db, Talk


class ModelConverterWithDoc(ModelConverter):

    """
    Use the ``doc`` attribute of SQLAlchemy columns for WTForms description.

    """

    def convert(self, model, mapper, prop, field_args, db_session=None):  # type: ignore
        field = super().convert(model, mapper, prop, field_args, db_session)
        if prop.doc:
            field.kwargs["description"] = prop.doc
        return field


TalkForm = model_form(
    model=Talk,
    db_session=db.session,
    base_class=FlaskForm,
    exclude={"talk_id", "length", "speakers", "updated", "created"},
    converter=ModelConverterWithDoc(),
)


def init_forms(app: Application) -> None:
    # Add "length" (talk length) field during app initialization
    # since its values depend on settings not know at module-time
    TalkForm.length = SelectField(
        choices=[
            (length, f"{length} Minutes")
            for length in app.settings.cfp.talk_lengths
        ],
        coerce=int,
    )
