"""Shared declarative registry; no engine, session or automatic migrations."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    def __repr__(self):
        return f'{type(self).__name__}(id={self.__dict__.get("id")!r})'

    def public_dict(self):
        raise TypeError('This model has no public projection')
