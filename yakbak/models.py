"""
Database models for Yak-Bak.

Some style notes:

- Always name tables with the singular noun for the data they contain,
  eg "User" not "Users"
- Always have an opaque primary key (usually an integer), even if a
  surrogate key seems like a good candidate (eg is unique, stable, etc)
- Always name the primary key "<tablename>_id"
- MyPy has some trouble understanding SQLAlchemy, so use `# type: ignore`
  on each model class, but do annotate each column with a type

"""
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class User(db.Model):  # type: ignore
    user_id: int = db.Column(db.Integer, primary_key=True)
    email: str = db.Column(db.String(256), nullable=False, unique=True)
    # password = ...
    name: str = db.Column(db.String(256), nullable=False)

    # Flask-Login compatibility
    def get_id(self) -> str:
        return str(self.user_id)

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_active(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False
