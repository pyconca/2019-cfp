import logging

from flask import Blueprint, current_app, redirect, render_template, Response, url_for
from flask_login import logout_user

from yakbak.settings import SocialAuthSettings


app = Blueprint("views", __name__)
logger = logging.getLogger("views")


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
