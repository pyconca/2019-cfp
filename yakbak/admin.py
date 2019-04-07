from typing import Any

from flask import abort, Blueprint, g, render_template, Response
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib import sqla

from yakbak.forms import Ethnicity, Gender
from yakbak.models import (
    Conference,
    db,
    DemographicSurvey,
    Talk,
    TalkStatus,
    User,
)


app = Blueprint("manage", __name__)


@app.before_request
def require_admin() -> None:
    if not g.user or not g.user.site_admin:
        abort(404)


@app.route("/")
def index() -> Response:
    num_talks = Talk.query.filter(
        Talk.state == TalkStatus.PROPOSED,
    ).count()

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
        num_surveys=num_surveys,
        num_non_man=num_non_man,
        num_non_white=num_non_white,
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
flask_admin.add_view(ModelView(User, db.session))
flask_admin.add_view(DemographicSurveyView())
