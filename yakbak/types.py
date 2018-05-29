from typing import Any, Dict, List

from flask import Flask

from yakbak.settings import Settings


class Application(Flask):

    """
    Custom :class:`~flask.Flask` sub-class with some convenience attributes.

    """

    def __init__(
        self,
        settings: Settings,
        *args: List[Any],
        **kwargs: Dict[str, Any],
    ) -> None:
        super(Application, self).__init__("yakbak", *args, **kwargs)
        self.settings = settings
