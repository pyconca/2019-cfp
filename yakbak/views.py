import logging

from flask import (
    abort,
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    Response,
    url_for,
)
from flask_login import login_required, login_user, logout_user

from yakbak import mail
from yakbak.auth import get_magic_link_token_and_expiry, parse_magic_link_token
from yakbak.forms import MagicLinkForm, TalkForm, UserForm
from yakbak.models import db, Talk, User


app = Blueprint("views", __name__)
logger = logging.getLogger("views")


@app.route("/")
def index() -> Response:
    if g.user.is_authenticated:
        return redirect(url_for("views.dashboard"))
    return render_template("index.html")


@app.route("/login")
def login() -> Response:
    auth_methods = current_app.settings.auth.auth_methods()
    return render_template("login.html", auth_methods=auth_methods)


@app.route("/logout")
def logout() -> Response:
    logout_user()
    return redirect(url_for("views.index"))


@app.route("/login/email", methods=["GET", "POST"])
def email_magic_link() -> Response:
    form = MagicLinkForm()
    if form.validate_on_submit():
        token, expiry = get_magic_link_token_and_expiry(form.email.data)
        url = url_for(
            "views.email_magic_link_login",
            magic_link_token=token,
            _external=True,
        )
        mail.send_mail(
            to=[form.email.data],
            template="email/magic-link",
            magic_link=url,
            magic_link_expiration=expiry,
        )
        return redirect(url_for("views.email_magic_link_done"))
    return render_template("email_magic_link.html", form=form)


@app.route("/login/email/sent")
def email_magic_link_done() -> Response:
    return render_template("email_magic_link_sent.html")


@app.route("/login/token/<magic_link_token>")
def email_magic_link_login(magic_link_token: str) -> Response:
    verified_email = parse_magic_link_token(magic_link_token)
    if verified_email is None:
        abort(404)

    user = User.query.filter_by(email=verified_email).first()
    if user:
        login_user(user)
        return redirect(url_for("views.dashboard"))

    user = User(email=verified_email, fullname=verified_email)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    flash("Welcome! Please tell us your name.")
    return redirect(url_for("views.user_profile"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
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
@login_required
def edit_talk(talk_id: int) -> Response:
    talk = Talk.query.get_or_404(talk_id)
    if g.user not in talk.speakers:
        # TODO: figure out how to do this in the query directly?
        abort(404)

    form = TalkForm(conference=g.conference, obj=talk)
    if form.validate_on_submit():
        form.populate_obj(talk)
        db.session.add(talk)
        db.session.commit()
        return redirect(url_for("views.preview_talk", talk_id=talk.talk_id))

    return render_template("edit_talk.html", talk=talk, form=form)


@app.route("/talks/<int:talk_id>/preview")
@login_required
def preview_talk(talk_id: int) -> Response:
    talk = Talk.query.get_or_404(talk_id)
    if g.user not in talk.speakers:
        # TODO: figure out how to do this in the query directly?
        abort(404)

    return render_template("preview_talk.html", talk=talk)


@app.route("/talks/new", methods=["GET", "POST"])
@login_required
def create_talk() -> Response:
    talk = Talk(speakers=[g.user])
    form = TalkForm(conference=g.conference, obj=talk)
    if form.validate_on_submit():
        form.populate_obj(talk)
        db.session.add(talk)
        db.session.commit()
        return redirect(url_for("views.preview_talk", talk_id=talk.talk_id))

    return render_template("edit_talk.html", talk=talk, form=form)
