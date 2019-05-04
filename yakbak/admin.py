from typing import Any

from bunch import Bunch
from flask import abort, Blueprint, flash, g, redirect, render_template, request, url_for
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib import sqla
from sqlalchemy import func, not_
from sqlalchemy.orm import joinedload
from werkzeug import Response

from yakbak import mail
from yakbak.forms import CategorizeForm, TalkForm
from yakbak.models import (
    Category,
    Conference,
    db,
    DemographicSurvey,
    Ethnicity,
    Gender,
    InvitationStatus,
    Talk,
    User,
)


app = Blueprint("manage", __name__)


@app.before_request
def require_admin() -> None:
    if not g.user or g.user.is_anonymous or not g.user.site_admin:
        abort(404)


@app.route("/")
def index() -> Response:
    num_talks = Talk.active().count()
    num_without_category = Talk.active().filter(not_(Talk.categories.any())).count()
    num_without_anonymization = Talk.active().filter_by(is_anonymized=False).count()

    # TODO: figure out how to do this with "not in JSON list" queires
    num_surveys = 0
    num_non_man = 0
    num_non_white = 0
    for survey in DemographicSurvey.query.all():
        num_surveys += 1
        if survey.doesnt_have_gender(Gender.MAN):
            num_non_man += 1
        if survey.doesnt_have_ethnicity(Ethnicity.WHITE_CAUCASIAN):
            num_non_white += 1

    return render_template(
        "manage/index.html",
        num_talks=num_talks,
        num_without_category=num_without_category,
        num_without_anonymization=num_without_anonymization,
        num_surveys=num_surveys,
        num_non_man=num_non_man,
        num_non_white=num_non_white,
    )


@app.route("/categorize")
def categorize_talks() -> Response:
    not_categorized = Talk.active().filter(not_(Talk.categories.any()))
    if not db.session.query(not_categorized.exists()).scalar():
        flash("All talks categorized")
        talks = Talk.active().options(joinedload(Talk.categories)).all()
        return render_template(
            "manage/category_list.html",
            talks=talks,
        )

    talk = not_categorized.order_by(func.random()).first()
    return redirect(url_for("manage.categorize_talk", talk_id=talk.talk_id))


@app.route("/categorize/<int:talk_id>", methods=["GET", "POST"])
def categorize_talk(talk_id: int) -> Response:
    talk = Talk.query.get_or_404(talk_id)
    category_ids = [c.category_id for c in talk.categories]
    form = CategorizeForm(obj=Bunch(category_ids=category_ids))
    if form.validate_on_submit():
        categories = Category.query.filter(
            Category.category_id.in_(form.category_ids.data),  # type: ignore
        ).all()
        del talk.categories[:]
        talk.categories.extend(categories)
        db.session.add(talk)
        db.session.commit()
        return redirect(url_for("manage.categorize_talks"))

    return render_template(
        "manage/categorize.html",
        form=form,
        talk=talk,
    )


@app.route("/anonymize")
def anonymize_talks() -> Response:
    not_anonymized = Talk.active().filter_by(is_anonymized=False)
    if not db.session.query(not_anonymized.exists()).scalar():
        flash("All talks anonymized")
        return redirect(url_for("manage.index"))

    talk = not_anonymized.order_by(func.random()).first()
    return redirect(url_for("manage.anonymize_talk", talk_id=talk.talk_id))


@app.route("/anonymize/<int:talk_id>", methods=["GET", "POST"])
def anonymize_talk(talk_id: int) -> Response:
    talk = Talk.query.get_or_404(talk_id)
    if request.method == "GET" and talk.is_anonymized:
        # the TalkForm uses the regular fields; if we've already
        # anonymized, an admin is looking at a past anonymization,
        # so show that instead of the original versions
        talk.title = talk.anonymized_title
        talk.description = talk.anonymized_description
        talk.outline = talk.anonymized_outline

    form = TalkForm(obj=talk)
    if form.validate_on_submit():
        talk.anonymized_title = form.title.data
        talk.anonymized_description = form.description.data
        talk.anonymized_outline = form.outline.data
        talk.is_anonymized = True
        talk.has_anonymization_changes = (
            talk.anonymized_title != talk.title or
            talk.anonymized_description != talk.description or
            talk.anonymized_outline != talk.outline
        )
        db.session.add(talk)
        db.session.commit()

        db.session.refresh(talk)
        speakers = [
            talk_speaker.user for talk_speaker in talk.speakers
            if talk_speaker.state == InvitationStatus.CONFIRMED
        ]

        if talk.has_anonymization_changes:
            mail.send_mail(
                to=[speaker.email for speaker in speakers],
                template="email/talk-anonymized",
                talk_id=talk.talk_id,
                title=talk.title,
            )

        if request.form.get("save-and-next"):
            return redirect(url_for("manage.anonymize_talks"))
        else:
            return redirect(url_for(
                "manage.preview_anonymized_talk",
                talk_id=talk.talk_id,
            ))

    return render_template(
        "manage/anonymize_talk.html",
        form=form,
        talk=talk,
    )


@app.route("/anonymize/<int:talk_id>/preview")
def preview_anonymized_talk(talk_id: int) -> Response:
    talk = Talk.query.get_or_404(talk_id)
    return render_template(
        "anonymized_talk_preview.html",
        talk=talk,
        mode="admin",
    )


class AuthMixin:
    def is_accessible(self) -> bool:
        return g.user.site_admin

    def inaccessible_callback(self, name: str, **kwargs: Any) -> None:
        abort(404)


class ModelView(AuthMixin, sqla.ModelView):
    pass


class AdminDashboard(AuthMixin, AdminIndexView):
    @expose()
    def index(self) -> Response:
        views = [v for v in flask_admin._views if isinstance(v, ModelView)]
        return self.render(
            "admin/index.html",
            views=views,
        )


class DemographicSurveyView(ModelView):
    column_exclude_list = ("user", )

    def __init__(self) -> None:
        super().__init__(DemographicSurvey, db.session)


flask_admin = Admin(
    index_view=AdminDashboard(url="/manage/db"),
    template_mode="bootstrap3",
    url="/manage/db",
)
flask_admin.add_view(ModelView(Conference, db.session))
flask_admin.add_view(ModelView(Talk, db.session))
flask_admin.add_view(ModelView(Category, db.session))
flask_admin.add_view(ModelView(User, db.session))
flask_admin.add_view(DemographicSurveyView())
