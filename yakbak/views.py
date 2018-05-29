import logging

from flask import Blueprint


app = Blueprint("views", __name__)
logger = logging.getLogger("views")


@app.route("/")
def hello_world():
    return "Hello, world!"
