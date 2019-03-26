from flask import Flask

from yakbak.settings import Settings


class Application(Flask):

    """
    Custom :class:`~flask.Flask` sub-class with some convenience attributes.

    """

    def __init__(
        self,
        settings: Settings,
    ) -> None:
        super(Application, self).__init__("yakbak")
        self.settings = settings
