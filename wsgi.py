from yakbak.core import create_app
from yakbak.settings import load_settings_from_env


settings = load_settings_from_env()
application = create_app(settings)
