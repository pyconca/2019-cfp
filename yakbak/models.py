"""
Database models for Yak-Bak.

Some style notes:

- Always name tables with the singular noun for the data they contain,
  eg "User" not "Users"
- Always have an opaque primary key (usually an integer), even if a
  surrogate key seems like a good candidate (eg is unique, stable, etc)
- Always name the primary key "<tablename>_id"

"""
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class User(db.Model):  # type: ignore
    user_id: int = db.Column(db.Integer, primary_key=True)
    email: str = db.Column(db.String(256), nullable=False, unique=True)
    # password = ...
    name: str = db.Column(db.String(256), nullable=False)
