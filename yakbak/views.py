from datetime import datetime
from typing import Any, Dict, Iterable, List, Tuple
import logging

from attr import fields
from flask import (
    abort,
    Blueprint,
    g,
    Markup,
    redirect,
    render_template,
    request,
    Response,
    url_for,
)
from flask_login import login_required, logout_user
from markdown import markdown

from yakbak.forms import TalkForm
from yakbak.models import db, Talk
from yakbak.settings import SocialAuthSettings


app = Blueprint("views", __name__)
logger = logging.getLogger("views")


@app.context_processor
def top_nav() -> Dict[str, List[Tuple[str, str, bool]]]:
    def navtuple(label: str, route: str) -> Tuple[str, str, bool]:
        url = url_for(route)
        return (label, url, request.path == url)

    nav = [
        navtuple("Home", "views.dashboard"),
    ]
    if g.user.is_authenticated:
        nav.append(navtuple("Log Out", "views.logout"))
    else:
        nav.append(navtuple("Log In", "views.login"))

    return {"nav_links": nav}


@app.app_template_filter("timesince")
def timesince(dt: datetime, default: str = "just now") -> str:
    # from http://flask.pocoo.org/snippets/33/
    now = datetime.utcnow()
    diff = now - dt

    periods = [
        (diff.days // 365, "year", "years"),
        (diff.days // 30, "month", "months"),
        (diff.days // 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds // 3600, "hour", "hours"),
        (diff.seconds // 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    ]

    for period, singular, plural in periods:
        if period:
            return "%d %s ago" % (period, singular if period == 1 else plural)

    return default


@app.app_template_filter("markdown")
def markdown_filter(value: str) -> str:
    return Markup(markdown(value, output_format="html5"))


@app.app_template_filter("remove")
def remove_element(value: Iterable[Any], item: Any) -> List[Any]:
    return [elm for elm in value if elm != item]


@app.route("/")
def index() -> Response:
    if g.user.is_authenticated:
        return redirect(url_for("views.dashboard"))
    else:
        return redirect(url_for("views.login"))


@app.route("/login")
def login() -> Response:
    social_methods = SocialAuthSettings.social_auth_methods()
    return render_template("login.html", social_methods=social_methods)


@app.route("/logout")
def logout() -> Response:
    logout_user()
    return redirect(url_for("views.index"))


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
