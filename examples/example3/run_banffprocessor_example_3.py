"""An example based on the IBSP Training Survey.

Note that this example was taken from ../TRNG/2015/Iteration_016/EI_Core_Central which uses synthetic data.
"""

from pathlib import Path

import banff

import banffprocessor
from banffprocessor.processor import Processor

# Get the directory of this script
program_dir = Path(__file__).resolve().parent

# The JSON file containing the input paramters is in the same location as this program file
input_file = program_dir.joinpath("processor_input.json")

# Setting the language to French so that log and console messages on written in French.
banffprocessor.set_language(banffprocessor.SupportedLanguage.fr)

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
    print(e) # noqa: T201 - A logging statement should be used in production
