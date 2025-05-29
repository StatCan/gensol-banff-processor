"""A very basic example which demonstrates that the processor can be called without a JSON file."""

from pathlib import Path

import banffprocessor.exceptions
from banffprocessor.processor import Processor
from banffprocessor.processor_input import ProcessorInput

# Supplying parameters directly, instead of an input file
input_params = ProcessorInput(job_id="example1",
                              unit_id="IDENT",
                              # Gets the path to the folder containing this file, as a string
                              input_folder=Path(__file__).parent.as_posix(),
                              indata_filename="./inputdata/current.parq",
                              indata_hist_filename="./inputdata/historical.parq",
                              seed=1,
                              save_format=[".csv"],
                              log_level=2,
                              process_output_type="all") # Options "all", "minimal" or "custom"



try:
    my_bp = Processor(input_params)
    my_bp.execute()
    my_bp.save_outputs()
except (banffprocessor.exceptions.ProcedureReturnCodeError, banffprocessor.exceptions.MetadataConstraintError) as e:
    print(e) # noqa: T201 - A logging statement should be used in production
