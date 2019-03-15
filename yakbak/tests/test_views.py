import re

from werkzeug.test import Client
import bs4
import mock

from yakbak import mail, views
from yakbak.models import (
    AgeGroup,
    db,
    DemographicSurvey,
    InvitationStatus,
    ProgrammingExperience,
    Talk,
    User,
)
from yakbak.tests.util import (
    assert_html_response,
    assert_html_response_contains,
    assert_html_response_doesnt_contain,
    assert_redirected,
    extract_csrf_from,
)


def test_root_shows_cfp_description_when_logged_out(client: Client) -> None:
    resp = client.get("/")
    assert_html_response_contains(resp, "Our Call for Proposals is open through")


def test_talks_list_shows_user_name(client: Client, user: User) -> None:
    resp = client.get("/test-login/{}".format(user.user_id), follow_redirects=True)
    assert_html_response_contains(resp, f"Log Out ({user.fullname})")


def test_logout_logs_you_out(client: Client, user: User) -> None:
    resp = client.get("/test-login/{}".format(user.user_id), follow_redirects=True)
    assert_html_response_contains(resp, f"Log Out ({user.fullname})")

    resp = client.get("/logout", follow_redirects=True)
    assert_html_response_contains(resp, "Log In")


def test_login_shows_auth_methods(client: Client) -> None:
    # only the email auth method is enabled in test config :\
    resp = client.get("/login")
    assert_html_response_contains(resp, "Magic Link")


def test_email_magic_link_form(client: Client) -> None:
    resp = client.get("/login/email")
    assert_html_response_contains(resp, re.compile('<input.*name="email"'))
    csrf_token = extract_csrf_from(resp)

    postdata = {"email": "jane@example.com", "csrf_token": csrf_token}
    with mock.patch.object(mail, "send_mail") as send_mail:
        resp = client.post("/login/email", data=postdata, follow_redirects=True)

    assert_html_response_contains(resp, "We have sent a link to you")
    send_mail.assert_called_once_with(
        to=["jane@example.com"],
        template="email/magic-link",
        magic_link=mock.ANY,
        magic_link_expiration="30 minutes",
    )


def test_email_magic_link_login_for_new_user(client: Client) -> None:
    with mock.patch.object(views, "parse_magic_link_token") as parse:
        parse.return_value = "jane@example.com"
        resp = client.get("/login/token/any-token-here", follow_redirects=True)

    assert_html_response_contains(resp, "User Profile")


def test_email_magic_link_login_for_returning_user(client: Client, user: User) -> None:
    with mock.patch.object(views, "parse_magic_link_token") as parse:
        parse.return_value = user.email
        resp = client.get("/login/token/any-token-here", follow_redirects=True)

    assert_html_response_contains(resp, "Talks")


def test_invalid_email_magic_link_login(client: Client) -> None:
    with mock.patch.object(views, "parse_magic_link_token") as parse:
        parse.return_value = None
        resp = client.get("/login/token/any-token-here", follow_redirects=True)

    assert_html_response(resp, status=404)


def test_profile_updates_name_not_email(client: Client, user: User) -> None:
    resp = client.get("/test-login/{}".format(user.user_id), follow_redirects=True)
    resp = client.get("/profile")
    assert_html_response_contains(
        resp,
        re.compile('<input[^>]*name="fullname"'),
        re.compile('<input[^>]*id="email"[^>]*disabled'),
    )

    csrf_token = extract_csrf_from(resp)
    postdata = {
        "email": "jane@example.com",
        "fullname": "Jane Doe",
        "csrf_token": csrf_token,
    }
    resp = client.post("/profile", data=postdata, follow_redirects=True)
    assert_html_response_contains(resp, "Talks")

    db.session.add(user)
    db.session.refresh(user)
    assert user.fullname == "Jane Doe"
    assert user.email == "test@example.com"  # the old address


def test_talks_list_page_lists_talks(client: Client, user: User) -> None:
    alice = User(email="alice@example.com", fullname="Alice Example")
    bob = User(email="bob@example.com", fullname="Bob Example")
    db.session.add(alice)
    db.session.add(bob)
    db.session.commit()

    one_talk = Talk(title="My Talk", length=25)
    one_talk.add_speaker(user, InvitationStatus.CONFIRMED)

    two_talk = Talk(title="Our Talk", length=40)
    two_talk.add_speaker(user, InvitationStatus.CONFIRMED)
    two_talk.add_speaker(alice, InvitationStatus.CONFIRMED)

    all_talk = Talk(title="All Our Talk", length=25)
    all_talk.add_speaker(user, InvitationStatus.CONFIRMED)
    all_talk.add_speaker(alice, InvitationStatus.CONFIRMED)
    all_talk.add_speaker(bob, InvitationStatus.CONFIRMED)

    db.session.add(one_talk)
    db.session.add(two_talk)
    db.session.add(all_talk)
    db.session.commit()

    client.get("/test-login/{}".format(user.user_id))
    resp = client.get("/talks")
    body = assert_html_response(resp)
    soup = bs4.BeautifulSoup(body, "html.parser")

    talks = soup.find_all("div", class_="talk")
    assert len(talks) == 3

    talk_row_texts = [re.sub(r"\s+", " ", talk.get_text()).strip() for talk in talks]
    assert sorted(talk_row_texts) == sorted([
        "My Talk (25 Minutes)",
        "Our Talk (40 Minutes, Alice Example and You)",
        "All Our Talk (25 Minutes, Alice Example, Bob Example, and You)",
    ])


def test_create_talk_goes_to_preview(client: Client, user: User) -> None:
    client.get("/test-login/{}".format(user.user_id))
    resp = client.get("/talks/new")
    csrf_token = extract_csrf_from(resp)

    postdata = {
        "title": "My Awesome Talk",
        "length": "25",
        "csrf_token": csrf_token,
    }

    resp = client.post("/talks/new", data=postdata, follow_redirects=True)
    assert_html_response_contains(
        resp,
        "Reviewers will see voting instructions here",
        "Save &amp; Return",
        "Edit Again",
    )

    # but at this point the talk is saved
    speakers_predicate = Talk.speakers.any(user_id=user.user_id)  # type: ignore
    talks = Talk.query.filter(speakers_predicate).all()
    assert len(talks) == 1
    assert talks[0].title == "My Awesome Talk"


def test_talk_form_uses_select_field_for_length(client: Client, user: User) -> None:
    client.get("/test-login/{}".format(user.user_id))
    resp = client.get("/talks/new")

    assert_html_response_contains(
        resp,
        re.compile(
            '<select[^>]*(?:name="length"[^>]*required|required[^>]*name="length")',
        ),
    )


def test_it_redirects_to_login_page_if_youre_not_logged_in(client: Client) -> None:
    resp = client.get("/talks/new")
    assert_redirected(resp, "/login?next=%2Ftalks%2Fnew")


def test_demographic_survey_saves_data(client: Client, user: User) -> None:
    assert user.demographic_survey is None

    client.get("/test-login/{}".format(user.user_id))
    resp = client.get("/profile/demographic_survey")

    assert_html_response_contains(
        resp,
        "I identify as a:",
        "I identify my ethnicity as:",
        "About my past speaking experience:",
        "My age is:",
        "I have been programming for:",
    )

    csrf_token = extract_csrf_from(resp)
    postdata = {
        "gender": [
            "MAN",
            "WOMAN",
            "NONBINARY",
            "free form text for 'other' gender",
        ],
        "ethnicity": [
            "ASIAN",
            "BLACK_AFRICAN_AMERICAN",
            "HISPANIC_LATINX",
            "NATIVE_AMERICAN",
            "PACIFIC_ISLANDER",
            "WHITE_CAUCASIAN",
            "free form text for 'other' ethnicity",
        ],
        "past_speaking": [
            "NEVER",
            "PYGOTHAM",
            "OTHER_PYTHON",
            "OTHER_NONPYTHON",
        ],
        "age_group": "UNDER_45",
        "programming_experience": "UNDER_10YR",
        "csrf_token": csrf_token,
    }
    resp = client.post(
        "/profile/demographic_survey",
        data=postdata,
        follow_redirects=True,
    )
    assert_html_response_contains(resp, "Thanks For Completing")

    survey = DemographicSurvey.query.filter_by(user_id=user.user_id).one()

    assert sorted(survey.gender) == sorted(postdata["gender"])
    assert sorted(survey.ethnicity) == sorted(postdata["ethnicity"])
    assert sorted(survey.past_speaking) == sorted(postdata["past_speaking"])
    assert survey.age_group == AgeGroup.UNDER_45
    assert survey.programming_experience == ProgrammingExperience.UNDER_10YR


def test_demographic_survey_skips_blank_other_values(client: Client, user: User) -> None:
    assert user.demographic_survey is None

    client.get("/test-login/{}".format(user.user_id))
    resp = client.get("/profile/demographic_survey")

    assert_html_response_contains(
        resp,
        "I identify as a:",
        "I identify my ethnicity as:",
        "About my past speaking experience:",
        "My age is:",
        "I have been programming for:",
    )

    csrf_token = extract_csrf_from(resp)
    postdata = {
        "gender": ["MAN", ""],
        "csrf_token": csrf_token,
    }
    resp = client.post(
        "/profile/demographic_survey",
        data=postdata,
        follow_redirects=True,
    )
    assert_html_response_contains(resp, "Thanks For Completing")

    survey = DemographicSurvey.query.filter_by(user_id=user.user_id).one()

    assert survey.gender == ["MAN"]


def test_demographic_survey_opt_out(client: Client, user: User) -> None:
    assert user.demographic_survey is None

    client.get("/test-login/{}".format(user.user_id))
    resp = client.get("/profile/demographic_survey/opt-out")

    assert_html_response_contains(resp, "You Have Opted Out")

    survey = DemographicSurvey.query.filter_by(user_id=user.user_id).one()

    assert not survey.gender
    assert not survey.ethnicity
    assert not survey.age_group
    assert not survey.programming_experience
    assert not survey.past_speaking


def test_prompt_for_demographic_survey(client: Client, user: User) -> None:
    client.get("/test-login/{}".format(user.user_id))
    resp = client.get("/talks")

    assert_html_response_doesnt_contain(resp, "demographic survey")

    talk = Talk(title="My Talk", length=25)
    talk.add_speaker(user, InvitationStatus.CONFIRMED)
    db.session.add(talk)
    db.session.commit()

    client.get("/test-login/{}".format(user.user_id))
    resp = client.get("/talks")

    assert_html_response_contains(resp, "demographic_survey")
