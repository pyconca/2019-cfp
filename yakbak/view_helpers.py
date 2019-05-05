from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Iterable, List, Tuple, Union

from flask import Blueprint, current_app, g, Markup, render_template, request, url_for
from flask_login import current_user
from markdown import markdown
from werkzeug.wrappers import Response
import diff_match_patch

from yakbak.diff import diff_wordsToChars
from yakbak.models import Talk


app = Blueprint("view_helpers", __name__)
ViewResponse = Union[Response, Tuple[Response, int]]


@app.app_context_processor
def top_nav() -> Dict[str, List[Tuple[str, str, bool]]]:
    def navtuple(label: str, route: str) -> Tuple[str, str, bool]:
        url = url_for(route)
        return (label, url, request.path == url)

    user = getattr(g, "user", None)

    left_nav = []
    if user and not user.is_anonymous:
        left_nav.append(navtuple("My Proposals", "views.talks_list"))
    if user and not user.is_anonymous and user.is_site_admin:
        left_nav.append(navtuple("Admin", "manage.index"))
        left_nav.append(navtuple("DB Entries", "admin.index"))

    right_nav = []
    if user and user.is_authenticated:
        right_nav.append(navtuple("Edit Profile", "views.user_profile"))
        right_nav.append(navtuple(f"Log Out ({g.user.fullname})", "views.logout"))
    else:
        right_nav.append(navtuple("Log In", "views.login"))

    return {
        "left_nav": left_nav,
        "right_nav": right_nav,
    }


@app.app_context_processor
def settings_in_template() -> Dict[str, Any]:
    return {"settings": current_app.settings}


@app.app_context_processor
def set_user_in_templates() -> Dict[str, Any]:
    try:
        return {"user": current_user}
    except AttributeError:
        return {}


@app.before_app_request
def set_current_user_on_g() -> None:
    g.user = current_user


def if_creating_proposals_allowed(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> ViewResponse:
        window = g.conference.proposal_window
        if window and not window.includes_now():
            return render_template("action_not_allowed.html", action="create_proposal"), 400
        return func(*args, **kwargs)
    return wrapper


def if_editing_proposals_allowed(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> ViewResponse:
        proposal_window = g.conference.proposal_window
        voting_window = g.conference.voting_window
        disallowed = (
            request.method == "POST" and (
                (proposal_window and not proposal_window.includes_now())
                or (voting_window and voting_window.includes_now())
            )
        )
        # TODO: allow edits to accepted talks after proposal and voting windows
        if disallowed:
            return render_template("action_not_allowed.html", action="edit_proposal"), 400
        return func(*args, **kwargs)
    return wrapper


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
def markdown_filter(value: str) -> Markup:
    return Markup(markdown(value, output_format="html5"))


@app.app_template_filter("remove")
def remove_element(value: Iterable[Any], item: Any) -> List[Any]:
    return [elm for elm in value if elm != item]


@app.app_template_filter("anonymization_diff")
def anonymization_diff(talk: Talk, attr: str) -> Markup:
    left = getattr(talk, attr)
    right = getattr(talk, f"anonymized_{attr}")
    if not right:
        return Markup(left)

    dmp = diff_match_patch.diff_match_patch()

    # from https://github.com/google/diff-match-patch/wiki/Line-or-Word-Diffs#line-mode
    left_words, right_words, word_array = diff_wordsToChars(left, right)
    diff = dmp.diff_main(left_words, right_words)
    dmp.diff_charsToLines(diff, word_array)

    out = []
    for op, text in diff:
        if op == 1:  # addition
            out.append(f'<span class="diff_add">{text}</span>')
        elif op == -1:  # deletion
            out.append(f'<span class="diff_sub">{text}</span>')
        else:
            out.append(text)

    return Markup("".join(out))
