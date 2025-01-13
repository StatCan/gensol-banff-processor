from pathlib import Path
import sys
from banffprocessor.processor import Processor

# Getting the current directory of the program and programatically adding the parent directory.
# This allows this example to run from any location
program_dir = Path(__file__).resolve().parent
sys.path.append(program_dir.parent.parent)

# Loading parameters from the JSON file
input_file = program_dir.joinpath("processor_input.json")
my_bp = Processor.from_file(input_file)

try: 
    my_bp.execute()
    my_bp.save_outputs()
except Exception as e:
    print(e)
