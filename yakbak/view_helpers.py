from datetime import datetime
from typing import Any, Dict, Iterable, List, Tuple

from flask import Blueprint, g, Markup, request, url_for
from markdown import markdown


app = Blueprint("view_helpers", __name__)


@app.app_context_processor
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
