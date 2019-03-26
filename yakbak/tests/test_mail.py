from yakbak import mail
from yakbak.types import Application


def test_send_mail(app: Application) -> None:
    with app.app_context(), app.test_request_context():
        with mail.mail.record_messages() as outbox:
            mail.send_mail(
                to=["test@example.com"],
                template="email-template",  # in yakbak/tests/templates
                variables="replacements",
            )

    assert len(outbox) == 1

    msg = outbox[0]
    assert msg.subject == "The Email Subject"
    assert msg.sender == "sender@example.com"
    assert msg.recipients == ["test@example.com"]
    assert msg.body == "This is the email. It has replacements!"
