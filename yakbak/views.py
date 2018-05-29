import logging

from flask import Blueprint, Response


app = Blueprint("views", __name__)
logger = logging.getLogger("views")


@app.route("/")
def hello_world() -> Response:
    return Response("Hello, world!")
