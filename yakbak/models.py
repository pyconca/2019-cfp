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


class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), nullable=False, unique=True)
    # password = ...
    name = db.Column(db.String(256), nullable=False)
