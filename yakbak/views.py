import logging

from flask import (
    abort,
    Blueprint,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    url_for,
)
from flask_login import login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError
from werkzeug.wrappers import Response

from yakbak import mail
from yakbak.auth import get_magic_link_token_and_expiry, parse_magic_link_token
from yakbak.forms import (
    DemographicSurveyForm,
    EmailAddressForm,
    SpeakerEmailForm,
    TalkForm,
    UserForm,
)
from yakbak.models import (
    db,
    DemographicSurvey,
    InvitationStatus,
    Talk,
    TalkSpeaker,
    TalkStatus,
    UsedMagicLink,
    User,
)
from yakbak.view_helpers import (
    requires_new_proposal_window_open,
    requires_proposal_editing_window_open,
)

app = Blueprint("views", __name__)
logger = logging.getLogger("views")


def load_talk(talk_id: int) -> Talk:
    talk = Talk.query.get_or_404(talk_id)
    if g.user not in [s.user for s in talk.speakers]:
        # TODO: figure out how to do this in the query directly?
        abort(404)

    return talk


@app.route("/")
def index() -> Response:
    return render_template("index.html")


@app.route("/login")
def login() -> Response:
    auth_methods = current_app.settings.auth.auth_methods()
    return render_template("login.html", auth_methods=auth_methods)


@app.route("/logout")
def logout() -> Response:
    logout_user()
    return redirect(url_for("views.index"))


@app.route("/login/email", methods=["GET", "POST"])
def email_magic_link() -> Response:
    form = EmailAddressForm()
    if form.validate_on_submit():
        token, expiry = get_magic_link_token_and_expiry(form.email.data)
        url = url_for(
            "views.email_magic_link_login", magic_link_token=token, _external=True
        )
        mail.send_mail(
            to=[form.email.data],
            template="email/magic-link",
            magic_link=url,
            magic_link_expiration=expiry,
        )
        return redirect(url_for("views.email_magic_link_done"))
    return render_template("email_magic_link.html", form=form)


@app.route("/login/email/sent")
def email_magic_link_done() -> Response:
    return render_template("email_magic_link_sent.html")


@app.route("/login/token/<magic_link_token>")
def email_magic_link_login(magic_link_token: str) -> Response:
    try:
        used_magic_link = UsedMagicLink(token=magic_link_token)
        db.session.add(used_magic_link)
        db.session.commit()
    except IntegrityError:
        # race condition, UsedMagicLink row exists
        db.session.rollback()
        return current_app.response_class(
            render_template("email_magic_link_used.html"), status=401
        )

    verified_email = parse_magic_link_token(magic_link_token)
    if verified_email is None:
        abort(404)

    user = User.query.filter_by(email=verified_email).first()
    if user:
        login_user(user)
        return redirect(url_for("views.talks_list"))

    user = User(email=verified_email, fullname=verified_email)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    flash("Welcome! Please tell us your name.")
    return redirect(url_for("views.user_profile"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def user_profile() -> Response:
    user = g.user
    form = UserForm(obj=user)
    if form.validate_on_submit():
        form.populate_obj(user)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("views.index"))

    return render_template("profile.html", form=form)


@app.route("/talks")
@login_required
def talks_list() -> Response:
    talks = [ts.talk for ts in g.user.talks if ts.state == InvitationStatus.CONFIRMED]
    proposed_talks = [t for t in talks if t.state == TalkStatus.PROPOSED]
    withdrawn_talks = [t for t in talks if t.state == TalkStatus.WITHDRAWN]

    invitations = TalkSpeaker.query.filter(
        TalkSpeaker.user == g.user,
        TalkSpeaker.state != InvitationStatus.CONFIRMED,
        TalkSpeaker.state != InvitationStatus.DELETED,
    ).all()
    speaker_actions = {
        InvitationStatus.PENDING: [
            ("Reject", "danger", "views.reject_invite"),
            ("Accept", "primary", "views.accept_invite"),
        ],
        InvitationStatus.REJECTED: [("Accept", "primary", "views.accept_invite")],
    }
    talk_actions = {
        TalkStatus.PROPOSED: [("Withdraw", "danger", "views.withdraw_proposal")],
        TalkStatus.WITHDRAWN: [("Re-Submit", "primary", "views.resubmit_proposal")],
    }
    prompt_for_survey = proposed_talks and not g.user.demographic_survey
    prompt_for_bio = proposed_talks and not g.user.speaker_bio
    return render_template(
        "talks_list.html",
        proposed_talks=proposed_talks,
        withdrawn_talks=withdrawn_talks,
        num_talks=len(proposed_talks),
        invitations=invitations,
        speaker_actions=speaker_actions,
        talk_actions=talk_actions,
        prompt_for_survey=prompt_for_survey,
        prompt_for_bio=prompt_for_bio,
        TalkStatus=TalkStatus,
    )


@app.route("/talks/<int:talk_id>", methods=["GET", "POST"])
@requires_proposal_editing_window_open
@login_required
def edit_talk(talk_id: int) -> Response:
    talk = load_talk(talk_id)
    form = TalkForm(conference=g.conference, obj=talk)
    if form.validate_on_submit():
        form.populate_obj(talk)
        talk.reset_after_edits()
        db.session.add(talk)
        db.session.commit()
        return redirect(url_for("views.preview_talk", talk_id=talk.talk_id))

    return render_template("edit_talk.html", talk=talk, form=form)


@app.route("/talks/<int:talk_id>/anonymized", methods=["GET", "POST"])
@login_required
def anonymized_talk(talk_id: int) -> Response:
    talk = load_talk(talk_id)
    if not talk.is_anonymized:
        flash("This talk has not yet been anonymized for review")

    return render_template("anonymized_talk_preview.html", talk=talk)


@app.route("/talks/<int:talk_id>/withdraw")
@login_required
def withdraw_proposal(talk_id: int) -> Response:
    talk = load_talk(talk_id)
    talk.state = TalkStatus.WITHDRAWN
    db.session.add(talk)
    db.session.commit()
    flash(f"{talk.title!r} withdrawn")
    return redirect(url_for("views.talks_list"))


@app.route("/talks/<int:talk_id>/resubmit")
@login_required
def resubmit_proposal(talk_id: int) -> Response:
    talk = load_talk(talk_id)
    talk.state = TalkStatus.PROPOSED
    db.session.add(talk)
    db.session.commit()
    flash(f"{talk.title!r} re-submitted")
    return redirect(url_for("views.talks_list"))


@app.route("/talks/<int:talk_id>/speakers", methods=["GET", "POST"])
@requires_proposal_editing_window_open
@login_required
def edit_speakers(talk_id: int) -> Response:
    talk = load_talk(talk_id)
    actions = {
        InvitationStatus.PENDING: [("Uninvite", "danger", "views.uninvite_speaker")],
        InvitationStatus.CONFIRMED: [],
        InvitationStatus.REJECTED: [],
        InvitationStatus.DELETED: [("Reinvite", "primary", "views.reinvite_speaker")],
    }

    speaker_emails = [s.user.email for s in talk.speakers]
    form = SpeakerEmailForm(speaker_emails)
    if form.validate_on_submit():
        email = form.email.data
        try:
            user = User(fullname=email, email=email)
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            user = User.query.filter_by(email=email).one()

        try:
            talk.add_speaker(user, InvitationStatus.PENDING)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

        mail.send_mail(to=[email], template="email/speaker-invite", talk=talk)

        return redirect(url_for("views.edit_speakers", talk_id=talk.talk_id))

    return render_template("edit_speakers.html", talk=talk, actions=actions, form=form)


@app.route("/talks/<int:talk_id>/speakers/uninvite/<int:user_id>")
@login_required
def uninvite_speaker(talk_id: int, user_id: int) -> Response:
    talk = load_talk(talk_id)
    user = User.query.get_or_404(user_id)

    ts = TalkSpeaker.query.filter_by(
        talk_id=talk.talk_id, user_id=user.user_id
    ).one_or_none()
    if not ts:
        abort(404)

    ts.state = InvitationStatus.DELETED
    db.session.add(ts)
    db.session.commit()
    # TODO: send email?
    return redirect(url_for("views.edit_speakers", talk_id=talk.talk_id))


@app.route("/talks/<int:talk_id>/speakers/reinvite/<int:user_id>")
@login_required
def reinvite_speaker(talk_id: int, user_id: int) -> Response:
    talk = load_talk(talk_id)
    user = User.query.get_or_404(user_id)

    ts = TalkSpeaker.query.filter_by(
        talk_id=talk.talk_id, user_id=user.user_id
    ).one_or_none()
    if not ts:
        abort(404)

    ts.state = InvitationStatus.PENDING
    db.session.add(ts)
    db.session.commit()
    # TODO: send email?
    return redirect(url_for("views.edit_speakers", talk_id=talk.talk_id))


@app.route("/talks/<int:talk_id>/speakers/accept")
@login_required
def accept_invite(talk_id: int) -> Response:
    ts = TalkSpeaker.query.filter(
        TalkSpeaker.talk_id == talk_id, TalkSpeaker.user == g.user
    ).one_or_none()
    if not ts:
        abort(401)

    ts.state = InvitationStatus.CONFIRMED
    db.session.add(ts)
    db.session.commit()
    return redirect(url_for("views.talks_list"))


@app.route("/talks/<int:talk_id>/speakers/reject")
@login_required
def reject_invite(talk_id: int) -> Response:
    ts = TalkSpeaker.query.filter(
        TalkSpeaker.talk_id == talk_id, TalkSpeaker.user == g.user
    ).one_or_none()
    if not ts:
        abort(401)

    ts.state = InvitationStatus.REJECTED
    db.session.add(ts)
    db.session.commit()
    return redirect(url_for("views.talks_list"))


@app.route("/talks/<int:talk_id>/preview")
@login_required
def preview_talk(talk_id: int) -> Response:
    talk = load_talk(talk_id)
    return render_template("preview_talk.html", talk=talk)


@app.route("/talks/new", methods=["GET", "POST"])
@requires_new_proposal_window_open
@login_required
def create_talk() -> Response:
    talk = Talk(accepted_recording_release=True)
    talk.add_speaker(g.user, InvitationStatus.CONFIRMED)
    form = TalkForm(conference=g.conference, obj=talk)
    if form.validate_on_submit():
        form.populate_obj(talk)
        db.session.add(talk)
        db.session.commit()
        return redirect(url_for("views.preview_talk", talk_id=talk.talk_id))

    return render_template("edit_talk.html", talk=talk, form=form)


@app.route("/profile/demographic_survey", methods=["GET", "POST"])
@login_required
def demographic_survey() -> Response:
    survey = g.user.demographic_survey or DemographicSurvey(user=g.user)
    form = DemographicSurveyForm(obj=survey)
    if form.validate_on_submit():
        form.populate_obj(survey)
        db.session.add(survey)
        db.session.commit()
        return redirect(url_for("views.demographic_survey_done"))
    return render_template("demographic_survey.html", form=form)


@app.route("/profile/demographic_survey/opt-out")
@login_required
def demographic_survey_opt_out() -> Response:
    survey = g.user.demographic_survey or DemographicSurvey(user=g.user)
    survey.clear()
    db.session.add(survey)
    db.session.commit()
    return render_template("demographic_survey_done.html", optout=True)


@app.route("/profile/demographic_survey/done")
@login_required
def demographic_survey_done() -> Response:
    return render_template("demographic_survey_done.html", optout=False)
