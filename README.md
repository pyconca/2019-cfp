# Yak-Bak

Future home of a tech conference call for proposals and program selection app.

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

## Running it Locally

Yak-Bak requires Python 3.7 or newer.

1. Install requirements: `pip install -rtest-requirements.txt`

    You may want to use [virtualenv](https://virtualenv.pypa.io/en/stable/)
    or [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/)
    to prevent interference with or by other installed packages and projects.

2. Copy the `yakbak.toml-local` file to `yakbak.toml`.

    The `yakbak.toml-local` file contains sensible defaults for local
    development, but not proper values for production configuration. On your
    production systems, you will have to manage the configuration file outside
    of the repository. Be a good citizen and don't ever check production
    configuration into the source code repo!

3. Choose a database and enter an appropriate URI in `yakbak.toml`

    For local development with Postgres, you may use
    `postgres+psycopg2://localhost/yakbak`, assuming a database name of
    `yakbak`.

    We recommend that you use PostgreSQL 10 or newer. You will also need to
    install the PostgreSQL driver for python with `pip install psycopg2`.

4. Create tables in the database with `FLASK_APP=wsgi flask sync_db`

5. Run the Flask development server: `FLASK_APP=wsgi flask run`

    You may find the `--debugger` and `--reload` flags helpful during
    development.

6. Run tests with `tox -e py37`, check style compliance with `tox -e style`,
   or check types with `tox -e mypy`. You can also format the code with `tox -e
   format`.

## Development Notes

- Yak-Bak uses [pip-tools](https://github.com/jazzband/pip-tools) to manage
  the `requirements.txt` from `install_requires` in setup.py.

  To update dependencies, run `tox -e freeze`. To add a new package, run `tox -e
  freeze -- --upgrade-package name-of-package`; this will update
  `requirements.txt` with just that package and its dependencies. You will have
  to re-run `pip install -r requirements.txt` after doing so to install or
  update the packages.

## Social Auth

### GitHub

You will need to [create a new
application](https://github.com/settings/applications/new) on GitHub. You
should name it "Yak-Bak <yourname> Development". You can set the homepage
URL and description to anything you like, but you will need to set the
callback URL to `http://localhost:5000/login/external/complete/github/`.
Enter the Client ID and Client Secret as `github_key` and `github_secret`,
respectively, in `yakbak.toml` in the `social_auth` section.

### Google

You will need to create a new project in the [Google APIs
Console](https://console.developers.google.com/apis/dashboard) by clicking
"Select a Project" and then "New Project" in the upper-right of that dialog.
You should name it "Yak-Bak <yourname> Development". Select your project
from the "Select a Project" menu, then select "Credentials" from the
left-hand menu. Click "Create credentials", then "OAuth Client ID". Select
"Web Application", and enter
`http://localhost:5000/login/external/complete/google-oauth2/` as the
Authorized Redirect URL. Enter the Client ID and Client Secret as
`google_key` and `google_secret`, respectively, in `yakbak.toml` in the
`social_auth` section.

You must also enable the Google+ API. Go to the [Google APIs
Console](https://console.developers.google.com/apis/dashboard), select your
project, select "Dashboard" on the left menu, then click "Enable APIs and
Services". Search for, select, and enable the Google+ API.
