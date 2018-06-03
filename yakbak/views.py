from typing import Dict, List, Tuple
import logging

from flask import (
    Blueprint,
    g,
    redirect,
    render_template,
    request,
    Response,
    url_for,
)
from flask_login import logout_user

from yakbak.settings import SocialAuthSettings


app = Blueprint("views", __name__)
logger = logging.getLogger("views")


@app.context_processor
def top_nav() -> Dict[str, List[Tuple[str, str, bool]]]:
    def navtuple(label: str, route: str) -> Tuple[str, str, bool]:
        url = url_for(route)
        return (label, url, request.path == url)

    nav = [
        navtuple("Home", "views.index"),
    ]
    if g.user.is_authenticated:
        nav.append(navtuple("Log Out", "views.logout"))
    else:
        nav.append(navtuple("Log In", "views.login"))

    return {"nav_links": nav}


@app.route("/")
def index() -> Response:
    return render_template("index.html")


@app.route("/login")
def login() -> Response:
    social_methods = SocialAuthSettings.social_auth_methods()
    return render_template("login.html", social_methods=social_methods)


@app.route("/logout")
def logout() -> Response:
    logout_user()
    return redirect(url_for("views.index"))
