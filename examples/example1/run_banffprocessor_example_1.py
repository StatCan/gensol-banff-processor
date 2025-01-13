"""A very basic example of how to call the Banff Processor with a JSON file."""

from pathlib import Path

import banffprocessor.exceptions
from banffprocessor.processor import Processor

# Get the directory of this script
program_dir = Path(__file__).resolve().parent

# Loading parameters from the JSON file
input_file = program_dir.joinpath("processor_input.json")

try:
    my_bp = Processor.from_file(input_file)
    my_bp.execute()
    my_bp.save_outputs()
except (banffprocessor.exceptions.ProcedureReturnCodeError, banffprocessor.exceptions.MetadataConstraintError) as e:
    print(e) # noqa: T201 - A logging statement should be used in production
