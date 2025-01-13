import os
import sys
from importlib.metadata import PackageNotFoundError, version

import banff
import pandas as pd

import banffprocessor.nls
from banffprocessor.nls.nls import SupportedLanguage

# get version from package metadata
try:
    __version__ = version("banffprocessor")
except PackageNotFoundError:
    __version__ = "Unknown/Inconnue"

# Initialize Native Language Support (bilingual messages)
banffprocessor.nls.set_language()

# Adds the directory of the current src folder to the path in order to
# enable pytest tests to properly import
sys.path.append(os.path.dirname(os.path.realpath(__file__))) # noqa: PTH120

# Defaults all fields with str dtypes to use Pandas StringDtype as their backend
# Note: This will be the default in future versions of Pandas
pd.set_option("future.infer_string", True)

def set_language(new_lang : SupportedLanguage = SupportedLanguage.en) -> None:
    """Set the languaged used for console and log messages.

    For `new_lang`, specify a value from enum `banffprocessor.SupportedLanguage`.
    """
    banffprocessor.nls.set_language(lang=new_lang)
    banff.set_language(new_lang)
