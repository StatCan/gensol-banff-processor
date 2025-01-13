"""An example that includes process controls and process blocks.

The tutorial was restructured to replace user-defined processes with a process control.
The process control applies to multiple steps so a process blocks is used.
"""
from pathlib import Path

import banff

import banffprocessor
import banffprocessor.util.metadata_excel_to_xml as e2x
from banffprocessor.processor import Processor

# Setting the language to French so that log and console messages on written in French.
banffprocessor.set_language(banffprocessor.SupportedLanguage.fr)

# Get the directory of this script
program_dir = Path(__file__).resolve().parent

# Convert metadata from Excel to XML
input_file = program_dir /  Path("metadata") / Path("banffprocessor_metadata.xlsx")
e2x.convert_excel_to_xml(str(input_file))


# The JSON file containing the input paramters is in the same location as this program file
input_file = program_dir / Path("processor_input.json")

# If you don't want diagnostics information in the log, the following command can be executed.
banff.diagnostics.disable_all()

# This section creates a banff processor object based on the input parameters, executes the job and saves the outputs to disk.
try:
    my_bp = Processor.from_file(input_file)
    my_bp.execute()
    my_bp.save_outputs()
except (banffprocessor.exceptions.ProcedureReturnCodeError,
        banffprocessor.exceptions.MetadataConstraintError,
        banffprocessor.exceptions.UserDefinedPluginError) as e:
    print(e) # noqa: T201 - A logging statement should be used in production, this is just an example.
