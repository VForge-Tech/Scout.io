'''Package initializer for app.models.

Import all model classes so that SQLAlchemy's Base metadata is aware of
the tables when ``Base.metadata.create_all`` is invoked (e.g., in test
fixtures).'''

# Import model classes to register them with ``Base``
from .chatbot import Chatbot  # noqa: F401

__all__ = [
    "Chatbot",
]
