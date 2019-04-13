from typing import Any
import random

from bunch import Bunch
from flask import abort, Blueprint, flash, g, redirect, render_template, url_for
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib import sqla
from sqlalchemy import not_
from sqlalchemy.orm import joinedload
from werkzeug import Response

from yakbak.forms import CategorizeForm, Ethnicity, Gender
from yakbak.models import Category, Conference, db, DemographicSurvey, Talk, User


app = Blueprint("manage", __name__)


@app.before_request
def require_admin() -> None:
    if not g.user or g.user.is_anonymous or not g.user.site_admin:
        abort(404)


@app.route("/")
def index() -> Response:
    num_talks = Talk.active().count()
    num_without_category = Talk.active().filter(not_(Talk.categories.any())).count()

    # TODO: figure out how to do this with "not in JSON list" queires
    num_surveys = 0
    num_non_man = 0
    num_non_white = 0
    for survey in DemographicSurvey.query.all():
        num_surveys += 1
        if Gender.MAN.name not in survey.gender:
            num_non_man += 1
        if Ethnicity.WHITE_CAUCASIAN.name not in survey.ethnicity:
            num_non_white += 1

    return render_template(
        "manage/index.html",
        num_talks=num_talks,
        num_without_category=num_without_category,
        num_surveys=num_surveys,
        num_non_man=num_non_man,
        num_non_white=num_non_white,
    )


@app.route("/categorize")
def categorize_talks() -> Response:
    count = Talk.active().filter(not_(Talk.categories.any())).count()
    if count == 0:
        flash("All talks categorized")
        talks = Talk.active().options(joinedload(Talk.categories)).all()
        return render_template(
            "manage/category_list.html",
            talks=talks,
        )

    offset = int(random.random() * count)
    talk = Talk.active().filter(not_(Talk.categories.any())).offset(offset).limit(1).one()
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
