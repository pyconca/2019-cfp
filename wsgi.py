from yakbak.core import create_app
from yakbak.settings import load_settings_file


settings = load_settings_file("yakbak.toml")
application = create_app(settings)
