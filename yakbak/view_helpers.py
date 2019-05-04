from datetime import datetime
from typing import Any, Dict, Iterable, List, Tuple

from flask import Blueprint, current_app, g, Markup, request, url_for
from flask_login import current_user
from markdown import markdown
import diff_match_patch

from yakbak.diff import diff_wordsToChars


app = Blueprint("view_helpers", __name__)


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


@app.app_template_filter("anonymization_diff")
def anonymization_diff(talk, attr):
    left = getattr(talk, attr)
    right = getattr(talk, f"anonymized_{attr}")
    if not right:
        return Markup(left)

    dmp = diff_match_patch.diff_match_patch()

    # based on https://github.com/google/diff-match-patch/wiki/Line-or-Word-Diffs#line-mode
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
