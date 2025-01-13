import banffprocessor.processor_logger as plg
from banffprocessor.processor_data import ProcessorData
from pathlib import Path
from pyarrow import parquet as pq
import pandas as pd

class SaveParquet:
    
    @classmethod
    def execute(cls, processor_data: ProcessorData) -> int:
        # Creating a logger for this step
        log_lcl = plg.get_processor_child_logger("save_parquet")
        pd = processor_data
        
        try:
            # Each test should only be filtering a single targetfile, so just grab the first key
            target_file = next(iter(pd.metaobjects.get_process_controls(pd.current_job_step.controlid).keys()))
            log_lcl.info(f"Saving {target_file}...")
            target_dataset = pd.get_dataset(target_file)
            result_file = pd.input_params.output_folder / f"{target_file}_{pd.current_job_step.controlid}"
            pq.write_table(target_dataset, f"{result_file}.parq")
            
            target_dataset.to_pandas().to_csv(f"{result_file}.csv", index=False)
            
            return 0
        except Exception as e:
            # If an error occurs, printing the error to the log and returning a non-zero return code
            log_lcl.exception(str(e))
            return 1

# Providing a function so that the processor can register this class in the procedure factory
def register(factory):
    factory.register("save_parquet", SaveParquet)
