# Yak-Bak

Future home of a tech conference call for proposals and program selection app.

## Running it Locally

Yak-Bak requires Python 3.6 or newer, and PostgreSQL 10 or newer.

1. Install requirements: `pip install -r test-requirements.txt`

    You may want to use [virtualenv](https://virtualenv.pypa.io/en/stable/)
    or [virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/)
    to prevent interference with or by other installed packages and projects.

2. Copy the `yakbak.toml-local` file to `yakbak.toml`.

    The `yakbak.toml-local` file contains sensible defaults for local
    development, but not proper values for production configuration. On your
    production systems, you will have to manage the configuration file outside
    of the repository. Be a good citizen and don't ever check production
    configuration into the source code repo!

3. Run the Flask development server: `FLASK_APP=wsgi flask run`

    You may find the `--debugger` and `--reload` flags helpful during
    development.

4. Run tests with `py.test yakbak`, check style compliance with `tox -e
   style`, check types with `tox -e mypy`, or run the full CI suite (tests,
   style check, and type check) simply with `tox`.
