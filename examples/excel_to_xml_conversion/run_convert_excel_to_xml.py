"""An example to call the Excel to XML metadata converter."""

from pathlib import Path

import banffprocessor.util.metadata_excel_to_xml as e2x

# Get the directory of this script
program_dir = Path(__file__).resolve().parent

input_file = program_dir.joinpath("Banff_2.08_Processor_Tutorial.xlsx")
e2x.convert_excel_to_xml(str(input_file))
