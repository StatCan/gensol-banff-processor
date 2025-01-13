"""Native Language Support (bilingual messages) for the Banff Processor."""

from banffprocessor.nls.nls import SupportedLanguage, default_language, get_language, set_language
from banffprocessor.nls.nls import custom_gettext as _  # create commonly used `_()` alias for gettext

__all__ = [
    "SupportedLanguage",
    "_",
    "default_language",
    "get_language",
    "set_language",
]
