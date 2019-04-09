from werkzeug.test import Client

from yakbak.models import db, User
from yakbak.tests.util import assert_html_response


def test_anonymous_users_cant_access_admin(client: Client) -> None:
    resp = client.get("/manage/")
    assert_html_response(resp, status=404)


def test_ordinary_users_cant_access_admin(client: Client, user: User) -> None:
    client.get("/test-login/{}".format(user.user_id), follow_redirects=True)
    resp = client.get("/manage/")
    assert_html_response(resp, status=404)


def test_site_admins_can_access_admin(client: Client, user: User) -> None:
    client.get("/test-login/{}".format(user.user_id), follow_redirects=True)

    user.site_admin = True
    db.session.add(user)
    db.session.commit()

    resp = client.get("/manage/")
    assert_html_response(resp, status=200)
