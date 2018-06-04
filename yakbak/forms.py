from flask_wtf import FlaskForm
from wtforms.ext.sqlalchemy.orm import model_form, ModelConverter
from wtforms.fields import SelectField

from yakbak.models import db, Talk, User
from yakbak.types import Application


TalkForm = model_form(
    model=Talk,
    db_session=db.session,
    base_class=FlaskForm,
    exclude={"talk_id", "length", "speakers", "updated", "created"},
)


UserForm = model_form(
    model=User,
    db_session=db.session,
    base_class=FlaskForm,
    exclude={"user_id", "email", "talks", "created", "updated"},
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
