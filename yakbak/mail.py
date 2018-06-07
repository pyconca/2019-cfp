from typing import Any, Dict, List, Optional, Tuple

from attr import attrib, attrs
from flask import current_app, render_template as flask_render_template
from flask_mail import Mail
import frontmatter


mail = Mail()


@attrs
class MailMeta:
    subject: str = attrib()
    sender: Optional[str] = attrib(default=None)


def render_template(template: str, **kwargs: Dict[str, Any]) -> Tuple[MailMeta, str]:
    rendered = flask_render_template(template, **kwargs)
    parsed = frontmatter.loads(rendered)
    meta = MailMeta(parsed["subject"], parsed.get("sender"))
    return meta, parsed.content


def send_mail(to: List[str], template: str, **kwargs: Any) -> None:
    """
    Send an email based on the ``template`` and ``kwargs``.

    The ``template`` is a hybrid Jinja2 template with Markdown-style
    frontmatter. The frontmatter is expected to contain the keys:

    - ``subject`` (str): (required) used as the email subject
    - ``sender`` (str): override default sender address

    """
    meta, body = render_template(template, **kwargs)
    sender = meta.sender or current_app.settings.smtp.sender
    with mail.connect() as conn:
        conn.send_message(
            subject=meta.subject,
            sender=sender,
            recipients=to,
            body=body,
        )
