from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from yakbak.models import Conference, db, Talk, User


admin = Admin(template_mode="bootstrap3")

admin.add_view(ModelView(Conference, db.session))
admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Talk, db.session))
