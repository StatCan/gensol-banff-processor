"""Native Language Support (NLS) for the Banff Processor.

Implement bilingual message support via `gettext`. This module was copied from Banff and
adapted for the Banff Proessor.
"""
import gettext
import locale
from collections.abc import Iterable
from pathlib import Path
from warnings import warn

from banff.nls import SupportedLanguage

# Store language settings in module level variables, access via functions (defined below)
default_language = SupportedLanguage.en
active_language = default_language

def _get_translations_instance(languages: Iterable[str] | None,
                               domain: str = "banffprocessor",
                               locale_dir_relative: Path = "messages/",
                               fallback: bool = True) -> gettext.NullTranslations:
    locale_dir = Path(__file__).parent / locale_dir_relative
    return gettext.translation(languages=languages, domain=domain, localedir=locale_dir, fallback=fallback)

# setup gettext for each supported language
en_i18n = _get_translations_instance(["en"])
fr_i18n = _get_translations_instance(["fr"])

def custom_gettext(a: str) -> str: # aka _(a):
    """Implement costom gettext function.

    To be aliased as `_()` when used by other modules.

    Uses the gettext instance corresponding to the active language, defaulting to English.

    Why not use `gettext.install()`?
        - it goes against a tsunami of recommendations against modifying builtins
        - it plays poorly with intellisense
        - it makes the origin of the `_()` function untraceable to new developers
        - it may affect (or be affected by) 3rd party Python Code
          - installed `_()` can become broken (redefined, undefined) when running interactively.
    """
    if active_language == SupportedLanguage.en:
        return en_i18n.gettext(a)
    if active_language == SupportedLanguage.fr:
        return fr_i18n.gettext(a)
    return en_i18n.gettext(a)

def determine_language() -> SupportedLanguage:
    """Try to determine user's language and return corresponding `SupportedLanguage` member.

    Calls `locale.getlocale()`, performs custom search on language portion of return value
    for French and English language codes as observed in the wild (i.e., Windows AVD, Linux VM).
        Users can affect the outcome using `locale.setlocale()` prior to importing the package.
        For example, to use French run `locale.setlocale(locale.LC_CTYPE, "fr_CA")`

    Returns associated `SupportedLanguage` member.
        `.UNKNOWN` if language not supported

    about `locale.getlocale()`
        [non RFC1766 language codes](https://github.com/python/cpython/issues/82986)
        - Around Python 3.8 on Windows, this function started returning codes
          like 'English_United States', instead of 'en_US'
    about `locale.getdefaultlocale()`
        [getdefaultlocale() deprecated](https://github.com/python/cpython/pull/31206)
        - tempting to use since it returns rfc1755 codes seemingly in all versions
        - not used because it's deprecated in Python 3.13
    """
    try:
        # get current language
        current_locale = locale.getlocale()[0] # like `'en_US'` or `'eNgLIsH_United States'`
        current_language = current_locale.lower().split("_")[0] # like `'en'` or `'english'`

        # return associated supported language
        # search for supported language's with matching language value
        for sl in SupportedLanguage:
            if current_language in sl.value:
                return sl

        return SupportedLanguage.UNKNOWN
    except IndexError:
        return SupportedLanguage.UNKNOWN

def get_language() -> SupportedLanguage:
    """Return the active language."""
    return active_language

def set_language(lang : SupportedLanguage | None = None) -> None:
    """Set the active language to `lang`, or determine language based on locale.

    Specify a member of `banffprocessor.SupportedLanguage` for `lang`.

    The value set by this function will affect log message output.  It may be referred to
    (via `get_language()`) by other modules in order to implement NLS.
    """
    _ = custom_gettext
    # get or validate `lang`
    if lang is None:
        lang = determine_language()
    elif not isinstance(lang, SupportedLanguage):
        mesg = _("invalid `lang`, expecting `SupportedLanguage` member")
        raise TypeError(mesg)

    # Set language (module level variable)
    global active_language
    if lang == SupportedLanguage.UNKNOWN:
        active_language = default_language
        mesg = _("Language not supported, using default language: {}").format(default_language)
        warn(mesg, stacklevel=2)
    else:
        active_language = lang
