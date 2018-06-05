import logging

from flask import (
    abort,
    Blueprint,
    current_app,
    g,
    redirect,
    render_template,
    Response,
    url_for,
)
from flask_login import login_required, logout_user

from yakbak.forms import TalkForm, UserForm
from yakbak.models import db, Talk


app = Blueprint("views", __name__)
logger = logging.getLogger("views")


@app.route("/")
def index() -> Response:
    if g.user.is_authenticated:
        return redirect(url_for("views.dashboard"))
    else:
        return redirect(url_for("views.login"))


@app.route("/login")
def login() -> Response:
    auth_methods = current_app.settings.auth.auth_methods()
    return render_template("login.html", auth_methods=auth_methods)


@app.route("/logout")
def logout() -> Response:
    logout_user()
    return redirect(url_for("views.index"))


@app.route("/profile", methods=["GET", "POST"])
def user_profile() -> Response:
    user = g.user
    form = UserForm(obj=user)
    if form.validate_on_submit():
        form.populate_obj(user)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("views.dashboard"))

    return render_template("profile.html", form=form)


@app.route("/dashboard")
@login_required
def dashboard() -> Response:
    talks = g.user.talks
    return render_template("dashboard.html", talks=talks)


@app.route("/talks/<int:talk_id>", methods=["GET", "POST"])
def edit_talk(talk_id: int) -> Response:
    talk = Talk.query.get_or_404(talk_id)
    if g.user not in talk.speakers:
        # TODO: figure out how to do this in the query directly?
        abort(404)

    form = TalkForm(obj=talk)
    if form.validate_on_submit():
        form.populate_obj(talk)
        db.session.add(talk)
        db.session.commit()
        return redirect(url_for("views.preview_talk", talk_id=talk.talk_id))

    return render_template("edit_talk.html", talk=talk, form=form)


@app.route("/talks/<int:talk_id>/preview")
def preview_talk(talk_id: int) -> Response:
    talk = Talk.query.get_or_404(talk_id)
    if g.user not in talk.speakers:
        # TODO: figure out how to do this in the query directly?
        abort(404)

    return render_template("preview_talk.html", talk=talk)


@app.route("/talks/new", methods=["GET", "POST"])
def create_talk() -> Response:
    talk = Talk(speakers=[g.user])
    form = TalkForm(obj=talk)
    if form.validate_on_submit():
        form.populate_obj(talk)
        db.session.add(talk)
        db.session.commit()
        return redirect(url_for("views.dashboard"))

    return render_template("edit_talk.html", talk=talk, form=form)
