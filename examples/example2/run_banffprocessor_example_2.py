"""An example which has plugins and executes in French."""

import locale
from pathlib import Path

locale.setlocale(locale.LC_CTYPE, "french")

import banffprocessor.exceptions  # noqa: E402 - The locale must be set before this import or the language will already be set
from banffprocessor.processor import Processor  # noqa: E402 - The locale must be set before this import or the language will already be set

# Get the directory of this script
program_dir = Path(__file__).resolve().parent

# Loading parameters from the JSON file
input_file = program_dir.joinpath("processor_input.json")

plugin_folder = program_dir.joinpath("plugins")

try:
    my_bp = Processor.from_file(input_file)
    my_bp.execute()
    my_bp.save_outputs()
except (banffprocessor.exceptions.ProcedureReturnCodeError,
        banffprocessor.exceptions.MetadataConstraintError,
        banffprocessor.exceptions.UserDefinedPluginError) as e:
    print(e) # noqa: T201 - A logging statement should be used in production, this is just an example.
