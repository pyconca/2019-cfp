import logging

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    Response,
    url_for,
)
from flask_login import login_user, logout_user

from yakbak.auth import load_user


app = Blueprint("views", __name__)
logger = logging.getLogger("views")


@app.route("/")
def index() -> Response:
    return render_template("index.html")


@app.route("/login")
def login_form() -> Response:
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login() -> Response:
    user_id = request.form.get("user_id")
    user = load_user(str(user_id))
    if not user:
        flash("User ID not found")
        return render_template("login.html", user_id=user_id)

    login_user(user)
    return redirect(url_for("views.index"))


@app.route("/logout")
def logout() -> Response:
    logout_user()
    return redirect(url_for("views.index"))
