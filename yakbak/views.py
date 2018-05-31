import logging

from flask import abort, Blueprint, redirect, request, Response
from flask_login import current_user, login_user, logout_user

from yakbak.auth import load_user


app = Blueprint("views", __name__)
logger = logging.getLogger("views")


@app.route("/")
def index() -> Response:
    logger.info("current_user: %r", current_user)
    name = current_user.name if current_user.is_authenticated else "Anonymous"
    return Response("You are {}".format(name))


@app.route("/login")
def login_form() -> Response:
    return Response("""
        <form method="post" action="/login">
            <label for="user_id">User Id:</label>
            <input type="text" name="user_id">
            <input type="submit">
        </form>
    """)


@app.route("/login", methods=["POST"])
def login() -> Response:
    user_id = request.form.get("user_id")
    user = load_user(str(user_id))
    if not user:
        abort(500)
    login_user(user)
    return redirect("/")


@app.route("/logout")
def logout() -> Response:
    logout_user()
    return redirect("/")
