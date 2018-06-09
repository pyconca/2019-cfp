Configuration Guide
===================

Yak-Bak uses `TOML <https://github.com/toml-lang/toml>`_ for its
configuration file. Yak-Bak can only be configured through a configuration
file -- not through environment variables, or command line flags.

All sections in the configuration file are required, though some may be
empty.

TOML is a typed configuration language, and each field has a specific type.
Yak-Bak will not start if you configure the wrong type in a given field. The
type of each field is documented below.

A complete, documented example is available `in the source repository
<https://gitlab.com/bigapplepy/yak-bak/blob/master/yakbak.toml-example>`_.


``[site]`` section settings
---------------------------

The ``[site]`` section contains settings pertaining to the site and
conference for which you are collecting submissions.

Example::

    [site]
    title="PyConference Call for Proposals"
    conference="PyConference 2018"


``title``
~~~~~~~~~

:Type: string
:Required: true

The title of the site, will appear in ``<title>...</title>`` tags in HTML.

``conference``
~~~~~~~~~~~~~~

:Type: string
:Required: true

The name of the conference. This often includes the year, for example,
"PyConference 2018".


``[cfp]`` section settings
--------------------------

The ``[site]`` section contains settings specifically describing attributes
of the Call for Proposals and of the conference itself.

Example::

    [cfp]
    talk_lengths=[25, 40]

``talk_lengths``
~~~~~~~~~~~~~~~~

:Type: array of int
:Required: true

The lengths of talk slots, in minutes.


``[db]`` section settings
-------------------------

The ``[db]`` section configures the database for Yak-Bak.

Example::

    [db]
    uri="postgres+psycopg2://my.database.host/yakbak?sslmode=require"

``url``
~~~~~~~

:Type: string
:Required: true

A URL indicating the server name, database name, database type, and other
settings, of the database to be used by Yak-Bak. Uses `SQLAlchemy
<http://www.sqlalchemy.org/>`_ `database URL
<http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls>`_
syntax.


``[auth]`` section settings
---------------------------

The ``[auth]`` section configures how users can create accounts and log in
to Yak-Bak.

Unlike many web sites, Yak-Bak does not store any passwords -- username and
password authentication is omitted by design. Instead, Yak-Bak supports a
variety of "social authentication" mechanisms, which let users prove their
identity using a third party provider such as GitHub or Google.

Additionally, Yak-Bak supports "magic link" authentication, where a user can
have a special link emailed to them that, upon return, authenticates them to
Yak-Bak.

Example::

    [auth]
    github_key_id="6f370fd1DC9f963BA352"
    github_secret="9FaC731Bf3F934A04F326aD431eFC6f5E2A0EBa8"

    email_magic_link=true
    email_magic_link_expiry=7200  # 2 hours
    signing_key="jzBhOpiNlOtmgn7mLyE1vL_p9p835QZ-gT3innTeisQj"

``email_magic_link``
~~~~~~~~~~~~~~~~~~~~

:Type: boolean
:Required: false
:Default: false

If ``email_magic_link`` is true, authorization via magic link is enabled.
You must also set |email_magic_link_expiry|_, |signing_key|_, and |smtp|_.

.. |email_magic_link_expiry| replace:: ``email_magic_link_expiry``
.. |signing_key| replace:: ``signing_key``
.. |smtp| replace:: the ``[smtp]`` section
.. _smtp: #smtp-section-settings


``email_magic_link_expiry``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: int
:Required: false

How long generated magic links should be valid for, in seconds. Shorter
values are more secure, but less convenient to users. Recommended range is
1800 (30 minutes) to 86400 (1 day).

``signing_key``
~~~~~~~~~~~~~~~

:Type: boolean
:Required: false
:Default: false

A key that is used for securely signing magic links. It should be long and
randomly generated. If you are running Yak-Bak across several servers, you
must use the same ``signing_key`` on all servers.

.. warning::

    **Be sure to keep this key private!** If an attacker gains access to
    this key, they can spoof magic links and sign in as any person.

See |secret_key|_ for tips on how to generate keys securely.

.. |secret_key| replace:: ``secret_key``
.. _secret_key: #secret-key

Social Login
~~~~~~~~~~~~

Yak-Bak also supports the following social logins via OAuth:

* `GitHub <https://github.com/>`_
* `Google <https://google.com/>`_ (e.g. Google+ or GMail users)

Adding additional social providers is relatively straightforward, and
`contributions are welcome!
<https://gitlab.com/bigapplepy/yak-bak/blob/master/CONTRIBUTING.md>`_.

Each social authentication provider will have a method for generating a "key
ID" and "secret key" (sometimes these go by different names). These are
essentially a username and password for your instance of Yak-Bak to
authenticate itself to the provider, who can then authenticate users to
Yak-Bak. The sections below explain how to generate these credentials for
each of the providers supported by Yak-Bak.

GitHub
......

Settings reference:

:``github_key_id``: aka "Client ID"
:``github_secret``: aka "Client Secret"

To get a Client ID and Client Secret, `create a new application
<https://github.com/settings/applications/new>`_ on GitHub.

You should set the callback URL to
``https://your-site-domain/login/external/complete/github/``. Enter the
Client ID and Client Secret as ``github_key_id`` and ``github_secret``,
respectively.

Google
......

Settings reference:

:``google_key_id``: aka "Client ID"
:``google_secret``: aka "Client Secret"

To get a Client ID and Client Secret:

1. Create a new project in the `Google APIs Console
   <https://console.developers.google.com/apis/dashboard>`_
2. Click "Credentials" from the left-hand menu, then click "Create
   credentials", then "OAuth Client ID", then "Web Application"
3. Enter ``https://your-site-domain/login/external/complete/google-oauth2/``
   as the Authorized Redirect URL.

Enter the Client ID and Client Secret as ``google_key_id`` and
``google_secret``, respectively.


``[smtp]`` section settings
---------------------------

The ``[smtp]`` section configures mail sending using SMTP. All settings in
this section are optional, with no default, so if you set any, you should
set them all.

Yak-Bak requires that your SMTP server support ``STARTTLS`` for secure
authentication and mail sending. 

Example::

    [smtp]
    host="my-smtp-server.com"
    port=25
    username="my-user"
    password="my-password"
    sender="PyConference Organizers <organizers@pyconference.org>"

``host``
~~~~~~~~

:Type: string
:Required: false

The hostname of your SMTP server.

``port``
~~~~~~~~

:Type: integer
:Required: false

The port number of your SMTP server.

``username``
~~~~~~~~~~~~

:Type: string
:Required: false

The username of your SMTP account.

``password``
~~~~~~~~~~~~

:Type: string
:Required: false

The password of your SMTP account.

``sender``
~~~~~~~~~~

:Type: string
:Required: false

The "From" address used for emails sent by Yak-Bak.


``[flask]`` section settings
----------------------------

The ``[flask]`` section contains additional settings that are passed
directly to `Flask <http://flask.pocoo.org/>`_ `configuration
<http://flask.pocoo.org/docs/1.0/config/>`_.

A subset of Flask configuration variables are supported.

Example::

    [flask]
    secret_key="hlIuOBFBsKZBbq41BEE9XJUKipy2TC5b"
    templates_auto_reload=true

``secret_key``
~~~~~~~~~~~~~~

:Type: string
:Required: true

A key that is used for securely signing session cookies, and other security
operations. It should be long and randomly generated. If you are running
Yak-Bak across several servers, you must use the same ``secret_key`` on all
servers.

.. warning::

    **Be sure to keep this key private!** If an attacker gains access to
    this key, they can tamper with user sessions, or synthesize fraudulent
    sessions as any user.

One way to derive a secure ``secret_key`` is with :py:func:`os.urandom`,
like::

    $ python -c 'import base64, os; print(base64.b64encode(os.urandom(33)))'
    b'5jE9p1OVlsL96mqEDURmafgZeAk6LayllWf9EIkMYE4g'

``templates_auto_reload``
~~~~~~~~~~~~~~~~~~~~~~~~~

:Type: boolean
:Required: false
:Default: false

Whether Flask should re-load templates after you save them. This is only
useful during development, and should always be set to ``false`` (or omitted
entirely) from production configurations.


``[logging]`` section settings
------------------------------

The ``[logging]`` section configures Yak-Bak's operational logging.

Example::

    [logging]
    level="INFO"

``level``
~~~~~~~~~

:Type: string
:Required: false
:Default: "INFO"

The :py:mod:`logging` level.
