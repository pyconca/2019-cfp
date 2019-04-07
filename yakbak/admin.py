from typing import Any

from flask import abort, g
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


class AuthMixin:
    def is_accessible(self) -> bool:
        return g.user.site_admin

    def inaccessible_callback(self, name: str, **kwargs: Any) -> None:
        abort(404)


class AdminDashboard(AuthMixin, AdminIndexView):

    @expose("/")
    def dashboard(self) -> None:
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

        return self.render(
            "admin/index.html",
            num_talks=num_talks,
            num_surveys=num_surveys,
            num_non_man=num_non_man,
            num_non_white=num_non_white,
        )


class ModelView(AuthMixin, sqla.ModelView):
    pass


class DemographicSurveyView(ModelView):
    column_exclude_list = ("user", )

    def __init__(self) -> None:
        super().__init__(DemographicSurvey, db.session)


admin = Admin(index_view=AdminDashboard(), template_mode="bootstrap3")

admin.add_view(ModelView(Conference, db.session))
admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Talk, db.session))
admin.add_view(DemographicSurveyView())
