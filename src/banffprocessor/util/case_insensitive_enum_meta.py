"""Metaclass for a case-insensitive version of an Enum."""

from enum import EnumMeta
from typing import TypeVar

_EnumMemberT = TypeVar("_EnumMemberT")

class CaseInsensitiveEnumMeta(EnumMeta):
    """Metaclass for a case-insensitive version of an Enum."""

    def __getitem__(cls: type[_EnumMemberT], name: str) -> _EnumMemberT:
        """Overridden base Enum __getitem__ to index on `name.upper()` instead of `name`."""
        return super().__getitem__(name.upper())
