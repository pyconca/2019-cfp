"""
Yak-Bak collects submissions for and allows voting on conference talk proposals.
"""
from setuptools import find_packages, setup


setup(
    name="yak-bak",
    description=__doc__.strip().splitlines()[0],
    long_escription=__doc__,
    author="Big Apple Py, Inc.",
    author_email="yakbak@bigapplepy.org",
    url="https://gitlab.com/bigapplepy/yak-bak",
    download_url="https://gitlab.com/bigapplepy/yak-bak/tags",
    license="BSD-3-Clause",
    packages=find_packages(),
    install_requires=[
        "alembic",
        "attrs",
        "flask",
        "flask-login",
        "flask-mail",
        "flask-sqlalchemy",
        "flask-wtf",
        "itsdangerous",
        "markdown",
        "python-frontmatter",
        "python-social-auth",
        "social-auth-app-flask-sqlalchemy",
        "sqlalchemy",
        "toml",
    ],
    entry_points={
        "flask.commands": [
            "sync_db=yakbak.flaskcli:sync_db",
        ],
    },
    setup_requires=["vcversioner"],
    vcversioner={"version_module_paths" : ["yakbak/_version.py"]},
)
