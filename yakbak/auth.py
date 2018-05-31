from typing import Optional

from flask_login import LoginManager

from yakbak.models import User


login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    try:
        return User.query.get(int(user_id))
    except TypeError:
        return None
