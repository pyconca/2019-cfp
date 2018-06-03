import logging

from flask import Blueprint, redirect, render_template, Response, url_for
from flask_login import logout_user


app = Blueprint("views", __name__)
logger = logging.getLogger("views")


@app.route("/")
def index() -> Response:
    return render_template("index.html")


@app.route("/login")
def login() -> Response:
    return render_template("login.html")


@app.route("/logout")
def logout() -> Response:
    logout_user()
    return redirect(url_for("views.index"))
